#!/usr/bin/env python3
"""C8-B born-digital PDF structure inspection (offline, read-only).

Usage: python -I born_digital.py --pdf <file> --expect-sha256 <hex> --label <id> --work <dir> [--openssl /usr/bin/openssl]

Reports, as JSON on stdout:
  * re-hash vs expected sha256 (stops if mismatch)
  * every %%EOF offset, every startxref value, PDF header offset
  * every signature dictionary found by a raw byte scan for /ByteRange (all of them),
    with /Filter, /SubFilter, /Name, /Reason, /Location, /M, /ContactInfo as printed
  * whether each signed range pair covers the whole file except the /Contents hole,
    bytes after the last signed range
  * pymupdf metadata (producer/creator) and the XMP packet's producer/creator tool, if any
  * OPTIONAL integrity step with ALREADY-INSTALLED openssl: writes the /Contents
    DER blob and the concatenated signed bytes into --work, runs
       openssl cms -verify -inform DER -binary -noverify -purpose any
    (checks the CMS signature over signedAttrs with the embedded signer
    certificate's public key and the messageDigest against the signed bytes;
    -noverify means the certificate chain / trust / revocation is NOT checked),
    and prints the embedded certificates' subject/issuer/validity.
"""
import argparse, hashlib, json, os, re, subprocess, sys
import pymupdf


def field(d, key):
    m = re.search(rb'/' + key + rb'\s*\(((?:\\.|[^\\)])*)\)', d)
    if m:
        return m.group(1).decode('latin-1')
    m = re.search(rb'/' + key + rb'\s*<([0-9A-Fa-f\s]*)>', d)
    if m:
        h = re.sub(rb'\s', b'', m.group(1))
        try:
            b = bytes.fromhex(h.decode())
            if b.startswith(b'\xfe\xff'):
                return b[2:].decode('utf-16-be', 'replace')
            return b.decode('latin-1')
        except Exception:
            return '<hex>' + h.decode()[:80]
    m = re.search(rb'/' + key + rb'\s*/([A-Za-z0-9.#_-]+)', d)
    if m:
        return '/' + m.group(1).decode()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--expect-sha256', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--openssl', default='/usr/bin/openssl')
    a = ap.parse_args()
    data = open(a.pdf, 'rb').read()
    sha = hashlib.sha256(data).hexdigest()
    out = {'label': a.label, 'file': a.pdf, 'bytes': len(data), 'sha256': sha,
           'hash_check': 'MATCH' if sha == a.expect_sha256 else 'MISMATCH'}
    if sha != a.expect_sha256:
        print(json.dumps(out, indent=1)); return 2
    out['pdf_header_offset'] = data.find(b'%PDF-')
    out['pdf_header'] = data[out['pdf_header_offset']:out['pdf_header_offset'] + 8].decode('latin-1')
    out['eof_offsets'] = [m.start() for m in re.finditer(rb'%%EOF', data)]
    out['eof_count'] = len(out['eof_offsets'])
    out['startxref_values'] = [int(m.group(1)) for m in re.finditer(rb'startxref\s+(\d+)', data)]
    last_eof = out['eof_offsets'][-1] if out['eof_offsets'] else None
    out['bytes_after_last_eof_marker'] = (len(data) - (last_eof + 5)) if last_eof is not None else None
    out['trailing_bytes_after_last_eof_hex'] = data[last_eof + 5:].hex() if last_eof is not None else None
    sigs = []
    for m in re.finditer(rb'/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]', data):
        br = [int(x) for x in m.groups()]
        # take the enclosing dictionary window: back to the nearest 'obj', forward to 'endobj'
        start = data.rfind(b' obj', 0, m.start())
        end = data.find(b'endobj', m.end())
        d = data[start:end if end > 0 else m.end() + 20000]
        objnum = None
        mo = re.search(rb'(\d+)\s+(\d+)\s*$', data[max(0, start - 20):start])
        if mo:
            objnum = f"{int(mo.group(1))} {int(mo.group(2))} obj"
        a0, l0, a1, l1 = br
        hole_start, hole_end = a0 + l0, a1
        covers = (a0 == 0 and a1 + l1 == len(data))
        cm = re.search(rb'/Contents\s*<([0-9A-Fa-f]*)>', d)
        contents_hex = cm.group(1) if cm else b''
        contents_abs = (start + cm.start(1) - 1) if cm else None
        s = {'dict_object': objnum, 'dict_offset': start, 'byte_range': br,
             'signed_bytes': l0 + l1, 'hole': [hole_start, hole_end],
             'hole_matches_contents_string': (contents_abs == hole_start and contents_abs + len(contents_hex) + 2 == hole_end) if cm else None,
             'covers_whole_file_except_contents_hole': covers,
             'bytes_after_last_signed_range': len(data) - (a1 + l1),
             'Filter': field(d, b'Filter'), 'SubFilter': field(d, b'SubFilter'),
             'Name': field(d, b'Name'), 'Reason': field(d, b'Reason'),
             'Location': field(d, b'Location'), 'M': field(d, b'M'),
             'ContactInfo': field(d, b'ContactInfo'),
             'contents_hex_len': len(contents_hex)}
        sigs.append((s, contents_hex))
    out['signature_dictionaries'] = [s for s, _ in sigs]
    out['signature_dictionary_count'] = len(sigs)
    out['sig_field_types'] = len(re.findall(rb'/FT\s*/Sig', data))
    out['type_sig_count'] = len(re.findall(rb'/Type\s*/Sig\b', data))
    doc = pymupdf.open(a.pdf)
    md = doc.metadata or {}
    out['pages'] = len(doc)
    out['metadata'] = {k: md.get(k) for k in ('producer', 'creator', 'creationDate', 'modDate', 'format', 'encryption')}
    xmp = doc.get_xml_metadata() or ''
    out['xmp_present'] = bool(xmp)
    for tag in ('pdf:Producer', 'xmp:CreatorTool', 'xmp:CreateDate', 'xmp:ModifyDate'):
        mm = re.search(r'<' + tag + r'>([^<]*)</' + tag + r'>', xmp)
        out['xmp_' + tag.split(':')[1]] = mm.group(1) if mm else None
    ia = [k for k in ('Internet Archive', 'archive.org', 'LuraDocument', 'ABBYY', 'Recoded by') if k.encode() in data]
    out['ia_or_rerender_markers_in_bytes'] = ia
    doc.close()
    # optional CMS integrity step with installed openssl
    os.makedirs(a.work, exist_ok=True)
    checks = []
    for i, (s, hx) in enumerate(sigs):
        br = s['byte_range']
        der = bytes.fromhex(hx.decode()).rstrip(b'\x00')
        sig_p = os.path.join(a.work, f'{a.label}_sig{i}.der')
        con_p = os.path.join(a.work, f'{a.label}_signed{i}.bin')
        open(sig_p, 'wb').write(der)
        open(con_p, 'wb').write(data[br[0]:br[0] + br[1]] + data[br[2]:br[2] + br[3]])
        r = subprocess.run([a.openssl, 'cms', '-verify', '-inform', 'DER', '-in', sig_p, '-content', con_p,
                            '-binary', '-noverify', '-purpose', 'any', '-out', os.devnull],
                           capture_output=True, text=True)
        certs = subprocess.run([a.openssl, 'pkcs7', '-inform', 'DER', '-in', sig_p, '-print_certs', '-noout'],
                               capture_output=True, text=True)
        cmsprint = subprocess.run([a.openssl, 'cms', '-cmsout', '-print', '-inform', 'DER', '-in', sig_p],
                                  capture_output=True, text=True)
        txt = cmsprint.stdout
        dig = re.search(r'messageDigest.*?OCTET STRING:\s*\n?\s*((?:\s*[0-9a-f]{4} - [^\n]*\n?)+)', txt, re.S)
        st = re.search(r'signingTime.*?UTCTIME:([^\n]*)', txt, re.S)
        da = re.findall(r'digestAlgorithm:\s*\n\s*algorithm: ([^\n]*)', txt)
        sa = re.findall(r'signatureAlgorithm:\s*\n\s*algorithm: ([^\n]*)', txt)
        ectype = re.search(r'eContentType: ([^\n]*)', txt)
        econtent_absent = 'eContent: <ABSENT>' in txt
        checks.append({'sig_index': i, 'der_sha256': hashlib.sha256(der).hexdigest(), 'der_bytes': len(der),
                       'signed_content_sha256': hashlib.sha256(open(con_p, 'rb').read()).hexdigest(),
                       'openssl_cms_verify_noverify_rc': r.returncode,
                       'openssl_cms_verify_stderr': r.stderr.strip()[:400],
                       'embedded_certs': certs.stdout.strip(), 'certs_rc': certs.returncode,
                       'cms_eContentType': ectype.group(1).strip() if ectype else None,
                       'cms_eContent_absent(detached)': econtent_absent,
                       'cms_digestAlgorithms': da, 'cms_signatureAlgorithms': sa,
                       'cms_signingTime': st.group(1).strip() if st else None,
                       'cms_messageDigest_raw': re.sub(r'\s+', ' ', dig.group(1)).strip() if dig else None})
    out['cms_checks'] = checks
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
