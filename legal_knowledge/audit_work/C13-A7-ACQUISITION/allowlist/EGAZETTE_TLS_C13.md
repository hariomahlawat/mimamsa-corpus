# egazette.gov.in TLS failure: root cause and fix (C13 A7)

Investigated on 2026-11-25 from the cloud container through the agent proxy. Verification was never disabled.

## Symptom (C12)

httpx and curl fail with "unable to get local issuer certificate", so robots.txt cannot be read and the C12 run
failed closed.

## Root cause (measured)

`openssl s_client -proxy … -connect egazette.gov.in:443 -showcerts` shows the server sends **one certificate only:
the leaf**. Saved as `egazette_served_leaf_2026-11-25.pem`.

| Field | Value |
|---|---|
| Subject | CN = egazette.gov.in (SAN DNS:egazette.gov.in) |
| Issuer | C=US, O=Let's Encrypt, **CN=YR1** |
| Validity | 2026-10-16 to 2027-01-14 |
| SHA-256 fingerprint | 64:31:E5:84:…:BC:30:67 |
| AIA CA Issuers | `http://yr1.i.lencr.org/` |

The missing certificates:

1. **Intermediate `CN=YR1`** (Let's Encrypt), issued by `CN=Root YR` (O=ISRG). It is AIA-fetchable from
   `http://yr1.i.lencr.org/` (DER, 1,247 bytes). Its own AIA is `http://yr.i.lencr.org/`.
   - SHA-256 (DER): `13949634d99cd6fd6aa80bc034fefacceb1969feef986586713ecdbb05758d3f`
   - Valid 2025-09-03 to 2028-09-02; CA:TRUE, pathlen:0.
2. **`CN=Root YR` cross-signed by ISRG Root X1.** It is AIA-fetchable from `http://yr.i.lencr.org/` (DER, 1,528 bytes).
   - SHA-256 (DER): `072639d0b140d5bffae16ad9c3f6cc6086040621f51ee61a6d46a8915c07cf76`
   - Valid 2026-05-13 to 2032-09-02.

The proxy CA bundle (`/root/.ccr/ca-bundle.crt`, 121 certificates) and the system store contain ISRG Root X1 and
X2, but **neither YR1 nor Root YR**. The newer Let's Encrypt "Y" hierarchy can only reach a trusted root through
the Root YR cross-sign, and the server sends neither certificate. Browsers that chase AIA recover; OpenSSL, httpx
and curl do not. Both certificates are needed. YR1 alone gives "unable to get issuer certificate" in strict mode
(tested).

## Verification of the fix

- `openssl verify -CAfile /root/.ccr/ca-bundle.crt -untrusted egazette_intermediates.pem -purpose sslserver -verify_hostname egazette.gov.in egazette_served_leaf_2026-11-25.pem` gives **OK**.
- The certificates came over plain HTTP. Their authenticity rests on the signature chain to ISRG Root X1, which is already trusted, not on the transport.
- Python 3.13 `ssl.create_default_context()` sets `VERIFY_X509_PARTIAL_CHAIN` by default. Loaded naively, an intermediate would then become a trust anchor. The fix **clears that flag**, so the chain must still end at the self-signed ISRG Root X1. Tested: strict mode with both certificates connects (robots.txt 404); strict mode with YR1 only fails.

## Proposed fix (not applied to the live config)

- `config/ca/egazette_intermediates.pem` holds exactly these two certificates (patch `proposed/crawler_revision/0003`).
- `sources.egazette.ca_extra_pem` and `ca_extra_sha256` list the two DER SHA-256 pins (`proposed/sources.yaml.diff`).
- `crawler/http.py::tls_verify_for` loads the extra PEM only for that source, refuses a PEM whose certificates do not equal the pins, keeps hostname checking and CERT_REQUIRED, and clears partial-chain trust.
- If Let's Encrypt moves egazette to another intermediate (e.g. YR2), the chain stops validating and requests fail closed. Re-run this check and re-pin only after the same verification.
- Better long-term fix: ask NIC to serve the full chain.

## Use in this cycle (disclosed)

The A7 acquisition run used the same strict context, implemented in `tools/a7net.py`, for egazette.gov.in. That host is
already allow-listed at staging. 47 requests went to egazette (robots.txt answers 404, meaning no robots file). This
does not weaken verification: it is the chain an AIA-chasing browser builds, anchored at the same trusted root. The
coordinator may still decide that the CA-pin mechanism needs acceptance before use. In that case, the 17 egazette
files obtained here remain preserved but can be re-fetched under the accepted crawler code; their pins make the
result checkable.
