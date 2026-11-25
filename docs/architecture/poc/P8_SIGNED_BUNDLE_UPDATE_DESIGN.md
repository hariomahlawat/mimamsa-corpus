# P8 design note: signed offline update bundles (C13 B-PoC)

Status: DESIGN ONLY. Nothing here was built or run in Cycle 13. Any key mentioned is a disposable development key and
must never be used for a real release.

## Goal

The offline Windows installation receives corpus, index and model updates on removable media. It must accept only
bundles produced by the project, detect tampering or corruption, activate a bundle atomically, and roll back to the
previous good state if activation fails.

## Bundle format

```
mimamsa-bundle-<channel>-<yyyymmdd>-<seq>/
  manifest.json          # bundle_id, created_at, channel, min_app_version, parent_bundle_id, schema versions,
                         # restricted_list_commit, files: [{path, sha256, bytes, role}], change_list
  manifest.json.sig      # raw 64-byte Ed25519 signature over the exact manifest.json bytes
  payload/...            # data, index segments, ONNX models, app binaries (optional)
  SHA256SUMS             # convenience copy for manual checks; NOT trusted on its own
```

- The signature covers the manifest only, and the manifest pins every payload file by SHA-256. This keeps
  verification streaming-friendly and avoids signing gigabytes.
- `parent_bundle_id` allows delta bundles; a delta is refused unless the parent is the currently active bundle.
- `restricted_list_commit` records which version of `config/restricted_material.json` the build excluded.
  The build fails if any payload file matches a restricted `source_sha256` or `derived_sha256`, a restricted
  `doc_id`, or a restricted path. The importer repeats this check from its own pinned copy.

## Keys

- The algorithm is Ed25519 (RFC 8032), using `cryptography` in Python. For .NET: it is NOT VERIFIED in this
  cycle whether the .NET 10 BCL exposes Ed25519. If it does not, use NSec (MIT, libsodium) or BouncyCastle
  (MIT). This has to be checked before any build.
- Development key: generated per developer, kept in the scratch directory, never committed, and labelled `DEV`.
  Bundles signed with it carry `channel: "dev"`. Production installs reject the dev channel.
- Release key: generated offline on an air-gapped machine and kept on a hardware token or under split custody.
  Its public key is embedded in the application and also shipped in a separate `trusted_keys.json`. That file is
  itself signed by a root key, which allows rotation.
- Rotation: `trusted_keys.json` lists the key id, public key, valid_from, valid_to and revoked. A bundle names its
  key id. The importer refuses expired or revoked keys.

## Import and verification steps (importer service, dedicated low-privilege account)

1. Copy the bundle from removable media into `staging\<bundle_id>\`, an ACL-restricted folder that the importer
   account alone can write. Never read it in place from the media.
2. Parse `manifest.json` with a size limit (e.g. 10 MB) and a strict JSON schema.
3. Verify `manifest.json.sig` with the trusted public key for the named key id. Stop on failure.
4. Check the channel, `min_app_version`, `parent_bundle_id` and monotonic `created_at`. Refuse a downgrade unless
   it is an explicit, signed rollback bundle.
5. For every payload file: the path must be normalised and inside `payload/`, with no `..`, no absolute paths, no
   alternate data streams, no reparse points or symlinks. Check the byte count and SHA-256. Refuse any file that is
   not listed.
6. Repeat the restricted-material check.
7. Run the bundle's self-test: open the index, run 10 canned queries with known expected doc_ids, load each ONNX
   model, and embed one string, comparing it to the expected vector within a tolerance.

## Atomic activation and rollback

- Layout: `C:\ProgramData\Mimamsa\bundles\<bundle_id>\`, one folder per installed bundle. A small
  `active.json` holds the active bundle_id and the previous one.
- Activation:
  1. Stop or drain the search service: it reads `active.json` at start and on a signed "reload" control message.
  2. Write `active.json.tmp`, then call `MoveFileEx(..., MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)`,
     which is an atomic rename on NTFS within one volume (`os.replace` / `File.Replace`).
  3. Start the services. If the health check and self-test do not pass within N seconds, swap `active.json` back
     to the previous bundle and restart.
- Database parts (PostgreSQL): load into a new schema `bundle_<id>`. Activation is one transaction that changes
  the `search_path` default or swaps views (`CREATE OR REPLACE VIEW ... AS SELECT ... FROM bundle_<id>.x`).
  Rollback points the views back. Old schemas are dropped only after K successful days.
- Retention: keep the last 2 good bundles. Keep a delta's parent until a newer full bundle is active.

## Audit

Every import writes an append-only log entry with: bundle_id, manifest sha256, key id, verification result per
step, operator, time, activation result and rollback reason. The log is hash-chained, so each entry includes the
previous entry's hash.

## Open items needing owner decisions

- Who holds the release key. Hardware token vs split custody.
- Whether app binaries travel in the same bundle as data. The recommendation is separate channels, so a data
  update cannot change code.
- Whether an MSI/MSIX code-signing certificate (Authenticode) is also required for the binaries. It is
  recommended, and it is separate from the Ed25519 data signature.
