# Cloud WP1 execution on an isolated Linux host

GitHub Actions runs synthetic tests for WP1. The repository’s environment admits a branch name, and the plan in use does not provide an independently enforced approval boundary for the branch. The corpus credential belongs only on the dedicated execution host. The default-branch stub is optional and displays a notice. It grants no execution authority.

## Owner prerequisites

- Remove the temporary WP1 Hugging Face secret from GitHub and revoke that credential if it was provisioned. Remove the former activation variable. The workflow changes do not alter repository settings.
- Provision a dedicated, non-root Linux service account on an isolated cloud host with a persistent local filesystem. GitHub contributors and Actions have no access to this host, its account, or its provisioning. Restrict outbound traffic to the infrastructure required for verified TLS to Hugging Face. Use a dedicated byte-preserving checkout reviewed by full Git SHA. Do not auto-update it from a moving branch.
- Install the owner Ed25519 public PEM as root-owned `/etc/mimamsa/wp1-owner.pem`. Create root-owned `/etc/mimamsa/wp1-deployment` containing one deployment-unique 64-character lowercase hex value. Neither file nor their parent directories may be group- or world-writable. The private signing key stays with the owner. Provision root-controlled `/var/lib/mimamsa-wp1` and a persistent `jobs` child owned by the service account with mode `0700`. Preserve claimed job directories even when the run fails.
- Prepare a new temporary token with one exact fine-grained read grant for the private dataset. The application verifies the grant before listing any tree. Use a trusted local console on the host. Keep the detailed receipt under the private job directory.

## Prepare and execute one operation

From the reviewed checkout on that host, using reviewed Python 3.12 with `cryptography==50.0.2` installed, set the accepted Git commit SHA and a fresh job name. The command's expected HF revision is `f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc`. The owner must confirm it against the approved dataset history before signing. Do not open or download source documents.

```bash
umask 077
runner="$PWD/legal_knowledge/audit_work/C14-CA01-STATUTORY/runner/hf_metadata_cloud.py"
boot="import runpy,sys; from pathlib import Path; p=sys.argv.pop(1); sys.path.append(str(Path(p).parent)); runpy.run_path(p,run_name='__main__')"
commit='<full independently accepted Git SHA>'
job='wp1-<fresh-lowercase-job-id>'
python -I -B -c "$boot" "$runner" --prepare-approval \
  --code-commit "$commit" --job-name "$job" > approval.json
```

Review the exact approval JSON, including the deployment, HF revision, seven roots, code and runtime digests, job name and expiry. On the trusted signing system, sign the exact bytes with `openssl pkeyutl -sign -rawin -inkey "$owner_private_key" -in approval.json -out approval.sig`. Transfer the approval and detached signature to the dedicated host. Run only after separate owner authorization.

```bash
python -I -B -c "$boot" "$runner" --execute \
  --code-commit "$commit" --job-name "$job" --approval approval.json --signature approval.sig
```

The launcher verifies the host-installed key and signed scope, then atomically claims the job before asking for a hidden interactive token. Each claimed name is permanently consumed in that deployment. A failed job requires a fresh name and a new approval. The worker takes the token through a local pipe and uses only bounded HTTPS metadata requests. No source downloads, HF writes, or legal promotions are authorized.

The private `metadata_inventory.json` is published atomically without replacement. A failed write leaves no partial receipt at that name. Exit 0 signals complete scoped reconciliation, exit 1 signals a finalized incomplete receipt, and exit 2 signals refusal or failed publication. The console reports aggregate status, counts and the receipt SHA-256. Independently compare that digest before accepting a receipt. Share only safe aggregates, and revoke the token after completion or failure. Never use a partial inventory or this metadata-only receipt as acquisition approval.
