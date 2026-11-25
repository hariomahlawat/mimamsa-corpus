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
