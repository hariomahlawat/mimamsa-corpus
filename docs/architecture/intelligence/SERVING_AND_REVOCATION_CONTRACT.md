# Serving and revocation contract

**R2 — INT-F01 (P1), INT-F12 (P2). Proposed normative design for review, not implemented.** Governs all application-controlled delivery, including ordinary research in B1/B2 and future AI. Integrate into existing publication, withdrawal, restore and P8 acceptance work without adding a Cycle 13 gate.

## 1. Safety property and limits

Define **withdrawal fence** as the serialized, durable acceptance of a new serving state by the site's authoritative policy service. From that point, no affected application-controlled content may be newly handed to a transport or external file recipient by the server. A completed request check, prior read lease, prebuilt file, or queued frame is not an authorization to deliver. A pending withdrawal is reported as pending, not completed; do not report success before durable acceptance. An exclusion update that is still being staged is not yet accepted. Where evidence of a newer accepted state is missing, halt content delivery rather than assert the old state is safe.

The linearization point for delivery is the final application-controlled handoff of a bounded frame/chunk/range or export byte segment to the transport, not initial request authorization, response creation, queue insertion, or client receipt. Bytes already handed to an OS/socket/proxy before the fence can arrive later; bytes already downloaded, printed, copied or displayed outside server control cannot be recalled. Do not promise retroactive erasure. Disable intermediary caching/buffering of protected content wherever controllable; minimize transport buffers, terminate affected streams and purge compliant clients' application-controlled views on invalidation. Offline/disconnected clients cannot be guaranteed to forget earlier material. Record this limitation explicitly in Admin withdrawal UX.

## 2. Authoritative state

One site policy coordinator owns a monotonically increasing serving epoch, referencing the active release generation, site publication/withdrawal revision, signed exclusion sequence and register hash, policy/authorization revision, current dependency/approval freshness state, trusted signing state and applicable session authorization revisions. Subject-scoped changes may be tracked as a versioned dependency map; every state change affecting access must serialize through the same final handoff mechanism. The epoch is a site serving concept, not a new legal status axis or R1 bundle field. A generation pin helps reproducibility, never authorizes bypass of current exclusion. Keep a durable high-water mark independent of release DB rollback. Fail closed if policy state is unavailable, its authority cannot be established, or a newer accepted epoch is unresolvable.

Treat original copy hashes and aliases, logical document/candidate/edge identity, provenance, derivatives, snippets, saved research, report claims, graph paths, prompt/evidence packs, embeddings, cached result fragments, exports and other dependent artifacts as a dependency closure. For each result, record exact source identities, derivative versions, other evidence dependencies, owner and scope, output class, policy and generation versions. If closure is unknown, do not reuse; invalidate conservatively (including full-generation invalidation when necessary). A restricted alias or alternate route cannot bypass a copy-level exclusion. Keep upstream publication and site authorization separate. No new restricted content is copied into diagnostic fixtures.

## 3. Handoff and revocation serialization

A suggested single-host design uses one trusted delivery gateway/coordinator for every protected route. The application may compute and queue work outside the coordinator. Queue entries carry immutable artifact identity, dependency manifest and scope, never a final delivery grant. Workers, static-file paths, PDF range routes, download handles and background exporters cannot write directly to clients. All application-controlled outbound buffers containing protected content are owned by or rechecked at the gateway; no asynchronous unguarded writer after a check. If a future multi-process implementation cannot prove this, use a sole gateway or an equivalent linearizable mechanism.

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

Oracle is a separately prepared ordered handoff/fence trace and known source dependency map. Force deterministic pause points, not timing-only sleeps. Test direct routes and actual Windows transport/proxy behavior in the applicable existing acceptance gate.

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