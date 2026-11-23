# Born-digital Gazettes T1-19 and T1-20: structural findings (C8 Workstream B)

Evidence only. Nothing here approves, activates or changes legal status. The parsing was done by an AI agent (Claude Opus 5.5 subagent); the results are not human-confirmed. Each figure can be reproduced offline with `tools/born_digital.py` and `tools/rsa_diag.py`. The per-file output is in `born_digital/T1-19.json`, `born_digital/T1-20.json` and `born_digital/*_rsa_diag.json` (absolute paths replaced by `<scratchpad>/...`), and is tabulated in `born_digital_structure.csv`.

## Held bytes
| Row | Instrument | Held path (scratchpad) | sha256 (re-hashed 2026-11-23) | Bytes | Result |
| --- | --- | --- | --- | --- | --- |
| T1-19 | S.R.O. 2(E)/2018 | downloads/amendment-search/in.gazette.central.e.2018-02-20.183010/183010.pdf | 7c12a7ecc849c8f6df96830b093fda3c16bf9e943a5cb5d331ae3352b9455551 | 1,707,387 | MATCH |
| T1-20 | S.R.O. 17(E)/2019 | downloads/independent-reviewer-D/amend/in.gazette.central.e.2019-12-28.214956/214956.pdf | 138c1da0d3d9ffafe50603fb810a6d0857c942f845d52e36f355ec8b5add2f8c | 339,524 | MATCH |

## File structure
| Item | T1-19 | T1-20 |
| --- | --- | --- |
| Header | %PDF-1.6 at offset 0 | %PDF-1.6 at offset 0 |
| Linearized | yes; /L = 1,707,387 = file length | yes; /L = 339,524 = file length |
| %%EOF markers | 2 (offsets 853, 1,707,380) | 2 (offsets 917, 339,517) |
| startxref values | 0 (first-page section), 116 | 0, 116 |
| Incremental updates | none detected: the two %%EOF are the linearized first-page section and the main section, there is one /Prev, and /L equals the file length | same |
| Bytes after last %%EOF | 2 (CR LF) | 2 (CR LF) |
| Signature dictionaries (raw scan for every /ByteRange) | 1 (obj 10 0) | 1 (obj 22 0) |
| /ByteRange | [0 260473 1699735 7652] | [0 324995 332029 7495] |
| Signed bytes | 268,125 | 332,490 |
| Unsigned hole | 260473-1699735; exactly the /Contents hex string | 324995-332029; exactly the /Contents hex string |
| Signed ranges cover the whole file except /Contents | YES | YES |
| Bytes after the last signed range | 0 | 0 |
| /Filter, /SubFilter | /Adobe.PPKLite, /adbe.pkcs7.detached | /Adobe.PPKLite, /adbe.pkcs7.detached |
| /Name (as printed, unverified) | RAKESH SUKUL | MANOJ KUMAR VERMA |
| /M (as printed, unverified) | D:20180220192255+05'30' | D:20191228200143+05'30' |
| /Reason, /Location, /ContactInfo | absent | absent |
| Producer / Creator (Info and XMP) | GPL Ghostscript 8.15 / PScript5.dll Version 5.2.2 | GPL Ghostscript 8.15 / PScript5.dll Version 5.2.2 |
| CreationDate / ModDate | D:20180220185951Z / D:20180220192255+05'30' | D:20191228195452Z / D:20191228200143+05'30' |
| Internet Archive or re-render markers in the bytes | none found | none found |
| archive.org metadata snapshot | ACQ-02 snapshot: name, size, md5, sha1 and mtime 1534716964 match; no `source` (original or derivative) field is recorded | ACQ-01 snapshot: `files[].source = original`; md5 and size match |
| Visible signature appearance | p.2: "Digitally signed by RAKESH SUKUL Date: 2018.02.20 19:22:55 +05'30'" (C8-PIC-37) | none on p.2; on PDF p.6, the last page, bottom right: "Digitally signed by MANOJ KUMAR VERMA Date: 2019.12.28 20:01:43 +05'30'", with one Signature widget on that page (C8-PIC-40, rendered after review 5212a95b; the small type was read from the text layer). Its time equals /M and ModDate. It is an appearance, not a validation |
| Instruments in the file | S.R.O. 2(E)/2018 only (Hindi p.1, English p.2) | five: S.R.O. 17(E)/2019 (pp.1-2), and on pp.3-6 S.R.O. 18(E) and 19(E) (Navy regulations), 20(E) (Air Force (Amendment) Rules, 2019) and 21(E) (Air Force (Amendment) Regulations, 2019), all dated 28-12-2019 and signed M. SUBBARAYAN. pp.3-5 were read from the text layer only. An entry would cover the whole copy |

## CMS signature (integrity checks with installed tools only)
- Method: `openssl cms -verify -inform DER -binary -noverify -purpose any` (OpenSSL 3.0.13, already installed). The /Contents DER was used as the signature and the concatenated signed ranges as the detached content. An independent raw-RSA check (`tools/rsa_diag.py`, Python `cryptography`, already installed in the venv) computed s^e mod n for every embedded certificate.
- **T1-19:**
  - "CMS Verification successful".
  - messageDigest = SHA-256 of the signed ranges = 7785d388e7bc88729d7389754d54fe811fb8ee1c9d21f14c032260f6e86ad38d.
  - The RSA signature (sha256WithRSAEncryption) decodes to a well-formed PKCS#1 v1.5 block, and its DigestInfo equals SHA-256 of the signedAttrs SET. It does so only for the embedded certificate CN=RAKESH SUKUL (O=GOVT OF INDIA PRESS, OU="DTR OF PRINTING,CID - 4751192"; serial 5352D5F2 = SignerInfo sid 1397937650; validity 2016-10-29 to 2018-10-29). That certificate was issued by "(n)Code Solutions CA 2014", which was issued by "CCA India 2014"; all three certificates are embedded.
  - An Adobe revocation-information attribute (1.2.840.113583.1.1.8) of about 714 KB is present. It was not examined.
- **T1-20:**
  - "CMS Verification failure ... RSA_padding_check_PKCS1_type_1: invalid padding".
  - messageDigest = SHA-256 of the signed ranges = 739566ad9d5ff3ae8b8f6cf380fb1541c29a64fd3b7c134bf8e1a012e21c49a2 (it matches).
  - The RSA signature value does **not** decode to a PKCS#1 v1.5 block with the only embedded certificate. That certificate is CN=MANOJ KUMAR VERMA (O=GOVT. OF INDIA PRESS; serial 5391176F = SignerInfo sid 1402017647; validity 2018-06-11 to 2020-06-10; issuer "(n)Code Solutions CA 2014"). No issuer certificate is embedded, and the revocation attribute is an empty SEQUENCE.
  - The cause is UNCERTAIN. It could be a signing-software defect at origin, a wrong certificate embedded, or alteration of the signature value. The held bytes cannot tell these apart. The page text itself is CONFIRMED (C8-PIC-38, C8-PIC-39). Recorded as **C8-CR-03 (OPEN)**. The visible appearance on p.6 carries the same time as /M (2019.12.28 20:01:43 +05'30'); this does not bear on why the signature value fails.
- **What was NOT done, for either file:**
  - no certificate-chain building or validation;
  - no trust anchor (CCA India) check;
  - no check of validity at signing time against a trusted time source (signingTime is absent and no timestamp token was found);
  - no revocation (CRL or OCSP) check;
  - no comparison with an egazette.gov.in copy (unreachable offline).

  The T1-19 result therefore shows only that the signed bytes are internally consistent with a signature made with the key of the embedded RAKESH SUKUL certificate. It does not show that the certificate was valid, trusted or unrevoked, and it does not prove documentary authenticity.

## Recommendations (source-specific)
- **T1-19, S.R.O. 2(E)/2018: HOLD_FIDELITY_DECISION (owner decision P-D2).**
  - The structure is clean:
    - one signature;
    - signed ranges span the file except /Contents;
    - no incremental update;
    - no trailing bytes beyond CR LF;
    - origin-type producer;
    - no Internet Archive marker.
  - CMS integrity passes.
  - What would allow validation:
    1. Run an offline chain validation against a pinned CCA India 2014 root, using the embedded intermediate (n)Code Solutions CA 2014 and the embedded revocation archive (1.2.840.113583.1.1.8), with a reviewed, pinned validator (for example pyHanko). This needs an owner-approved install, which was not done here.
    2. Compare bytes or page text with the egazette.gov.in copy of No. 02 of 20-02-2018, if one can be obtained.
    3. Get the owner's P-D2 position on whether a spanning-range born-digital copy stays primary without validation.
- **T1-20, S.R.O. 17(E)/2019: NEEDS_FURTHER_EVIDENCE (and still subject to P-D2).**
  - The ByteRange spans the file, which earned the class `BORN_DIGITAL_SIGNED_RANGE_SPANS_FILE`. The signature value nevertheless fails integrity with the embedded certificate.
  - P-D2 as drafted ("spanning range, not validated") does not address a signature that is checked and **fails**.
  - Before any fidelity decision:
    1. Obtain an independent copy of Extraordinary No. 13 of 28-12-2019 (egazette.gov.in, or another archive with recorded provenance) and compare bytes and signature.
    2. Failing that, record the failure as a limitation the owner explicitly accepts.
    3. Optionally re-run validation with a reviewed validator to rule out a parser issue. Two independent methods (OpenSSL and a raw RSA computation) agree on the failure.

## Effect on earlier records
- `AUTH-LEDGER/evidence/copy_structure.csv` and matrix v11 record "signature byte range ... covers file: YES; NOT CRYPTOGRAPHICALLY VERIFIED". C8 confirms the range facts exactly. The C8 integrity checks add one positive finding (T1-19) and one adverse finding (T1-20).
- F-T1-3 in `TRANCHE1_FINDINGS.md` ("Each file has an embedded signature byte range that spans the file") remains accurate. It should not be read as signature validity.
