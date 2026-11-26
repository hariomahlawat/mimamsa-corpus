# B1 walkthrough: user journeys (C14)

Each journey was driven in headless Chromium (Playwright 1.63.0) by `scripts/walkthrough.cjs`. The raw record is in `walkthrough_observations.json`: every step, its observed values, timings and console errors. Screenshots are in `screenshots/`, named `<journey>-<step>.jpg`.

**Instances**
- **B** = the commissioned instance, `127.0.0.1:5199`, database `mimamsa_b1`.
- **A** = an isolated audit instance, `127.0.0.1:5299`. It runs over `mimamsa_b1_audit`, a clone of `mimamsa_b1` taken before testing, with the same site and the same release.
- Destructive steps ran on A only: withdrawal, lockout and service kill.

**Labels:** "Observed" means seen in the running application. "Assumed" is marked where it applies.

## J01 Authentication, logout and session (B)

| Step | Observed | Assessment |
| --- | --- | --- |
| Sign-in page | Title and the "not legally verified" statement; the lockout and session rules are printed. | Good |
| Wrong password | "The username or password is not correct, or the account is locked." The same text appears for an unknown user (J14). | Good: no user enumeration |
| Sign in as User | Research shell in 448 ms | Good |
| Landing view | Empty three-pane research workspace with search guidance. There is no dashboard: no recent items, no corpus summary, no starting points. | P3 gap (see UX_REVIEW §2) |
| Session cookie | `mimamsa_session`: HttpOnly, SameSite=Strict, session cookie, Secure=false | Expected on HTTP loopback; LAN use needs TLS (known B1 limit) |
| Sign out | Returns to sign-in with "You have signed out." | Good |
| Back after sign-out | `about:blank`; inconclusive, because the test context had no prior history entry | Not tested |
| Deep link after sign-out | `/d/act-army-1950?p=25` shows the sign-in page | Good |

## J02 Navigation and keyboard (B)

- **Workspaces** (User): Research, Statutes, Graph, Studio, Assistant (with a closed glyph). An Admin also sees Administration.
- **Graph, Studio, Assistant:** these show honest "later milestone" or "Closed" pages, with the reasons and what would open them.
- **`?` help:** opens the full shortcut list.
- **`:` palette:** opens the commands.
- **`/` key:** focuses the search field.
- **Tab order:** skip link → logo → workspaces → search → view switch → user menu → results → pane dividers. It is logical, with no positive tabindex.
- **Automated accessibility basics** (landmarks, accessible names): no issues on the landing view or at any of the three layouts.
- **Not tested:** NVDA/JAWS, 200%/400% zoom.

## J03 Statutory identifier search and PDF viewer (B)

| Step | Observed |
| --- | --- |
| `s.69 Army Act` | Identifier chip "Section 69 · The Army Act, 1950"; 6 documents and 17 passages; provision text first. UI round trip 277 ms, server 44 ms. |
| Open first hit | First PDF page canvas after **940 ms**. Header shows type, issuer, dates (crawler-labelled), copy hash, source and retrieval date; one highlight mark. |
| Cited passage in view? | **No.** p.25 opens at its top (ss.64–66); s.69 is below the fold (F12). |
| N / page box / zoom / Fit width | All work. The hit counter steps (hit 3 of 6); page 30 renders within about 1.4 s including the wait. |
| Text view | "Extracted text (automated, not verified)", with physical page markers. |
| Hindi Army Act text | Garbled Devanagari; the header has no language marker (F07). |

## J04 Judgment, evidence status, provenance and cross-references (B)

- **`2013 INSC 408`:** resolves to Dharamvir Singh. The PDF appears in 829 ms.
- **Header:** neutral citation; reported `[2013] 8 S.C.R. 1119`; "Judges (crawler; may be incomplete) A.K. PATNAIK"; the case number on p.1, marked Candidate.
- **Context tabs:** Evidence, Provenance, Related, Cited/Citing, Notes.
  - **Evidence:** the seven axes, in order. Source integrity: re-hashed. Authenticity: Unknown. Fidelity: Candidate. Applicability: Not established. Approval: T0. Publication: Published. Freshness: Not evaluated.
  - **Provenance:** full source URL, record id, file name, SHA-256, bytes and pages.
  - **Cited/Citing:** 12 extracted citations, all labelled Candidate. Several read "Unresolved reference". It carries the notice "Absence of a citation is not absence of authority".
  - **Related:** "No related candidate records". The absence notice is present.
  - **Notes:** states that notes are not part of B1.
- **Party-name search:** `Dharamvir Singh` ranks the judgment **9th** (F02).

## J05 Citation copy and exact page (B)

| Action | Clipboard / result |
| --- | --- |
| Copy citation (C) | `The Army Act, 1950, 46 of 1950 (Parliament, 20 May 1950), p. 25 (metadata not verified)` |
| Internal ref (Shift+C) | `[act-army-1950 · copy e47a4265813e · p.25 · R13-b1-sample-20261126-4b31855f] /cite/R13-…/act-army-1950/e47a4265813e/25` |
| Open the permalink | Same copy, page 25 |
| Reload | Same URL, same page |

**Assessment:** exact, copy-pinned citation works. The legal citation names the page but not the section. For statutes, "s. 69" would be more useful than "p. 25" (P3, recorded in UX_REVIEW).

## J06 Statutes, amendments and temporal applicability (B)

- **Statutes list:** see F11 for the naming and duplicate problems.
- **Army Act s.75:**
  - Heading "[Field punishment.] Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 2".
  - Notice that the heading and note are compilation text, not a verified history.
  - A4 strip: "Temporal chain not established", with the as-enacted version and the omission version as candidates.
  - **As-of control disabled.**
- **Army Act s.127:** printed as omitted, with the same treatment as s.75.
- **IPC s.302:** "No A4 temporal version candidate is recorded"; **no BNS reference** (F03).
- **Brief's supersession cases:**
  - s.75–76 and s.127 (1992): **visible**.
  - IPC→BNS: **not visible**.
  - Dharamvir Singh (1982 Rules) vs the Sept 2026 ruling on the 2008 Rules: **not checked**, because the later ruling is not identifiable in the sample.
  - 2023 HC-writs ruling: **not established** (F04).

## J07 Results, filters, pagination and sorting (B)

- **`court martial`:** 255 documents and 13,497 passages, "showing the first 200 passages" (F10).
- **Facets:** Document type, Court or issuer, Year, Corpus status.
- **Filtering:**
  - Type = Judgment gives 220 documents.
  - Year 2020–2026 gives 109 documents.
  - The URL holds the filters, and the deep link restores them.
- **Sort:** Relevance, Date newest, Date oldest, Flat passages.
- **No pagination or load-more control.**

## J08 Misspellings, ambiguity, empty and malformed queries (B)

| Query | Observed |
| --- | --- |
| `court marshal` | Navy Regulations "provost marshal" first; no suggestion (F08) |
| `Rule 22 Rules` | "AMBIGUOUS Rule 22: which instrument?" with 11 candidates; nothing pinned |
| `xqzvbn plorktastic` | "No published documents match… not evidence that no authority exists." |
| `"court martial NEAR/5` | "Quotation mark is not closed… Problem at character 1… Nothing was searched." plus "Search the words without operators" (works) |
| `section 302 IPC` | "No instrument titled 'IPC'" (F01) |

## J09 Commander view and dark theme (B)

- **Commander view:** hides the court and status facets and the context pane. Otherwise results and documents are the same (F18).
- **Dark theme:** applies to the whole UI. The PDF page stays light, which is correct for originals.

## J10 Desktop layouts (B)

| Viewport | Horizontal overflow | Results pane | Results fully visible | Document pane | PDF canvas |
| --- | --- | --- | --- | --- | --- |
| 1366×768 | none | 360 px (filter rail collapsed to an icon) | 1 | 952 px | 904 px |
| 1920×1080 | none | 400 px | 4 | 968 px | 920 px |
| 2560×1440 | none | 400 px | 5 | 1608 px | 1530 px |

At 2560 px the PDF is rendered 1530 px wide; the page is taller than the screen and needs scrolling. There is no "fit page" option (only Fit width).

## J11 Access control (B)

- **Anonymous requests:** every API route returned **401**: session, search, documents, text, statutes, admin, pdf-meta, cite, and a path-traversal id.
- **User role:** `GET /api/admin/overview` → **403**; `/admin` in the UI → "This action is for Admins."; `POST /api/admin/withdraw` → **403**.

## J12 Administrator functions (A)

- **Overview:**
  - release, generation and HF revision;
  - documents 290, derivatives 290 and candidates 3,262, all verified;
  - originals re-hashed 290;
  - quarantined 0;
  - exclusion channel none; policy epoch; AUTH-LEDGER 0;
  - the withdraw form; the withdrawals table; the quarantine table.
- **CSRF checks:**
  - Admin `POST withdraw` with a foreign Origin → **403 csrf**.
  - Admin `POST withdraw` without a CSRF token → **403 csrf**.
- **Not available in B1:** user management, release import, audit-log viewer (the `audit_log` table exists: 7 rows at baseline).

## J13 Withdrawal and enforcement (A)

| Route after withdrawing `sc-1987-ranjit-thakur-1987insc285` | Observed |
| --- | --- |
| Admin UI | Confirmation dialog, then toast "Withdrawn (policy epoch 2)"; 840 ms from click to refreshed page |
| Concurrent searches during the withdrawal (20) | median 47 ms, max 157 ms |
| Search (User and Admin) | Not listed |
| `/api/documents/…`, `/text`, `/v2/…/pdf-meta` | 404 "This document is not available in this installation." |
| `/cite/…` permalink (UI) | "The cited copy is not available in this installation." |
| `/api/cite` | `CITED_COPY_UNAVAILABLE`, with no id, hash or page leaked |
| Viewer already open in the User's tab | **Still shows the page and metadata, with no notice** (F05) |
| `/d/<doc>` deep link | **Empty research home, no notice** (F05) |
| Restore | No control (F17) |

**Follow-up probe** (`scripts/withdrawal_open_viewer.cjs`, second document): same result. The 5-page file was fully delivered before withdrawal, so a mid-transfer cut-off was **not tested**.

## J14 Account lockout (A)

- **Lockout:** five wrong passwords → 401 ×5. The correct password then also → 401, with the generic message. An unknown user gets the identical message.
- **Lock extension:** every attempt during the lock, including a correct one, moved `locked_until` forward: `failed_count` went 8 → 9 → 10 (F15).
- **Expiry:** see WALKTHROUGH_REPORT §7.

## J15 Service loss and recovery (A)

- **Service stopped with a document open:** the banner reads "Connection to the server lost. Retrying." The views are cleared: "nothing is shown from cache".
- **Restart:** the UI recovered **10.6 s** after the restart command, which includes the service's own 7–10 s start-up. The session survived; there was no sign-in prompt.
- **After recovery:** the previously open document was not restored, which is by design.
- **Note:** the first run reported 72.8 s. That was a script error: the waiting condition used `#degraded`, which also carries the permanent "Not a production installation" banner. The figure was re-measured after fixing the condition, and the rerun is the recorded result.
