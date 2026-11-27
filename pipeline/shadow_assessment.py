"""CA-03 read-only assessment prototype. Not called by the legacy pipeline."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

from . import relevance_states, text_quality

VERSION = 'c14-shadow-v3'
MAX_BYTES = 50_000_000
MAX_PAGES = 500


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bind_raw(root, relative, expected_sha, *, expected_bytes=None):
    root = Path(root).resolve()
    if not isinstance(relative, str) or not re.fullmatch(r'data/raw/[A-Za-z0-9_./-]+\.pdf', relative):
        raise ValueError('invalid raw path')
    if any(p in ('', '.', '..') for p in relative.split('/')):
        raise ValueError('invalid path segment')
    path = root / relative
    if path.resolve() != path or not path.resolve().is_relative_to(root / 'data' / 'raw'):
        raise ValueError('path containment failure')
    limit = MAX_BYTES if expected_bytes is None else expected_bytes
    if type(limit) is not int or not 0 < limit <= MAX_BYTES:
        raise ValueError('invalid declared raw size')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if expected_bytes is not None and len(raw) != expected_bytes:
        raise ValueError('declared size mismatch')
    if len(raw) > MAX_BYTES or sha(raw) != expected_sha:
        raise ValueError('raw size or hash mismatch')
    return raw


class _ScopeMismatch(ValueError):
    """Observed source metadata conflicts with the declared batch scope."""


def assess(root, meta, *, decide_fn=None, quality_fn=None, declared_bytes=None):
    """Derive an immutable candidate assessment from raw bytes, not stale text.

    Native extraction only. OCR results, verified blank-page exemptions and
    legal/research release eligibility are deliberately not adopted here.
    A bounded batch also requires its declared byte size, digest, and page count
    to match before examining individual pages.
    """
    result = {'version': VERSION, 'doc_id': None, 'source_sha256': None,
              'classifier_mode': 'default_c13' if decide_fn is None else 'injected_test',
              'quality_mode': 'default_c13' if quality_fn is None else 'injected_test',
              'classifier_version': relevance_states.POLICY_VERSION if decide_fn is None else None,
              'quality_version': text_quality.POLICY_VERSION if quality_fn is None else None,
              'metadata_sha256': None, 'eligible_for_documentary_review': False,
              'source_integrity': 'UNVERIFIED', 'pages': [], 'research_eligible': False,
              'relevance': 'EXTRACTION_FAILED', 'text_sha256': None, 'reasons': []}
    try:
        if not isinstance(meta, dict) or not isinstance(meta.get('doc_id'), str) or not meta['doc_id'].strip():
            raise ValueError('invalid metadata identity')
        if not isinstance(meta.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', meta['sha256']):
            raise ValueError('invalid source hash')
        result.update(doc_id=meta['doc_id'], source_sha256=meta['sha256'],
                      metadata_sha256=sha(json.dumps(meta, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')))
        try:
            raw = bind_raw(root, meta['raw_path'], meta['sha256'], expected_bytes=declared_bytes)
        except (OSError, ValueError) as exc:
            if declared_bytes is not None:
                raise _ScopeMismatch(str(exc)) from exc
            raise
        import pymupdf
        result['renderer_version'] = str(pymupdf.VersionBind)
        result['visual_concordance'] = 'NOT_INDEPENDENTLY_VALIDATED'
        if decide_fn is None:
            decide_fn = relevance_states.decide
        if quality_fn is None:
            quality_fn = text_quality.page_verdict
        with pymupdf.open(stream=raw, filetype='pdf') as pdf:
            if pdf.needs_pass or not pdf.is_pdf:
                raise ValueError('unsupported PDF')
            page_count = pdf.page_count
            count_ok = type(meta.get('page_count')) is int and meta['page_count'] == page_count
            if declared_bytes is not None and not count_ok:
                raise _ScopeMismatch('declared page count mismatch')
            if not 0 < page_count <= MAX_PAGES:
                raise ValueError('unsupported PDF')
            result['physical_page_count'] = page_count
            truncated = not raw.rstrip().endswith(b'%%EOF') or bool(pdf.is_repaired)
            result['source_integrity'] = 'INCOMPLETE_OR_REPAIRED' if truncated else 'HASH_MATCH_PDF_OPENED'
            texts = []
            for i, page in enumerate(pdf, 1):
                txt = page.get_text('text')
                texts.append(txt)
                q = quality_fn(txt)
                flags = list(q.get('flags', []))
                letters = [c for c in txt if c.isalpha()]
                if not letters or sum(c.isascii() for c in letters) / len(letters) < 0.95:
                    flags.append('language_or_script_not_validated')
                # Conservative candidate checks: drawings can carry unextracted text;
                # invisible or transparent text can pass lexical checks while not rendering.
                if page.get_drawings():
                    flags.append('vector_content_not_validated')
                for span in page.get_texttrace():
                    if span.get('type') == 3 or span.get('opacity', 1) < 1:
                        flags.append('hidden_or_transparent_text')
                if page.get_image_info():
                    flags.append('image_content_not_validated')
                if not txt.strip():
                    flags.append('blank_or_unreadable_not_validated')
                usable = q.get('usable') is True and not flags
                result['pages'].append({'physical_page': i, 'text_sha256': sha(txt.encode('utf-8')),
                                        'native_heuristics_pass': usable, 'usable_for_negative_evidence': False,
                                        'flags': sorted(set(flags))})
            full = '\n'.join(f'[[page {i}]]\n{t}\n' for i, t in enumerate(texts, 1))
            result['text_sha256'] = sha(full.encode('utf-8'))
            bad = [p['physical_page'] for p in result['pages'] if not p['native_heuristics_pass']]
            complete = not truncated and count_ok and not bad
            quality = {'verdict': 'TEXT_OK' if complete else 'OCR_REQUIRED', 'unusable_pages': bad,
                       'usable_share': (len(texts) - len(bad)) / len(texts)}
            # Count mismatch is independent of classifier evidence and blocks negative conclusions.
            classifier_text = '\n'.join(texts)
            result['classifier_text_sha256'] = sha(classifier_text.encode('utf-8'))
            decision = decide_fn(text=classifier_text, quality=quality, truncated=truncated, ocr_done=False,
                                 ocr_quality_ok=complete, title=meta.get('title'))
            state = decision['state']
            # No native-text heuristic proves visual concordance. Until a separate
            # source-bound visual adjudication exists, never issue a negative finding.
            if state == 'IRRELEVANT':
                state = 'INSUFFICIENT_TEXT' if not complete else 'MANUAL_REVIEW_REQUIRED'
            result['classifier_candidate_state'] = decision['state']
            result.update(relevance=state, native_heuristics_complete=complete,
                          complete_native_evidence=False,
                          metadata_page_count_matches=count_ok,
                          reasons=list(decision.get('reasons', [])),
                          eligible_for_documentary_review=False)
            result['reasons'].append('visual concordance not independently validated; no negative or documentary eligibility')
            if not count_ok:
                result['reasons'].append('metadata page count missing or mismatched')
            if truncated:
                result['reasons'].append('raw EOF or repair check failed')
    except _ScopeMismatch:
        raise
    except Exception as exc:
        result.update(relevance='EXTRACTION_FAILED', source_integrity='REVIEW_REQUIRED',
                      complete_native_evidence=False, native_heuristics_complete=False, eligible_for_documentary_review=False,
                      reasons=[type(exc).__name__])
    result['assessment_id'] = sha(json.dumps(result, sort_keys=True, ensure_ascii=False).encode('utf-8'))
    return result
