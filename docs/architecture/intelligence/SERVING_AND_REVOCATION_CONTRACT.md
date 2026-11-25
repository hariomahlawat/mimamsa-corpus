# Serving and revocation contract

**R2 — INT-F01 (P1), INT-F12 (P2). Proposed normative design for review, not implemented.** Governs all application-controlled delivery, including ordinary research in B1/B2 and future AI. Integrate into existing publication, withdrawal, restore and P8 acceptance work without adding a Cycle 13 gate.

## 1. Safety property and limits

Define **withdrawal fence** as the serialized, durable acceptance of a new serving state by the site's authoritative policy service. From that point, no affected application-controlled content may be newly handed to a transport or external file recipient by the server. A completed request check, prior read lease, prebuilt file, or queued frame is not an authorization to deliver. A pending withdrawal is reported as pending, not completed; do not report success before durable acceptance. An exclusion update that is still being staged is not yet accepted. Where evidence of a newer accepted state is missing, halt content delivery rather than assert the old state is safe.

The linearization point for delivery is the final application-controlled acceptance of an exact bounded immutable byte slice into the audited one-way transport boundary defined in §6, not initial request authorization, descriptor queue insertion, a generic framework Write/Flush, or client receipt. Bytes already handed to an OS/socket/proxy before the fence can arrive later; bytes already downloaded, printed, copied or displayed outside server control cannot be recalled. Do not promise retroactive erasure. Disable intermediary caching/buffering of protected content wherever controllable; minimize transport buffers, terminate affected streams and purge compliant clients' application-controlled views on invalidation. Offline/disconnected clients cannot be guaranteed to forget earlier material. Record this limitation explicitly in Admin withdrawal UX.

## 2. Authoritative state

One site policy coordinator owns a monotonically increasing serving epoch, referencing the active release generation, site publication/withdrawal revision, signed exclusion sequence and register hash, policy/authorization revision, current dependency/approval freshness state, trusted signing state and applicable session authorization revisions. Subject-scoped changes may be tracked as a versioned dependency map; every state change affecting access must serialize through the same final handoff mechanism. The epoch is a site serving concept, not a new legal status axis or R1 bundle field. A generation pin helps reproducibility, never authorizes bypass of current exclusion. Keep a durable high-water mark independent of release DB rollback. Fail closed if policy state is unavailable, its authority cannot be established, or a newer accepted epoch is unresolvable.

Treat original copy hashes and aliases, logical document/candidate/edge identity, provenance, derivatives, snippets, saved research, report claims, graph paths, prompt/evidence packs, embeddings, cached result fragments, exports and other dependent artifacts as a dependency closure. For each result, record exact source identities, derivative versions, other evidence dependencies, owner and scope, output class, policy and generation versions. If closure is unknown, do not reuse; invalidate conservatively (including full-generation invalidation when necessary). A restricted alias or alternate route cannot bypass a copy-level exclusion. Keep upstream publication and site authorization separate. No new restricted content is copied into diagnostic fixtures.

## 3. Handoff and revocation serialization

The initial single-host candidate uses one trusted in-process delivery coordinator for every protected route. §§6–9 refine this generic protocol and are controlling for R3. The application may compute and queue work outside the coordinator. Queue entries carry immutable artifact identity, dependency manifest and scope, never a final delivery grant. Workers, static-file paths, PDF range routes, download handles and background exporters cannot write directly to clients. All application-controlled outbound buffers containing protected content are owned by or rechecked at the gateway; no asynchronous unguarded writer after a check. If a future multi-process implementation cannot prove this, use a sole gateway or an equivalent linearizable mechanism.

Proposed transition protocol:

1. Prepare candidate policy state/exclusion bundle in an ACL'd staging area; verify signature, monotonicity, schema and exact digest. Identify affected dependency closure. Do not activate staged bytes yet.
2. Acquire the coordinator's exclusive revocation barrier. Stop new protected handoffs while committing; cancel or invalidate affected queued frames, result leases, ranges/download handles, workspace replay and export jobs. Do not wait indefinitely on blocked sockets or long inference calls. Long-running work can be interrupted asynchronously; no such work may deliver directly.
3. Durably accept the new policy/epoch and exclusion high-water record, then publish the authoritative in-memory state under the same serialization boundary. This is the fence. If durability or state consistency is uncertain, keep delivery closed and enter recovery. Only after fence acknowledgment may Admin/UI report withdrawal complete.
4. A delivery attempt acquires the handoff guard, resolves current actor/ownership, full dependency closure, eligibility and output authorization against the current state, and performs a bounded, nonblocking final transport handoff within the same serialized operation. If transport is not ready, enqueue only the immutable artifact reference, release guard, retry under a fresh guard; do not hold it through slow network I/O. No downstream server-managed queue may send unguarded content. Release guard immediately after acceptance or rejection.
5. Deny invalidated content, cancel affected streams and handles, issue a non-content invalidation event to connected authorized workspaces, and purge server/client-controlled caches and index entries asynchronously. Logical denial precedes cleanup. Unaffected results can be revalidated against the new state without unnecessary full recomputation. Purge status is distinct from revocation acceptance.

Implementation may use a serialized event loop or a writer-priority read/write guard with bounded handoffs, provided actual transport semantics and all intermediaries satisfy the property. No database transaction alone is assumed to cover streams or filesystem. If the framework/proxy cannot expose a safe final handoff, disable that protected streaming path until a proven adapter exists. Record accepted handoff sequence and fence sequence in metadata-only audit for deterministic race tests; no content in logs. Revocation must not starve behind a flood of reads.

### Delivery coverage

| Surface | Required enforcement |
|---|---|
| Search, facets, counts, autocomplete | Filter before results/counts; gate each returned artifact, recompute affected results |
| Original PDF and range/download | Each new bounded range/chunk via gateway, no direct static vault path or reusable bearer link |
| Graph and evidence packs | Closure of every node/edge/source and derivative; no path disclosure via hidden endpoint |
| Cached, saved or pinned results | Revalidate current epoch and dependencies; old cache never grants access |
| Progress/SSE/WebSocket, reconnect | Only typed authorized events, guarded handoff and fresh snapshot; terminate invalidated streams |
| Generated response or report | Final claim authorization plus delivery gate; no raw model stream |
| PDF/DOCX/export file | Build in owner-scoped staging, bind content/digest and dependencies; gate activation/download and each chunk; cancel/delete affected staged artifacts |
| Restore, rollback, local uploads | Establish latest accepted policy and local publication before opening traffic; reapply exclusion and verify closure |

No direct filesystem export into a shared LAN folder by an agent. User-requested exports outside application control are explicit actions subject to the same handoff rule.

## 4. Crash-safe exclusion acceptance (INT-F12)

R1 reference helper writes numbered payload and signature separately; a missing newest companion currently fails closed. Preserve its conservative behavior. Future production acceptance must make a complete verified pair and its acceptance status distinguishable. Use a site-owned protected state store outside rollbackable release data, durable atomic acceptance record/transaction with monotone sequence, content digest, verified signature reference, previous accepted digest and serving epoch. Use staging and durable flush of content and directory/metadata as supported on Windows; prove power-loss behavior on the actual storage/OS. A commit marker or atomic rename alone is not proof of durability. Use a single writer and CAS expected prior high-water. Secure this store against ordinary app/worker writes. Backup/restore cannot reduce accepted sequence or discard a committed withdrawal. Local Admin withdrawal state participates in the same durable monotone policy history even when upstream exclusion sequence is unchanged.

| Restart observation | Required action |
|---|---|
| Staged incomplete pair, acceptance record unchanged and current accepted state provable | Quarantine incomplete staging; retain last accepted state; report pending/failed update, not accepted |
| New verified pair durable, not yet accepted | Revalidate and complete authorized acceptance or discard staging; never silently announce success |
| New acceptance record durable; memory publication interrupted | Recover exact new state and exclusions before opening any route |
| Accepted high-water references missing/corrupt pair or local history | Halt protected delivery; recover matching authenticated state; never fall back to lower sequence |
| Restored older DB/release or restored old policy store | Compare to independent trusted high-water and reconcile current local state; halt if latest cannot be proven |
| Conflicting same-sequence digest/concurrent update | Reject; investigate; never choose by filename or mtime |

If the entire independent policy store and high-water evidence are lost, the system cannot establish latest state offline: require authenticated recovery evidence from authorized custody before reopening, not an assumption. A signed old update is not proof of currency. Protect model/key revocations under equivalent monotone policy; not a change to R1 schema here.

## 5. Acceptance cases (synthetic fixtures)

Oracle is a separately prepared dependency and accepted-operation map plus independently observed transport acceptance and fence trace (§9), not merely the coordinator's own log. Force deterministic pause points, not timing-only sleeps. Test direct routes and actual Windows transport/proxy behavior in the applicable existing acceptance gate.

| ID | Injected race/fault | Required result |
|---|---|---|
| REV-01 | Pause after initial read authorization but before final handoff; accept withdrawal | No affected handoff after fence; fresh unaffected result succeeds |
| REV-02 | Queue stream frame, PDF range, reconnect replay and cache hit; accept withdrawal | No queued content accepted; close affected stream, refresh allowed view |
| REV-03 | Build export, pause before preview/download and between chunks; withdraw dependency | Reject subsequent handoff, remove staged export; disclose prior delivered-byte limit |
| REV-04 | Withdraw via copy alias, indirect graph edge, saved fragment or changed local publication | Deny full affected dependency closure; no hidden counts; unaffected access remains |
| REV-05 | Crash before/after each pair write, durable acceptance, state publication; restart | Exact accepted sequence recovered or safe halt; unaccepted pair never silently accepted |
| REV-06 | Restore older DB/release with newer policy or missing policy store; concurrent updates | Latest accepted state enforced or halt; no resurrection, no sequence regression |
| REV-07 | Slow socket, blocked writer, flood of reads, withdrawal during inference | Bounded handoff and prompt fence progress; no bypass via direct worker/proxy route |
| REV-08 | Reattach local overlay after rollback; mutate policy or approval while output queued | Revalidate scope and dependencies; no post-fence stale operative or private delivery |

Pass condition: zero observed affected server handoffs accepted after fence in all deterministic fixtures; logs distinguish accepted-before-fence bytes from denied attempts. Verify actual platform behavior, resource bounds and unaffected access. This document specifies the design and test oracle; it does not assert implementation or test execution.

## 6. Concrete protected delivery profile (R2-N01)

### Topology and ownership transfer

**T0 candidate:** native Windows application service, one process owns policy and protected egress, no intermediate reverse proxy for protected routes. TLS and authenticated browser session required. Do not presume a particular HTTP framework already implements the boundary. Select the actual framework/host at ADR-0005 GB1; a proven alternative may use the same contract. Prefer bounded request/response and polling initially. Do not add a network gateway service simply to satisfy this document.

Define three distinct stages:
1. **PREPARED**: immutable content bytes or reference staged by app/worker; may be queued, never authorized to emit.
2. **ACCEPTED**: under shared coordinator guard, the approved transport adapter irrevocably takes ownership of an exact immutable byte slice (full or prefix only), copies or takes exclusive ownership of those bytes in a bounded one-way send buffer with no later content lookup or discretionary authorization; accepted sequence and offset recorded at that boundary. No future sendfile descriptor, deferred read, replayable artifact ID, or generic Write/Flush return counts. Downstream can only drain these exact already accepted bytes once, not create new slices or reopen content.
3. **RECEIVED**: client/packet observation, which can occur after fence for previously accepted bytes. Client receipt does not determine fence ordering.

If framework exposes only an opaque asynchronous queue, adapter must either prove that this queue is the bounded terminal one-way boundary (including every downstream copy and retransmission allowance) or keep it outside the accepted boundary and serialize actual later acceptance; otherwise disable that route. An implementation that holds coordinator guard across a potentially blocking flush fails. On native Windows, instrument the selected response pipe or socket/TLS send adapter to establish exact ownership and bounded nonblocking acceptance; no claim that ordinary framework APIs inherently provide this. For a controlled IIS/reverse proxy topology **T1 conditional**, include proxy/framework buffers inside audited boundary and total cap, or designate an explicitly proven one-way downstream sink receiving only already accepted byte slices; prevent proxy cache/replay, deferred opens, response generation from protected references, and bypass. If unable to demonstrate, T1 protected routes disabled; do not select T1 as production topology for these functions. No untested proxy or transport failover.

### Proposed adapter API and serialized loop

All routes use a single adapter contract, not ad hoc response writes. Prepare expensive dependency resolution, render, hash and validate outside guard; immutable artifact identity + exact serving component vector + scope + byte offset/length. Under writer-priority guard match current vector and authorization/ownership, validate available credit, then nonblocking accept. If vector changed, release guard and revalidate/recompute before retry. Every accepted unit includes headers/control metadata if they convey protected information.

```text
try_accept(artifact_id, offset, n, expected_state, authorization_ref)
    under coordinator guard:
        deny if current scope, state, digest, grant or dependency binding mismatches
        deny if update pending, route closed, or cap/credit unavailable
        result = terminal_adapter.try_take_exact_bytes(slice, credit)
        # result: ACCEPTED(k) where 0 < k <= n, or WOULD_BLOCK(0), or CLOSED(0)
        # k counts only bytes whose immutable ownership was actually transferred.
        account k and advance accepted offset under guard
    return result
```

For partial k, never retry accepted prefix; remaining suffix stays a reference in PREPARED and needs fresh admission. WOULD_BLOCK releases guard and schedules bounded retry with deadline; no unguarded writer. If transfer outcome ambiguous, close connection and invalidate route until reconciliation; never retry uncertain slice. Actual accepted units, not self-declared records, determine audit oracle. Close/reset affected stream at fence; no new affected content/error metadata accepted, only generic non-content status via fresh authorized request. Do not keep guard during long disk read, inference, TLS handshake or waiting for client. Writer priority from admission of a valid update prevents new read grants while commit proceeds. Work in progress may finish computation, but may not hand off.

### Initial measurable profile (proposed, not measured)

For T0 pilot define max byte slice 64 KiB; max charged outstanding accepted payload + metadata across all downstream buffering per connection 256 KiB; site aggregate 8 MiB; max prepared protected response 256 KiB (paginate larger research results), bounded number of concurrent transfers, configured finite deadlines. Count actual residual copies/bytes in framework, TLS, socket/kernel and any proxy; account compression expansion and headers, and do not release credit simply because app Write/Flush returned. Credit returns only on independently characterized drain/termination at boundary; if kernel/proxy accounting cannot prove caps, lower limits/change adapter or do not enable affected route. Count retransmitted network bytes separately: cap concerns unique accepted payload still potentially deliverable, not a promise about total physical retransmission traffic or browser retention. Establish conservative measurable upper bound including in-flight transport data; if unsupported, acceptance fails. Proposed p95 fence latency ≤1 s and max ≤5 s at reference 25 concurrent browsers / 10 concurrent queries plus slow-client stress, from valid-update admission to durable fence acknowledgement; timeout is pending/failed and protected delivery remains closed while uncertain, never false completion. Record storage/network conditions, worst observed and tail. Tune non-safety targets before trials; do not relax zero post-fence acceptance or claim these numerical limits already achieved.

| Surface | Initial admission and HTTP behavior |
|---|---|
| Search, catalogue, counts, graph | Bounded JSON responses/pagination, all protected headers and body through adapter. No shared HTTP cache. |
| PDF original | Authenticated PDF.js range endpoint, single range bounded to profile (client requests compliant range); valid 206 exact Content-Range and Content-Length, no fake short range. Reject unsupported multi/oversized ranges with non-content error; viewer configured to request bounded ranges. If range unsupported, full bounded document only if entire delivery path proven and within cap; otherwise show safe unavailable state until adapter tested. 416 for invalid/unsatisfiable range, no unauthorized size disclosure. Recheck each chunk/range; terminate mid-response on withdrawal, no fresh bytes. |
| Conditional requests | No protected intermediary cache, Cache-Control: no-store/private, no reusable static URL; do not return 304 authorizing stale content after withdrawal. Validate current policy before any 206/200/metadata; avoid ETag/size/last-modified disclosure to unauthorized caller. |
| Compression, static file/sendfile | Disable protected compression and deferred file sends until separately proven with exact slice accounting; no static vault route. |
| Progress | Bounded authenticated polling and fresh owner-scoped snapshots initially. SSE/SignalR/WebSocket protected events disabled until same adapter property and reconnect proof. No raw substantive tokens. |
| Export/preview/print | Future generated artifacts staged privately, immutable and trusted-authorized; bounded authenticated download/range, explicit user action. Browser printing/copy after receipt outside recall; no direct worker/shared directory. |
| Revoked mid-response | Abort/reset connection or stream without newly disclosing protected content; no successful completion flag. Subsequent authorized fetch receives generic invalidation or permitted fresh artifact; user sees incomplete/withdrawn state. |

No protected route may fall back to an unproven streaming or buffering mechanism to preserve apparent functionality. Prove usable basic search and PDF browsing on the selected host within existing B0/P1/P4/P5 and B1 scope; generated delivery later.

## 7. Effective state, precedence and re-admission (R2-N03)

Keep separately versioned components: active release generation and upstream release publication records; signed complete exclusion register sequence/hash; independent site-local publication/withdrawal history; owner/session authorization revision; legal holds/freshness/approval; trusted policy/model/signing state. Effective eligibility = eligible under current source/access rules AND published through an authorized current site channel AND no applicable restriction, site-wide hash/alias suppression, local withdrawal for requested publication, owner/session denial or applicable operational hold. Denial dominates permission within its scope. An upstream release-only removal does not automatically mean global hash suppression if same bytes legitimately held locally; require existing Admin reconciliation before any local re-admission where upstream withdrawn bytes also exist locally. A signed site-wide hash/alias denial overrides both channels and rollback. A local channel withdrawal must not be erased by signed update, release swap or reattachment. Keep distinct reason and scope; unresolved conflict denies affected access.

Prepare against exact component revision vector. Under same serialized commit compare all referenced prior revisions and derive effective state from authoritative inputs; if stale, reject/rebase/recompute, never replace entire state from a stale prepared snapshot. Signed update is complete signed list for its channel, not a merge that preserves obsolete signed entries forever; verify monotone sequence and digest, semantic identity per Crosswalk §7. A row removed from the latest list does not on its own re-publish an object or erase an independent site denial. Re-admission requires explicit authorized decision recorded for exact hash/identity, channel, previous denial and current evidence; only competent authority may lift restriction/legal hold; no routine Admin override of signed denial. No automatic re-admission from omission, old snapshot, new alias or re-upload.

Query result/cache dependencies include query partition, index generation, filters, authorization scope and coverage revision (not just returned hit IDs). Counts, facets, negative results, "no adverse authority found" and completeness statements depend on the eligible search universe. Change to potentially relevant partition invalidates result even if existing hit list unchanged. If narrow proof unavailable, invalidate whole relevant generation. No stale aggregate/coverage via cache. Unaffected scope may revalidate with exact dependency certificate.

Synthetic trace: at E10 signed S5 + local L3. Signed S6 prepared and local L4 withdrawal prepared both against E10. L4 commits E11; S6 stale CAS rejected/rebased against L4; E12 combines S6 + L4, both denials preserved. Reverse order produces same component state and effective denial. Reattach local alternate copy on old release: signed hash denial still applies; release-only withdrawal requires Admin reconciliation; explicit authorized re-admission only after all current denials cleared. Cache count previously 10 and displayed hits unchanged; one eligible hidden-in-page record newly withdrawn -> old count/coverage invalid, requery.

## 8. Durable acceptance protocol and restore authority (R2-N02)

Use a protected **current witness** outside rollbackable release DB/event backup; authoritative acceptance is a durable CAS of witness from (epoch, committed digest) to exact next (epoch, digest). A single site policy writer. Witness is not restored with application snapshots. Store separately under owner-controlled custody with independently recoverable current evidence; actual Windows storage durability and backup procedures to be proven. A matching old database + old policy + old witness copy is not evidence of currency. No offline algorithm detects rollback of all trust anchors without an external-to-restore trusted current witness. If host loss/restore cannot establish current witness from authorized non-rolled-back custody, halt protected access and require explicit authenticated recovery/reconciliation by authorized owner. No arbitrary manual reset or acceptance of lower epoch. Site must document witness custody before production; not selected here.

Protocol (event store + witness):
- P0: authorized operation ID, expected prior witness, complete signed/local operation bytes, normalized component vector and derived state manifest; canonical digest chains previous digest and epoch. Write complete prepared event and recoverable referenced bytes durably to protected journal; verify all signatures/identities and flush file/storage metadata. Event state PREPARED only.
- P1: under writer-priority exclusive barrier, confirm expected current witness/inputs and no competing accepted update. Durable atomic CAS on protected witness commits exact prepared digest. This CAS, once durability established, is **sole acceptance and fence**; no content handoffs during transition. If outcome uncertain, keep service closed until witness resolved. Do not acknowledge based on preparation.
- P2: reconstruct/install effective state from exact committed witness/event bytes, invalidate affected work and publish memory pointer before reopening; journal may append committed marker for diagnostics, but marker is not second authority.
- P3: return Admin acknowledgment containing operation ID, committed epoch/digest and effective scope; cleanup/purge completion separate. Idempotent retry with same operation ID and digest checks committed witness chain and reports original outcome only if authenticated; different bytes under same ID reject. Lost ack is not a second commit.

Durability contract: actual selected storage implementation must prove crash-consistent atomic witness update and complete durable preparation (flush semantics, directory/metadata, power-loss simulation), not assume file rename or OS flush success alone. If not provable, choose alternate protected store/transaction implementation or halt activation. Do not implement by separately restoring matching old files as authority.

| Crash/restore observation | Oracle action |
|---|---|
| Prepared E21 durable; witness still E20; no ack | E21 not accepted; quarantine/revalidate pending. E20 only if current witness provable and no unresolved mandatory update. |
| Witness E21 commits; journal marker or memory install absent | E21 authoritative; verify matching exact bytes, rebuild and enforce before any route; retry reports original E21 after recovery. |
| Witness E21 points to missing/corrupt prepared event | Halt; recover exact digest from authorized custody, never fall back E20. |
| Event marked E21 committed but witness E20 | Marker cannot commit. Treat mismatch as incident; halt until trusted witness/history reconciled, no false ack. |
| DB and event restored E19; current witness E21 | Recover exact E21 chain/local publication state or halt. |
| DB/event/witness snapshots all match E19, current witness custody lost | Currency unprovable; halt. Owner-authorized recovery must establish latest accepted state from trusted independent evidence, not matching stale pair. |
| Same epoch different digest; two writers or lost ack | CAS rejects conflict; investigate; same operation+digest already committed returns original ack only after current authorization. |

## 9. R3 fault-injection oracle

Repeat REV-01..08 and INT-09/10/19 against actual selected Windows topology. Independently instrument acceptance boundary (including partial writes and credit occupancy), separate packet/client observation, durable witness operations and storage crash points. Use synthetic distinct payload markers and known policy/operation oracle independent of application self-log. Pause before and after adapter acceptance, at partial acceptance, WOULD_BLOCK, header/range, downstream buffer/proxy, cancellation, reconnect, before/after preparation flush, witness CAS, memory install and ack. Compare expected accepted offsets and post-fence forbidden acceptance; measure residual unique already-accepted bytes against per-connection/site cap and withdrawal p95/max under stated load. Include conditional request, PDF.js configured ranges/fallback, compression disabled/alternate topology, slow clients, read flood, signed/local operations both orders, explicit re-admission and stale aggregate. Restore independently old DB/event/witness images and matching old trio; check safe halt when current authority missing. Positive controls: unrelated published search/PDF and local upload remain accessible; accepted pre-fence bytes may arrive later and are reported separately. No production claim until practical tests pass. Design protocol addresses original gaps; exact host, adapter, storage and witness custody remain decisions at existing PoCs and owner-approved deployment.
