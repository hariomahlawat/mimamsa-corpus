"""Synthetic N01 fixture PDF, REUSED verbatim from the Codex reference PoC
codex/c13-n01-poc @ fbeda3745b21047278b3477a7db3d701d69994bf, app/poc/p4_pdf/harness.py::make_pdf.
Reused so that the PR #54 transport oracle fixtures (396,871 bytes, sha256 975782a1...) describe the same bytes."""

EXPECTED_SHA256 = "975782a1688d037b4916bfe7dbd9c711b286873dc0e38f124daababe658380e6"


def make_pdf():
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids = []
    for page in range(1, 13):
        number = len(objects) + 1
        kids.append(f'{number} 0 R')
        objects.append(
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 200] /Resources '
            f'<< /Font << /F1 3 0 R >> >> /Contents {number+1} 0 R >>'.encode())
        visible = f'BT /F1 20 Tf 40 100 Td (Synthetic page {page}) Tj ET\n'.encode()
        padding = b'%' + (b'x' * 32768) + b'\n'
        stream = visible + padding
        objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'endstream')
    objects[1] = f'<< /Type /Pages /Count 12 /Kids [{" ".join(kids)}] >>'.encode()
    pdf = bytearray(b'%PDF-1.4\n')
    offsets = []
    for index, data in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f'{index} 0 obj\n'.encode() + data + b'\nendobj\n')
    xref = len(pdf)
    pdf.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode())
    pdf.extend(f'trailer\n<< /Root 1 0 R /Size {len(objects)+1} >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(pdf)
