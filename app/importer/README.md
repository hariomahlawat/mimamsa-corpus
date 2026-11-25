# Release importer (source fidelity)

The first piece of application code, written in response to ASR-E05 from PR #54. It is build-side and site-side Python. It imports a contract-v1 release bundle into a content-addressed vault and a release generation. Nothing becomes servable until it has been verified against the **bundled bytes**; schema validation alone is not enough.

| Step | Check | On failure |
| --- | --- | --- |
| 1 | Contract validation: signature, checksums, schema, rules, restricted register (RM-001 and others) | Import refused. Nothing is written; the active generation is unchanged |
| 2 | Each document's original: bundled bytes exist with the claimed SHA-256; size equals `bytes`; vault key equals `vault/sha256/<2>/<sha>`; measured physical page count equals `page_count` (PDF via pypdfium2; text/plain as form-feed pages; other types unverifiable) | **Activation refused** for the whole generation; previous generation keeps serving; vault untouched |
| 3 | Each derivative: declared source is the verified copy of its doc_id; text file bundled with matching SHA-256; declared pages are physical pages of the original with matching `char_count`; passages lie inside their page and hash to `text_sha256` | Item **UNRESOLVED** (quarantined with reasons); never servable |
| 4 | Each candidate anchor: copy is the source document's own copy (or declared alternate) and verified; page is a physical page of that copy; a bound span resolves to a verified derivative passage with offsets inside it | Item **UNRESOLVED**; never servable |
| 5 | Verified originals are written once into the vault; the generation (servable and quarantine lists, candidate evidence) is written; the `ACTIVE` pointer is switched atomically | Previous generations retained |

**Page text format.** Page N is the text after its `[[page N]]` marker line, up to the next marker line. The single newline before the next marker, or at the end of the file, is removed.

**Not covered yet:** page-image comparison for OCR (see DA-04), database and index loading, the UI, exclusion re-application on activation (uses `ExclusionStore.effective_state`; B2) and the Windows service wrapper (P5/P6).

```
pip install -r app/importer/requirements.txt
cd app/importer && python -m pytest -q tests
python da_cases.py --observations obs.json     # observations for PR #54's comparator
```

PR #54 case results are in [RESULTS_DA.md](RESULTS_DA.md).
