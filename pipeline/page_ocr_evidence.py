"""Page-level OCR evidence candidates. No OCR invocation, writes or release.

The exact PDF bytes are rehashed and its physical page is rendered here. The
OCR claimant must identify that exact render. The receipt binds the supplied
TSV, not the truth of its transcription or the identity of an external engine.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import re

MAX_SOURCE = 50_000_000
MAX_PIXELS = 12_000_000
MAX_TSV = 8_000_000
DPI = 150


def sha(b):
    return hashlib.sha256(b).hexdigest()


def receipt(raw, source_sha256, physical_page, tsv, *, claimed_image_sha256,
            engine_version, languages, native_text=None):
    import pymupdf
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_SOURCE or sha(raw) != source_sha256:
        raise ValueError('source binding failure')
    if not raw.rstrip().endswith(b'%%EOF'):
        raise ValueError('source EOF not established')
    if not isinstance(tsv, bytes) or not 0 < len(tsv) <= MAX_TSV:
        raise ValueError('bounded TSV bytes required')
    if not isinstance(engine_version, str) or not 0 < len(engine_version) <= 120:
        raise ValueError('engine claim required')
    if not isinstance(languages, str) or not re.fullmatch(r'[a-z]{3}(?:\+[a-z]{3})*', languages):
        raise ValueError('unsupported language claim')
    with pymupdf.open(stream=raw, filetype='pdf') as pdf:
        if pdf.needs_pass or pdf.is_repaired or not pdf.is_pdf or not 0 < pdf.page_count <= 500:
            raise ValueError('unsupported source')
        if type(physical_page) is not int or not 1 <= physical_page <= pdf.page_count:
            raise ValueError('physical page out of bounds')
        page = pdf[physical_page-1]
        scale = DPI/72
        if (math.ceil(page.rect.width*scale)+2)*(math.ceil(page.rect.height*scale)+2)>MAX_PIXELS:
            raise ValueError('render pixel budget exceeded')
        pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY, alpha=False)
        if pix.width*pix.height > MAX_PIXELS:
            raise ValueError('render pixel budget exceeded')
        image = pix.tobytes('png')
        if sha(image) != claimed_image_sha256:
            raise ValueError('OCR claim refers to different rendered bytes')
        actual_native = page.get_text('text')
        if native_text is not None and native_text != actual_native:
            raise ValueError('native text not bound to source')
        frame = dict(viewport=list(page.rect), cropbox=list(page.cropbox),
                     rotation=page.rotation, width=pix.width, height=pix.height,
                     dpi=DPI, colorspace='GRAY', renderer=str(pymupdf.VersionBind))
    fields = ['level','page_num','block_num','par_num','line_num','word_num',
              'left','top','width','height','conf','text']
    reader = csv.DictReader(io.StringIO(tsv.decode('utf-8')), delimiter='\t', quoting=csv.QUOTE_NONE)
    if reader.fieldnames != fields:
        raise ValueError('unexpected TSV header')
    words = []
    keys = set()
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError('malformed TSV row')
        level = int(row['level'])
        if level not in (1,2,3,4,5):
            raise ValueError('invalid TSV level')
        if int(row['page_num']) != 1:
            raise ValueError('TSV must describe a single rendered image')
        if level != 5:
            continue
        key = tuple(int(row[k]) for k in ('block_num','par_num','line_num','word_num'))
        if min(key) < 1 or key in keys:
            raise ValueError('duplicate or invalid word identity')
        keys.add(key)
        x,y,w,h = (int(row[k]) for k in ('left','top','width','height'))
        conf = float(row['conf'])
        if not (0 <= x < x+w <= frame['width'] and 0 <= y < y+h <= frame['height']
                and math.isfinite(conf) and 0 <= conf <= 100 and row['text'].strip()):
            raise ValueError('invalid word box or confidence')
        words.append((key, row['text'], conf))
        if len(words) > 100_000:
            raise ValueError('word budget exceeded')
    # OCR confidence is engine-reported, not an accuracy or authenticity claim.
    text = ' '.join(word[1] for word in words)
    flags = []
    if not words:
        flags.append('BLANK_OR_UNREADABLE_UNADJUDICATED')
    elif min(w[2] for w in words) < 70:
        flags.append('LOW_WORD_CONFIDENCE')
    if re.sub(r'\s+', ' ', actual_native).strip() != re.sub(r'\s+', ' ', text).strip():
        flags.append('NATIVE_OCR_TEXT_DIFFERENCE')
    out = dict(schema='c14-ocr-evidence-v1', source_sha256=source_sha256,
               physical_page=physical_page, image_sha256=sha(image), frame=frame,
               tsv_sha256=sha(tsv), native_text_sha256=sha(actual_native.encode()),
               ocr_text_sha256=sha(text.encode()), engine_version_claim=engine_version,
               languages_claim=languages, word_count=len(words),
               minimum_word_confidence=min((w[2] for w in words), default=None),
               flags=flags, visual_concordance='NOT_INDEPENDENTLY_VALIDATED',
               research_eligible=False, eligible_for_exact_anchor=False,
               eligible_for_documentary_review=False, usable_for_negative_evidence=False)
    out['ocr_evidence_id']=sha(json.dumps(out, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())
    return out
