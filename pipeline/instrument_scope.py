"""CA-05 candidate instrument-region validation. No PDF mutation or release."""
from __future__ import annotations
import hashlib
import json
import math
import re


def validate_scope(source_sha256, page_sizes, regions):
    """Validate physical-page coordinates in PDF points, top-left origin.

    A region may cover an entire page or a contiguous rectangular portion.
    Uncovered portions remain unassigned, never silently inherited. All output
    stays a candidate until independently reviewed against the source image.
    """
    if not re.fullmatch(r'[0-9a-f]{64}', source_sha256):
        raise ValueError('source SHA-256 required')
    if not page_sizes or not regions:
        raise ValueError('page dimensions and explicit regions required')
    by_page = {}
    canonical = []
    for region in regions:
        page = region['physical_page']; box = region['bbox']; instrument = region['instrument_id']
        if type(page) is not int or not 1 <= page <= len(page_sizes) or not isinstance(instrument, str) or not instrument.strip():
            raise ValueError('invalid instrument or physical page')
        if len(box) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in box):
            raise ValueError('invalid coordinates')
        w, h = page_sizes[page - 1]
        x0, y0, x1, y1 = box
        if not (math.isfinite(w) and math.isfinite(h) and 0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise ValueError('region outside physical page')
        for old in by_page.get(page, []):
            a, b, c, d = old
            if max(a, x0) < min(c, x1) and max(b, y0) < min(d, y1):
                raise ValueError('overlapping instrument regions')
        by_page.setdefault(page, []).append(box)
        canonical.append({'physical_page': page, 'instrument_id': instrument, 'bbox': list(box),
                          'printed_page': region.get('printed_page'), 'eligible_for_exact_anchor': False})
    canonical.sort(key=lambda r: (r['physical_page'], r['bbox'], r['instrument_id']))
    result = {'source_sha256': source_sha256, 'physical_page_count': len(page_sizes),
              'coordinate_system': 'PDF_POINTS_TOP_LEFT', 'regions': canonical,
              'unassigned_full_pages': [i for i in range(1, len(page_sizes) + 1) if i not in by_page],
              'unassigned_partial_regions_policy': 'DO_NOT_INDEX', 'status': 'CANDIDATE_NOT_REVIEWED',
              'research_eligible': False}
    result['scope_id'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode('utf-8')).hexdigest()
    return result
