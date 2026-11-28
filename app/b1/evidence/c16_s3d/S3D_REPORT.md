# C16 Tranche B Stage 3, stream S3-D: in-process generation swap, boundary on every surface, facet recount

**Acceptance level: FIXTURE (SG-5).** Everything here runs on the SYN fixture site (its two real generations), the
CP-1 slice fixtures, development keys, B06 harness (simulation-unbound) staging markers in the S3-D tests, and disposable
`c16s3d_*` databases (the CP-1 slice keeps its own guarded `c16cp1_*` databases). **No FG-\* or CG-\* gate is closed on
real data.** Not done and not authorised: production activation, AUTH-LEDGER or oracle change, HF access, merge, Codex
review. Defaults are unchanged: memory/memory and `Mimamsa:Activation:Enabled` off. Contract 2.0 is unchanged; the one
2.1 addition (PREPARE on the B06 control channel) is additive and flagged in `B06_ACTIVATION_JOURNAL.md`.

Branch `claude/c16-s3d-runtime` from `claude/c16-cp1` at `4ba059fa`.

## 1. In-process generation swap

Before S3-D the web process failed closed after OPEN until it was restarted (CP-1 report section 7 item 4). Now:

| Step | What happens | Where |
| --- | --- | --- |
| **PREPARE** (new, 2.1 additive, before ENTER_SWITCHING) | the tool asks the participant to load and verify the target's services **beside** the serving ones: generation store, disk text store, disk index, graph (built, published and verified), restricted register, eligibility, search, boundary. The old generation keeps serving throughout | `ActivationEngine.Transition`, `ActivationParticipant.Prepare` (outside the participant lock), `GenerationHost.Prepare`, `Program.LoadSlot` |
| refusal | a load or verification failure, or an exhausted residency budget, answers `prepared: false`; the tool refuses with `PARTICIPANT_NOT_PREPARED` **before BEGIN**: nothing is journaled, admission never stopped | engine |
| ENTER_SWITCHING … OPEN | unchanged B06 protocol (admission stops; journaled effects; OPEN) | engine |
| **switch** | at OPEN the participant re-reads the head from disk and, under its lock, `GenerationHost.Switch` makes the prepared slot current: one reference assignment, no I/O | participant `LoadFromDisk` → `OnSwap` |
| **pinning** | every request takes a participant pin and then a lease on exactly the slot its pin names (`GenerationHost.Acquire`); all of the request's services (`AppServices` is resolved per request from that slot) come from that one generation. A request cannot see a mix | `Program` activation middleware |
| **release** | a slot that is no longer current is released when its last lease goes: disk text store closed, disk index cache and pooled connections dropped, every reference dropped (start-up locals are nulled under activation, search's eligibility goes through a box, the per-generation `Incoming` cache is weakly keyed) | `GenerationHost.TrimLocked`, `SearchIndex.Release`, `DiskTextStore.Dispose` |
| **budget** | at most **two** slots resident or loading. A third waits up to `Mimamsa:Activation:SwapBudgetWaitSec` (default 30) for the old slot to drain and is then refused (fail closed; old keeps serving). A new PREPARE supersedes a target prepared for a transition that never reached OPEN | `GenerationHost.Prepare` |
| **disk engines required** | bounded memory needs page text and postings on disk, so with activation enabled the service **refuses to start** unless `Mimamsa:Text:Store=disk` and `Mimamsa:Search:Engine=disk` | `Program` |
| recovery / failure | OPEN onto a head that is not resident (restart, recovery roll-forward, rollback to a released generation) loads it outside the participant lock while nothing is admitted (the participant is not on the head: 503); a failed load leaves no slot and the participant not serving; a lease that cannot be taken (slot released between pin and lease) is answered 503 | participant `Open`/`LoadHead`, middleware |

Responses under activation carry a content-free `X-Mimamsa-Generation` header (the generation that answered).

### Measured memory

- Unit (`C16S3dSwapTests.TheSwappedOutGenerationIsReleasedAndItsMemoryIsMeasured`, memory text store and memory index on
  purpose: the heaviest case; full blocking GCs in the shared test process): baseline 4.39 MB, one generation resident
  4.67 MB, two resident 4.93 MB, after the switch with the old generation still pinned 4.95 MB, after its last pin went
  4.68 MB. One SYN generation costs 0.28 MB and 0.27 MB came back; the old `GenerationStore` is **collected** (weak
  reference dead). File: `swap_memory.json`.
- Web process (`C16S3dWebTests`, disk engines, `/api/diag/memory?gc=1`): GC heap 6.9 MB with one resident before the swap,
  6.0 MB with two resident (old pinned by a paused request), 6.0 MB after release; working set 90.7 / 94.7 / 94.1 MB. With
  the disk engines a SYN generation's resident footprint is below the GC noise; the release itself is shown by the log
  (`previous generation released` only after the paused request ended) and by the unit test's collected weak reference.
  File: `web_journey.json`.
- These are fixture sizes. A real-corpus measurement (resident bytes per generation with disk engines, and the peak during
  PREPARE) belongs to the real-data runs (B09).

## 2. Every surface behind the response boundary

**Mechanism.** `Eligibility.Boundary` (new; null by default) makes the single eligibility decision that every surface
already asks also ask the response boundary. So graph, reasoning, Commander, statutes, library, relations, Studio, PDF,
admin views and the search engine's hidden-document predicate filter excluded copies **at handler time**. Within one
request the signed state is read once (cached on the request); the **final check** re-reads the current state
immediately before commit and withholds the whole buffered response if any copy it touched or names is now excluded
(the CP1-03 linearisation rule, unchanged). Handler-specific additions: admin overview counts over non-excluded documents
and drops withdrawal rows of excluded copies; withdraw-scope and reinstate answer an excluded document like an unknown
one (a local reinstatement never overrides the signed channel); audit rows naming an excluded copy keep action and time
but lose object and detail; withdraw's `distinct_editions_not_affected` omits excluded ids; search chips (case name,
identifier counts) are written after hidden documents are dropped (`SearchService.HideChipsOfHiddenDocuments`, activation
only).

**Route inventory** (`ActivationRouteInventory.cs`; 44 mapped routes plus the SPA fallback; the bidirectional
source-vs-inventory test is kept):

| Class | Routes | Final validation |
| --- | --- | --- |
| Boundary (CP-1) | search, document, text, sections, citation, `/api/cite` (6) | buffered; touched set + every doc id / held-copy hash named in the JSON body |
| **Boundary (new)** | graph stats/resolve/node/path (4), reasoning assess/rule-gate (2), Commander domains and domain (2), statutes, library, relations, PDF meta, admin overview, withdraw-scope, reinstate, audit (22 in total) | same |
| **BoundaryPrivate (new)** | Studio: templates, documents (list, create), document, versions, save, append, delete, export, notes (list, create), note delete (12) | buffered; the touched set (every source the handler rendered as available). The body is not scanned: a citation of an unavailable source keeps the author's own stored reference in the content-free C15 "source no longer available" form, which is not corpus content. Export (Markdown/HTML) included |
| **BoundaryStreaming (new)** | protected Range delivery (1) | checked before the first byte; the CURRENT signed state is re-read immediately before **each slice** is handed to the transport. After an acceptance becomes visible at most the slice already handed over (`Mimamsa:Delivery:Slice`) plus what the transport queued can reach the client; the connection is then reset (RST). Bytes already sent are not recalled; no retroactive recall is claimed |
| ContentFree | health, login, logout, session, policy, diag/memory, admin accounts, unlock, SPA shell (9) | none |
| ProtectiveAction | admin withdraw (1) | none |
| Refused | **none**; only unknown routes (fail closed) | content-free 503 |

Note: CP-1's report counted 45 mapped routes, Studio as 13 and 30 refused; the inventory itself has 44 mapped routes,
12 of them Studio, 29 refused under CP-1. All 29 are now behind the boundary.

## 3. Facet recount

The CP-1 post-filter (hits removed after the engine ran, totals reduced, facets withheld) is gone. Under activation the
engine's hidden-document predicate **is** the boundary, so excluded copies never enter hits, totals or facets; facets are
counted over the surviving results exactly as for any withdrawn document, nothing is withheld, and no "some results are
not available" note reveals that something was removed.

Tests: `FacetsAndTotalsAreCountedExactlyOverTheSurvivingResults` (three cases, with and without a type filter): totals
equal the unfiltered totals minus the excluded documents that matched; every facet value equals its unfiltered count
minus the excluded documents with that value (respecting the facet-ignores-its-own-filter rule); values only excluded
documents had disappear; no chip names an excluded document. Web journey: `search_totals_recounted`,
`search_facets_recounted_exactly`, plus library and admin overview counts reduced by exactly the two excluded documents
and graph statistics reduced.

## 4. Tests

| Test | What it proves |
| --- | --- |
| `C16S3dSwapTests.ConcurrentReadersAcrossSwapsNeverMixGenerationsOrUseAReleasedOne` | real engine + participant + host, 6 reader threads, 6 swaps (activate/rollback): 0 mixed, 0 use of a released slot, never more than 2 resident; both generations served (`swap_concurrency.json`) |
| `…AFailureWhileLoadingTheTargetLeavesTheOldGenerationServingAndNothingJournaled` | `PARTICIPANT_NOT_PREPARED`, journal unchanged, admission never stopped, nothing left resident; the same transition succeeds once the cause is gone |
| `…ARollbackSwapServesThePreviousGenerationAgainAndReleasesTheNewOne` | rollback swap, the rolled-back-from generation collected |
| `…TheResidencyBudgetRefusesAThirdGenerationWhileTheOldOneIsInUse` | budget refusal before BEGIN while the old slot is leased; admitted once drained |
| `…AnAbandonedPreparedTargetDoesNotBlockTheNextTransition` | a superseded PREPARE target is released, not counted |
| `…TheSwappedOutGenerationIsReleasedAndItsMemoryIsMeasured` | memory release, measured |
| `…FacetsAndTotalsAreCountedExactlyOverTheSurvivingResults` (3) | facet recount |
| `C16S3dWebTests.InProcessSwapAndTheBoundaryOnEverySurface` | real Kestrel process, real channel and signed exclusion store, SYN site copy: load failure keeps G1 serving (every request during the failed load 200); live swap with 4 reader loops (0 mixed of 231 responses; the 195 503s are the B06 ENTER_SWITCHING→OPEN window, all `activation_not_serving`); a request paused on G1 across the swap is answered wholly from G1; G1 released only after it; diag memory; then 22 routes and Range paused after their handler / first slice, a **doc-id** (judgment) and a **copy-hash** (statute copy) exclusion accepted, every paused response withheld or content-free and Range stopped after 256 of 3354 bytes (one 256-byte slice); afterwards every surface leaves both copies out (Studio shows the C15 form; export and notes content-free; audit row redacted; reinstate refused; withdraw-scope 404); counts and facets recounted; rollback swap to G1 where the doc-id exclusion holds and the copy-hash exclusion applies only to that copy (`web_journey.json`) |
| `C16Cp1BoundaryTests.EverySurfaceIsBehindTheBoundaryAndOnlyUnknownRoutesAreRefused` | the new inventory; the bidirectional inventory test is unchanged |
| `C16Cp1SliceTests` (CP-1 journey, updated) | disk index required; the old process now **swaps in process** to G2 (and releases G1) instead of failing closed; the restarted process still adopts the shipped text store; the surfaces CP-1 refused serve; six more routes in the paused-request linearisation set (statutes, library, relations, graph stats, PDF meta); post-acceptance checks for statutes, library, graph stats, Commander, Studio templates, PDF meta (both kinds), relations and admin overview; rollback is an in-process swap back to G1 |

## 5. Default-mode parity (activation off)

By construction every new path is gated: `Eligibility.Boundary`, `AppServices.ActivationExcluded*` and
`ActivationStreamPause` are null, `HideChipsOfHiddenDocuments` is false, `AppServices` stays a singleton, and the CP-1
post-filter it replaces only ran under activation. Admin views compute the same values (the boundary answers "not
excluded"). Results: see section 7.

## 6. Edits outside `Mimamsa.Web` boundary/inventory and the participant swap path

- `Mimamsa.Core/Delivery/Eligibility.cs`: `Boundary` hook (null default).
- `Mimamsa.Core/Search/SearchService.cs`: `HideChipsOfHiddenDocuments` (false default); `SearchIndex.Release`,
  `SqlitePostingTable.Release` (new methods, only called on swap release).
- `Mimamsa.Web/Api.cs`, `ProtectedDelivery.cs`, `AppServices.cs`, `Program.cs` (handlers and composition, gated).
- Tests: `Activation/ActivationTestSupport.cs` (copy-hash withdrawals in the development store), `C16Cp1SliceTests.cs`.
- Docs: `docs/architecture/c16/interfaces/B06_ACTIVATION_JOURNAL.md` (flagged 2.1 PREPARE section).

## 7. Results

Filled in below with the run ids.
