# Release importer (source fidelity)

The first piece of application code, written in response to ASR-E05 from PR #54. It is build-side and site-side Python. It imports a contract-v1 release bundle into a content-addressed vault and a release generation. Nothing becomes servable until it has been verified against the **bundled bytes**; schema validation alone is not enough.

| Step | Check | On failure |
| --- | --- | --- |
| 1 | Contract validation: signature, checksums, schema, rules, restricted register (RM-001 and others) | Import refused. Nothing is written; the active generation is unchanged |
| 0 | Replay protection: the active generation's `release_sequence` is read from the site (older or equal refused unless rollback); an identical re-import is a no-op; an existing generation is never rewritten | Refused, no write |
| 2 | Each document's original: bundled bytes exist with the claimed SHA-256; size equals `bytes`; vault key equals `vault/sha256/<2>/<sha>`; content type **detected from the bytes** equals the declared MIME type; measured physical page count equals `page_count` (PDF via pypdfium2; text/plain as form-feed pages; other types unverifiable) | **Activation refused** for the whole generation; previous generation keeps serving; vault untouched |
| 3 | Each derivative: declared source is the verified copy of its doc_id; text file bundled with matching SHA-256; declared pages are physical pages of the original with matching `char_count`; passages lie inside their page and hash to `text_sha256` | Item **UNRESOLVED** (quarantined with reasons); never servable |
| 4 | Each candidate anchor: copy is the source document's own copy (or declared alternate) and verified; page is a physical page of that copy; a bound span's offsets (either or both, with or without passage id) lie inside the verified page/passage and its declared text hash equals the hash recomputed from the verified text; unbound spans are served page-only with their fields stripped | Item **UNRESOLVED**; never servable |
| 5 | Verified originals are written once into the vault and **retained across generations**; the append-only held-copies index is updated; the generation is built in a temporary directory (fsync) and renamed into place; `ACTIVE` is switched by temp file, fsync, rename and directory fsync (directory fsync is skipped on Windows, where NTFS durability is proven in P8) | Previous generations retained |

**Page text format.** Page N is the text after its `[[page N]]` marker line, up to the next marker line. The single newline before the next marker, or at the end of the file, is removed.

**Serving decision:** `servable(site, kind, id, exclusions=store.effective_state(trust))` returns true only when the item is verified in the ACTIVE generation and is not withdrawn or restricted. If an exclusion store exists, `exclusions=None` fails closed. **Citations:** `cite()` implements `app/design/policies/citation_resolution.json`.

**Not covered yet:** page-image comparison for OCR (see DA-04), database and index loading, the UI and the Windows service wrapper (P5/P6).

```
pip install -r app/importer/requirements.txt
cd app/importer && python -m pytest -q tests
python da_cases.py --observations obs.json     # observations for PR #54's comparator
```

PR #54 case results are in [RESULTS_DA.md](RESULTS_DA.md).
