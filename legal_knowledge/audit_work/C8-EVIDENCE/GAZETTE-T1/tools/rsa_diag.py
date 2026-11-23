#!/usr/bin/env python3
"""Diagnose a CMS SignerInfo RSA signature (offline, installed tools only).

Usage: python -I rsa_diag.py <sig.der> <signed_content.bin> [--openssl /usr/bin/openssl]

Locates (via `openssl asn1parse`) the last SignerInfo's signedAttrs [0] (depth 5) and
its RSA signature OCTET STRING (depth 5), then, for EVERY certificate embedded in the
CMS, performs the raw RSA public operation s^e mod n and reports whether the result
is a well-formed PKCS#1 v1.5 type-1 block, the DigestInfo it carries, and whether that
digest equals SHA-256(DER(SET OF signedAttrs)) and/or SHA-256(signed content).
This is a diagnostic of signature-value consistency only. It does NOT check any
certificate chain, trust anchor, validity period or revocation.
"""
import argparse, hashlib, json, re, subprocess
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7

ap = argparse.ArgumentParser()
ap.add_argument('sig'); ap.add_argument('content')
ap.add_argument('--openssl', default='/usr/bin/openssl')
a = ap.parse_args()
der = open(a.sig, 'rb').read()
content = open(a.content, 'rb').read()
lines = subprocess.run([a.openssl, 'asn1parse', '-inform', 'DER', '-in', a.sig], capture_output=True, text=True).stdout.splitlines()
sa = sig = None
for ln in lines:
    m = re.match(r'\s*(\d+):d=(\d+)\s+hl=(\d+)\s+l=\s*(\d+)\s+(prim|cons):\s+(.*)', ln)
    if not m:
        continue
    off, d, hl, l = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    kind = m.group(6)
    if d == 5 and kind.startswith('cont [ 0 ]'):
        sa = (off, hl, l)
    if d == 5 and kind.startswith('OCTET STRING') and l in (128, 256, 384, 512):
        sig = (off, hl, l)
out = {'signedAttrs_at': sa, 'signature_at': sig}
attrs = der[sa[0]:sa[0] + sa[1] + sa[2]]
attrs_set = b'\x31' + attrs[1:]
h_attrs = hashlib.sha256(attrs_set).hexdigest()
h_content = hashlib.sha256(content).hexdigest()
out['sha256_signedAttrs_SET'] = h_attrs
out['sha256_signed_content'] = h_content
s = int.from_bytes(der[sig[0] + sig[1]:sig[0] + sig[1] + sig[2]], 'big')
res = []
for c in pkcs7.load_der_pkcs7_certificates(der):
    pub = c.public_key()
    try:
        n, e = pub.public_numbers().n, pub.public_numbers().e
    except Exception:
        continue
    k = (n.bit_length() + 7) // 8
    em = pow(s, e, n).to_bytes(k, 'big')
    ok = em[:2] == b'\x00\x01'
    di = None
    if ok:
        i = em.find(b'\x00', 2)
        ok = ok and all(b == 0xff for b in em[2:i])
        di = em[i + 1:].hex()
    res.append({'cert_subject_CN': c.subject.rfc4514_string()[:160], 'modulus_bits': n.bit_length(),
                'pkcs1_type1_wellformed': ok, 'digestinfo_hex': di,
                'digest_equals_sha256_signedAttrs': bool(di and di.endswith(h_attrs)),
                'digest_equals_sha256_content': bool(di and di.endswith(h_content)),
                'em_prefix_hex': em[:16].hex()})
out['per_certificate'] = res
print(json.dumps(out, indent=1))
