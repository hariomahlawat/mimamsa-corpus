# Decision note RM-001: FOUO-marked Regulations for the Air Force, Reprinted Edition 2000

**Decision required from:** the owner. A competent authority may need to determine whether the document was released for public use.
**Prepared:** 2026-11-25, Cycle 13. This note records facts only and contains no legal conclusion.

## Facts (verified)

| Item | Value |
| --- | --- |
| Document | Regulations for the Air Force, Reprinted Edition 2000, marked "For Official Use Only" on page 1 (C12 marking scan) |
| Source | Downloaded on 2026-11-21 by the project crawler from the **official India Code portal**: `https://indiacode.gov.in/server/api/core/bitstreams/201b93ce-3dbe-43e3-bf76-257d19ae3310/content` (`data/manifest.csv` row 3939) |
| Original | sha256 `4284820e5bc2fb7f52ae9fbe8a61650f1579e9b6389ba206a916a69fed016b14`, 5,075,455 bytes |
| Derived files | `data/meta/…edition-2000.json` (sha256 `212ac873…`) and `data/text/…edition-2000.txt` (sha256 `f26d3de7…`, the full extracted text) |
| Where held | (1) The private HF dataset, at head and in every revision since it was uploaded. (2) The private GitHub repository, branch `raw-data` (`ad77758d`) and its history, plus every clone, including the session object store `/home/user/c7`. (3) Earlier audit records cite it by sha256; they do not contain its text. |
| Second copy | A different Navy regulations PDF (`68dd1cea…`) only *mentions* the phrase "For Official Use Only" in running text. It is not marked FOUO and is not covered by this note. |

## Controls in place now (Cycle 13)

- `config/restricted_material.json` (RM-001) together with `scripts/restricted_material.py` is the single exclusion list. It covers the original, the meta file, the text file and their hashes.
- `tests/test_legal_audit_restricted_material.py` enforces that coverage.
- The application data contract (`app/contract/`) and every Cycle 13 workstream brief require exclusion of this item from all of the following:
  - release bundles;
  - research publication;
  - search indexes;
  - embeddings;
  - graph publication;
  - external inference;
  - general processing packages;
  - the forms registry.
- Routine operations must not copy, redistribute or delete it.

## Options

| Option | What it means | Implications |
| --- | --- | --- |
| **A. Retain, restricted (current state)** | Keep the bytes where they are. They stay excluded from every derivative and from the app. | No destructive action. The item remains in cloud storage. The fact that it came from an official public portal may bear on whether it is authorised, but a private repository is **not** by itself evidence that cloud storage is authorised. |
| **B. Quarantine** | Stop using the hosted copies and record the item as quarantined. Optionally move it to an owner-controlled offline store. | Moving it is a copy, which is a redistribution and needs approval. Removal from current trees is option C. |
| **C. Remove from current trees** | Delete the three paths at the HF head and in a new GitHub commit. | It stays in **all historical revisions**: earlier HF commits and the git history of `raw-data`. Every verification pin (`5524c3d9`, `ad77758d`, …) still contains it. This is deletion of a source document and needs owner approval. |
| **D. Purge history** | HF history squash and a git history rewrite of `raw-data`. | Destructive. It invalidates every recorded revision pin and the byte-verification evidence. GitHub requires a force-push, which project rules forbid without explicit owner instruction. Clones elsewhere keep copies. Only proportionate if a competent authority determines that storage was unauthorised. |

## Recommendation

1. Keep **option A** with the enforced exclusions while the authorisation question is resolved.
2. Ask the competent authority whether the India Code publication of this edition is an authorised public release.
   - **If it is authorised:** downgrade the item to "publicly published, marking retained", and decide separately whether it may be used in the app.
   - **If it is not authorised:** choose option C, plus option D if the authority requires it. The owner explicitly approves both the deletion and the history implications. A recorded procedure must re-baseline the verification pins.

Nothing in this note authorises deletion, copying, publication or any change of visibility.
