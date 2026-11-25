# Local AI inference, security and operational architecture

**Status:** proposed future design. No model download, runtime adoption or implementation authorised here. [Precedence](README.md).

## 1. Windows-native, entirely offline

Retain the current application stack decision process (ADR-0005 on active application branch at review time). Do not introduce a Linux VM, Docker, WSL or remote inference merely to support AI. Choose a native Windows-compatible inference service after representative PoCs; any exception needs measured justification and architecture review. Keep all assets, tokenizers, models, licenses and dependencies in signed, versioned offline packages.

Runtime candidates for later evaluation include llama.cpp-compatible local inference, ONNX-compatible inference where model/operator support permits, and other Windows-compatible engines. Orchestration candidates include a small application-owned state machine, Semantic Kernel and LangGraph; none is selected here. Verify exact versions, weights/code licences, tool-call behaviour, offline startup, resource needs, Windows service recovery and maintenance burden. No reliance on cloud API keys or model-hub pulls. No current claim about particular model quality.

Use a local model adapter with typed capabilities (structured output, embeddings, reranking, context limits), model/tokenizer/quantisation/config hashes, versioned prompt templates, cancellation, budgets, concurrency limits and explicit error handling. Do not couple the domain or rule engine to a specific vendor/model.

CPU must support basic research services even with AI disabled. Model performance and optional GPU/VRAM requirements are to be benchmarked; exact production hardware remains open. Isolate and queue long inference jobs; protect interactive search from model/ingestion resource starvation. If inference is unavailable, retain search, graph and original evidence navigation.

## 2. Trust boundaries

```
LAN browser -> authenticated web/API
                      |
             policy/tool broker
              /       |       \
 published read    own-session   isolated inference
 services          services      (no direct corpus write)
                      |
             private work area
```

- Application and tool broker own all authorisation. The inference process is not the authenticated user and receives only scoped evidence; it has no direct database, source-vault mutation, shell or external network tool.
- Run inference, OCR and document parsers under distinct restricted Windows service identities; apply NTFS ACLs, job/process limits, firewall egress denial and bounded scratch space. Parser jobs use the current security architecture isolation controls; an inference worker is not a substitute for parser isolation.
- Service-to-service interfaces must authenticate local callers, enforce scope, size and timeout, and be inaccessible to ordinary LAN clients. A loopback address alone is not authentication. Bind no unnecessary network ports.
- The runtime must not contain HF credentials, signing private keys or acquisition credentials. External build-side acquisition and release verification remain separate. Use no telemetry, automatic model download or runtime licensing checks requiring internet.
- Restriction and withdrawal enforcement applies before retrieval, on graph paths, during context construction, on every tool call, at final output and export. Cache invalidation and rollback cannot resurrect a forbidden source or derived content.

## 3. Document-borne prompt injection

Treat all source text, OCR, user documents, graph labels and model output as untrusted data, not instructions. Delimit and annotate evidence channels, but do not rely on prompt wording as the primary boundary. Models cannot modify tool definitions, policy, evidence status or scope. Reject tool calls outside the registered allow-list and typed schema. Never follow instructions embedded in a PDF, citation, source metadata or retrieved text to access another document, disclose private context, run code, change policy or contact an external service.

Test hostile instructions in text layers, scanned text, captions, metadata, multilingual passages, quotations, tables, graph edges and tool responses. Include indirect exfiltration requests, spoofed policy messages, attempts to bypass gates and excessive tool-loop requests. Fail closed and allow legitimate source research when safely possible. Sanitise rendered output, links and exports separately; no unsanitised model HTML or executable content.

## 4. Session privacy, memory and audit

- Persistent personal bookmarks and research notes, where authorised, stay user-scoped; working documents and agent working context remain session-owned. No shared training data, shared vector store or global retrieval from private content.
- Never use personal working material to enrich the shared legal corpus. Admin source submission is a distinct deliberate operation with eligibility checks.
- Do not write working text, prompts, model responses, generated drafts or hidden reasoning into ordinary logs. Record metadata-only operational events with trace ID, actor, versions, tool names, outcome and resource use. Content-bearing trace/evidence artefacts belong only to the authorised session, under configured retention.
- Prevent cross-session access through result IDs, job polls, streams, model-context reuse, caching, exports and restored backups. Apply Document Studio's default exclusion of working sessions from backups unless the site adopts equivalent isolation, retention and deletion controls.
- On expiry/deletion, remove session content, derived text, vectors, caches, job results and exports. Stop active workflows and handle backups under the applicable retention/deletion policy.
- Explain research actions with concise source-linked summaries, not hidden chain-of-thought. Auditability requires traceable tools, evidence and decisions; it does not require disclosing private model internals.

## 5. Releases and reliability

Pin model, tokenizer, prompt, tool, retrieval, rule and evidence versions. Verify signed model and application bundles offline; maintain compatibility and rollback tests. Model changes never alter legal status or bypass existing approved rules. Invalidate cached outputs on policy/release change. Use versioned configuration, reproducible test fixtures and a kill switch for generative features. Record the measured reference hardware, latency, memory, model load time and concurrent users; design for resource limits, cancellation and service recovery.

No autonomous irreversible operations. Research, source proposal, working-document generation and legal approval remain distinct operation classes. Production activation requires independent security review and the corresponding release/owner approvals.

## 6. Isolation of model context and result surfaces (INT-F09)

Enforce the broker's operation domain on inputs, results, subsequent tasks, streams, caches and exports. Private+published context remains private; staged content never enters ordinary research. No shared mutable conversation/KV/prefix cache across owners or staged/private/published domains; partition reusable context by authorized domain/owner and exact policy/evidence/model revision, or reset before reuse. Prefer no private prefix caching until demonstrated safe. Isolate temporary artifacts and process identity; clear session buffers and derived caches on expiry, logout as configured, revocation or crash recovery. Audit metadata and progress counts must be projected to permitted scope. Render text via escaped/allow-listed components; sanitize links and DOCX/PDF export, never execute model-produced markup or macros. Test synthetic canary markers across alternating users, Admin outside own session, reused worker, crash/retry, logs, progress streams, browser storage, restored state, and hostile document instructions. No real restricted content is needed.

## 7. Model lifecycle and trust (INT-F10)

Current R1 trust purposes are release/register/trust_list; do not invent an accepted model signer or use a register key to activate weights. Future model bundles require an explicitly authorized purpose and approved trust-policy revision (either a separately scoped signer or a release signer expressly delegated model authority). Enforce signer identity, purpose and current revocation policy; canonical contract change is separately reviewed. A signature alone proves neither model suitability nor compatibility.

Manifest binds exact weights and hashes, tokenizer, chat template, quantization/conversion provenance, runtime/backend/version, operators, driver/OS/architecture compatibility, embedding dimension/normalization, model config, licenses/notices, SBOM, vulnerability assessment, package file inventory, required app/tool/prompt versions, independent evaluation report digest and accepted workload/output scope. No dynamic remote code, plugins or arbitrary executable model code by default. Stage offline in a restricted location, verify signature and all hashes before parsing/loading, validate compatibility and evaluate against accepted benchmarks. Reject unexpected files and unapproved runtime options. Keep monotone accepted package/trust/revocation state outside rollback. Atomically switch model and compatible index generation; do not mix vector spaces. Invalidate or restart affected sessions/results on switch or revoke. Rollback only to verified, non-revoked compatible package/index pair; otherwise disable inference and retain lexical search and source viewing. No automatic internet download. Test invalid signer purpose, corrupted weights, revoked model/key, interrupted swap, incompatible dimensions, stale evaluation, missing dependencies, restart and rollback on network-denied Windows.

## 8. Host-level admission and benchmarking (INT-F16)

Separate interactive search/PDF capacity from embedding/reranking, OCR/import and generation queues. Bound active and queued work by operation class and owner; reserve measured CPU/RAM/DB I/O capacity for research, cap GPU residency and model concurrency, apply fair scheduling and backpressure, cancel abandoned work. Workflow budgets are cumulative; do not start inference if memory headroom or queue limits are exceeded. Provide explicit degraded modes and retry timing; disable or defer inference rather than starving search. Track metadata-only queue delay, stage latency, cold/warm load, memory/VRAM, cancellation, terminal reason and model revision.

Later PoC compares pinned native Windows builds and CPU-only control; accelerator configurations optional. Use review shortlist (llama.cpp, ONNX Runtime and relevant Windows-compatible candidates; BGE-M3, multilingual-e5-base, BGE reranker v2 m3, Qwen3-4B as benchmark candidates only). Verify exact upstream license, weights and conversion terms; runtime licenses do not cover model artifacts. Compare fixed/hybrid/dynamic workflows and model size/quantization on identical tasks. Reference profile 16 cores/64 GB/SSD provisional. Test 1/5/10 concurrent research jobs and 25 browser users with active OCR/indexing/PDF; record OS/driver/models/hashes, corpus, arrival profile, context lengths, p50/p95/p99, time to first verified result, RAM/VRAM, failure and cancellation. Test clean offline install/update, cold boot, interrupted swap, full inference outage and egress denial. Keep non-AI SLO under mixed load. Initial short-research p95 30 s or cancellable background task; proposed benchmark, not measured claim.
