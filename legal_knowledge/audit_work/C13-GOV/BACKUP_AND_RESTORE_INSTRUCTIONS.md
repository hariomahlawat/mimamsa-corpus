# Second persistent backup: owner instructions (Cycle 13)

**Status: no verified second backup exists yet.** The Hugging Face dataset is the only verified persistent store. The ZIP of the 48 copies delivered in Cycle 12 (SHA-256 `214f11e8…`) has not been verified on owner storage. The temporary session copies stay in place until the steps below have passed on owner-controlled storage.

## 1. Create the backup
Run this on a machine with network access and a Hugging Face credential in the environment.

```
python scripts/backup_corpus.py create --revision <pinned HF commit> --dest <empty folder>
```

- Use the current HF head, recorded in the latest GitHub audit record, or a release revision.
- **Size:** about 2.0 GB at revision `3864faf3`, for 16,041 files.
- **What the tool checks:** it downloads every file at the pinned revision and hashes the actual bytes. It checks each one against Hugging Face's LFS SHA-256 or git blob id, then writes `SHA256SUMS` and `BACKUP_MANIFEST.json`.
- **Restricted items:** items in `config/restricted_material.json` (RM-001) are excluded and listed in the manifest.
- **Exit codes:** `0` means every file is byte-verified. Any `MISMATCH` returns non-zero and lists the affected files.

## 2. Copy the backup to owner-controlled storage
Use offline, access-controlled media of your choice. The backup folder holds three things: `data/`, `SHA256SUMS` and `BACKUP_MANIFEST.json`.

## 3. Restore and verify on the storage medium
Read the backup back from the medium. Ideally restore it onto a different machine.

```
python scripts/backup_corpus.py verify --dest <restored folder>
```

or

```
sha256sum -c SHA256SUMS
```

Expected result: `failed: 0` and `unexpected_files: 0`.

## 4. Record the result
Add a line to `legal_knowledge/audit_work/C13-GOV/BACKUP_REGISTER.csv` containing:
- the date;
- the revision;
- the storage identifier (no sensitive location details);
- the file count;
- the verify result;
- the verifier.

Once a verified line exists, the owner may separately authorise release of the temporary session copies.

The project agents can run steps 1 and 3 in a session and record the result. Only the owner can carry out step 2 and confirm where the backup is stored.
