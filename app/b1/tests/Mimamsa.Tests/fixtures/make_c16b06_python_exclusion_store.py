"""Generate a real Python ExclusionStore (mimamsa_contract.exclusions) signed with a fixed DEVELOPMENT key, for the
.NET exclusion reader cross-check. Usage (from the repo root):
  python -I app/b1/tests/Mimamsa.Tests/fixtures/make_c16b06_python_exclusion_store.py app/contract app/b1/tests/Mimamsa.Tests/fixtures/c16b06_python_exclusion_store
The key is derived from a fixed public string: a DEVELOPMENT key with no value outside these tests."""
import hashlib, json, shutil, sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from mimamsa_contract.exclusions import ExclusionStore
from mimamsa_contract.trust import parse_trust_list

out = Path(sys.argv[2])
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)
(out / ".gitattributes").write_text("# Signed bytes: never normalise line endings (digests and Ed25519 signatures cover the exact bytes).
* -text
")
seed = hashlib.sha256(b"mimamsa-c16-b06-python-crosscheck-dev-key").digest()
sk = Ed25519PrivateKey.from_private_bytes(seed)
pub = sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
kid = "dev-" + hashlib.sha256(pub).hexdigest()
tl = {"contract_version": "1.0.0", "record_kind": "trust_list", "sequence": 1, "issued_at": "2026-11-27T00:00:00Z",
      "keys": [{"key_id": kid, "public_key_hex": pub.hex(), "holder": "DEVELOPMENT", "purposes": ["register"], "revoked": False}]}
(out / "trust").mkdir()
(out / "trust" / "TRUST_LIST.json").write_text(json.dumps(tl, sort_keys=True), encoding="utf-8")
trust = parse_trust_list(tl)

REG_SHA = "ab" * 32
def register(with_doc):
    items = [{"restriction_id": "RX-0001", "source_sha256": REG_SHA}]
    if with_doc:
        items[0]["doc_id"] = "doc-restricted-1"
    return json.dumps({"items": items}, sort_keys=True)

def update(seq, withdrawals, readmissions=None, with_doc=False):
    reg = register(with_doc)
    u = {"contract_version": "1.0.0", "record_kind": "exclusion_update", "sequence": seq, "issued_at": "2026-11-27T00:00:00Z",
         "register_sha256": hashlib.sha256(reg.encode()).hexdigest(), "register_json": reg, "withdrawals": withdrawals}
    if readmissions is not None:
        u["readmissions"] = readmissions
    return json.dumps(u, sort_keys=True).encode()

store = ExclusionStore(out / "exclusions")
for seq, w, r, d in [
    (1, [{"doc_id": "doc-a", "reason": "withdrawn by owner"}], None, False),
    (2, [{"doc_id": "doc-b", "reason": "withdrawn by owner"}], None, True),
    (3, [{"source_copy_sha256": "cd" * 32, "reason": "copy withdrawn"}], [{"doc_id": "doc-a", "reason": "readmitted on review", "authority_ref": "OWNER-DECISION-0001"}], False),
]:
    b = update(seq, w, r, d)
    store.append(b, sk.sign(b), trust, mode="development")
st = store.effective_state(trust, mode="development")
expected = {"sequence": st.sequence, "tombstone_doc_ids": sorted(st.tombstone_doc_ids), "tombstone_shas": sorted(st.tombstone_shas),
            "restricted_tombstone_doc_ids": sorted(st.restricted_tombstone_doc_ids), "restricted_tombstone_shas": sorted(st.restricted_tombstone_shas)}
(out / "EXPECTED_EFFECTIVE_STATE.json").write_text(json.dumps(expected, sort_keys=True, indent=1) + "\n", encoding="utf-8")
print(json.dumps(expected))
