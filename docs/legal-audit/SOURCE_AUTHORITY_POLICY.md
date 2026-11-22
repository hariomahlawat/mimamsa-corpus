# Source authority, copy provenance and conflict resolution policy (v1)

**Scope:** Indian Military Law Knowledge Base source intake, audit and review only; no application development.

## Governing distinction: legal authority is NOT the hosting website

Use **two independent dimensions** for every new source:

1. **Underlying document authority**: what the original document legally is, who issued it, and the date/scope of its authority.
2. **Carrier/copy provenance and fidelity**: where this particular copy was obtained, whether it reproduces the issued document faithfully, and what checks were performed.

Never rank legal sources solely by domain name, by whether someone uploaded a PDF, or by the number of agreeing copies. A government website can host a flawed transcription; a non-government archive can host a genuine facsimile of a Government Gazette. A SHA/MD5 proves byte integrity of the examined copy, **not** legal authenticity, completeness of amendments, or the current state of law.

## Working precedence (depends on the question)

| Question | Evidence priority | Qualification |
| --- | --- | --- |
| Exact wording on date of enactment/notification | Authenticated **issued Gazette**, signed/enacted instrument, official corrigendum | Check printed image, notice number, issue date and later corrections. |
| Rule/section currently operative | Issued text **plus complete applicable amendment, repeal, saving, and commencement chain**, interpreted in light of binding decisions | No old Gazette or manual alone establishes current law. |
| Binding legal interpretation | Controlling Supreme Court holding and other binding court decisions under the applicable hierarchy | Distinguish ratio/holding from party submissions, obiter and later treatment. An old official manual cannot overrule a binding decision. |
| Official restatement of law | Government India Code/Ministry compilations | Strong official reference and discovery source, but if their reproduced wording conflicts with issued Gazette, investigate rather than privileging hosting domain. |
| Practical military procedure and commentary | **Authenticated government-issued MML edition**, relevant official military manuals, MoD instructions and regulations | High-value military reference, especially for unit commanders. Distinguish a regulation/order with independent legal force from commentary/reproduction. Check date and amendments. |
| Independent copies and research | Archival scans, publisher reports, commercial databases and third-party commentary | An **archival facsimile** retains the authority *of its underlying official document* once identity/fidelity are established. A paraphrase/retelling has no such authority. |

An actual Gazette and a government-issued Manual of Military Law are **not equivalent types of authority**. Verify authenticity of the particular MML *edition* before labelling it government issued. Our eight user-supplied MML files have verified byte hashes, but no authenticated publication/printing edition; remain `UNVERIFIED_MANUAL` or a user-supplied reference until evidence warrants more. Never silently promote them to enacted law.

### Archival reproduction of a Government Gazette

**Correct example:** A scanned image of the Gazette of India printed in 1954, hosted on archive.org:
- `source_type=GAZETTE`
- `authenticity=ARCHIVAL_FACSIMILE_OF_OFFICIAL`
- `document_authority=ENACTED_OR_NOTIFIED_PRIMARY`
- `carrier_provenance=THIRD_PARTY_ARCHIVAL_FACSIMILE`
- `instrument_identity`: complete Gazette issue, Part/Section, notification number, date and pages
- `copy_fidelity`: HASH_ONLY until the source page image and identity marks have been checked; then PAGE_IMAGE_CHECKED, or CUSTODIAN_AUTHENTICATED if actually certified
- `amendment_chain_status`: NOT_CHECKED/PARTIAL until applicable subsequent notifications have been examined

Do NOT classify the Gazette's *content* as `THIRD_PARTY_COMMENTARY` merely because archive.org is the carrier. Conversely, do NOT label an archive-hosted scan `ORIGINAL_OFFICIAL` or `CUSTODIAN_AUTHENTICATED` without documentary support.

A verified archival facsimile may establish **historical wording** with its actual provenance and limitations. It does not automatically establish current operative wording and does not require blanket custodian certification for research use. For material authenticity disputes, record the custodian request or legal-advisor evidence-tier decision.

A source-level `SOURCE_VERIFIED` means its identified passage has been inspected against the copy; it does **not** mean the source has been adjudicated as binding/current law. New evidence with `document_authority` and `carrier_provenance` must carry `copy_fidelity`, `instrument_identity` for Gazette facsimiles, and `amendment_chain_status`.

### Conflict resolution checklist

1. Freeze original passages and file/source hashes; log **all** sources and conflicting exact quotations, not a majority vote.
2. Determine which source is the original issued instrument versus an amendment, later compilation, archived facsimile, military manual, judgment, or commentary.
3. Verify original identity, issued date, relevant Gazette part/section/page, scanned printed page (not OCR alone) and independent second reading on consequential negations/numbers.
4. Establish the complete relevant amendment/commencement/corrigendum/savings chain; inspect subsequent binding judgments.
5. Record precise temporal and jurisdictional scope, unresolved alternative readings and any limitations in access, edition or authentication.
6. Only the designated legal advisor may settle a substantive disputed interpretation for a research candidate; formal JAG validation remains a separate gate.
7. Where the chain or legal review is incomplete, retain `CONFLICTING`/`BLOCKED`; do not rewrite originals or mark candidate guidance legally approved.

### Rule 23(3), S.R.O. 484, 27 November 1954 (current example)

- The archive.org image of the *underlying Gazette* is a candidate **primary-document facsimile** and reportedly prints **"not obliged"** on printed p.300; archive.org MD5 matches published checksum. This is historical discovery evidence and is not a certified custodian copy.
- MML copies reproduce "not obliged"; India Code compilation prints without "not". Government-hosted compilation status does **not** erase the contradiction.
- An independent second page-image reading, complete Rule 23 amendment chain from 1954 to the relevant date and legal-advisor decision are outstanding.
- **Do not change any Rule 23(3) finding, underlying text or legal-review status from CONFLICTING at this stage.** A finding cannot become `CURRENT_IN_FORCE` solely because the original 1954 Gazette is located.

## Data rules for new sources

Use the optional-for-legacy fields introduced in `docs/legal-audit/schemas/source.schema.json`:
- `document_authority`: `ENACTED_OR_NOTIFIED_PRIMARY`, `OFFICIAL_JUDICIAL_DECISION`, `GOVERNMENT_COMPILATION`, `GOVERNMENT_ISSUED_MANUAL`, `UNVERIFIED_MANUAL`, `THIRD_PARTY_COMMENTARY`, `UNKNOWN`.
- `carrier_provenance`: `ISSUING_AUTHORITY`, `GOVERNMENT_HOSTED_COPY`, `THIRD_PARTY_ARCHIVAL_FACSIMILE`, `USER_SUPPLIED`, `THIRD_PARTY_TRANSCRIPTION`, `UNKNOWN`.
- `copy_fidelity`: `NOT_CHECKED`, `HASH_ONLY`, `PAGE_IMAGE_CHECKED`, `CUSTODIAN_AUTHENTICATED`.
- `amendment_chain_status`: `NOT_CHECKED`, `PARTIAL`, `CHECKED_FOR_RELEVANT_PERIOD`, `NOT_APPLICABLE`.
- `instrument_identity`: string with official Gazette/notification identity where relevant.
- `authority_rationale`: brief provenance basis, especially where distinguishing facsimile from compilation.

**Mandatory gate for future batches:** Set `"source_authority_policy_version": "v1"` in the new batch's frozen audit manifest and run `validate.py --batch ... --manifest ... --strict`. The validator then requires all four policy fields and `authority_rationale` on **every** source entry; new archival facsimiles also need their instrument identity, hash, and page-image evidence before SOURCE_VERIFIED. Unknown policy versions fail closed.

**Compatibility:** Frozen PILOT-01 source entries remain immutable and may lack these fields; its existing manifest has no new policy flag. Newly declared archival facsimiles and any newly classified source are validated even without the flag. A later migration of old sources must be additive and independently reviewed, not a silent change.

## Official reference links
- Government of India eGazette, Department of Publication: https://egazette.gov.in/
- Central Secretariat Library, Gazette of India description: https://csl.nic.in/index.php/page/innerpage/gazette-of-india.php
- Ministry of Law and Justice, India Code: https://indiacode.gov.in/

**Data-quality policy is source-neutral regarding authorship. Human and AI inputs pass the same tests.**
