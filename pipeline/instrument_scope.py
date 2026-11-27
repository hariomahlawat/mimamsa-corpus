"""CA-05 candidate instrument-region validation. No PDF mutation or release."""
from __future__ import annotations
import hashlib
import json
import math
import re


def _validate_scope(source_sha256, page_sizes, regions, frame):
    """Validate physical-page coordinates in PDF points, top-left origin.

    A region may cover an entire page or a contiguous rectangular portion.
    Uncovered portions remain unassigned, never silently inherited. All output
    stays a candidate until independently reviewed against the source image.
    """
    if not re.fullmatch(r'[0-9a-f]{64}', source_sha256):
        raise ValueError('source SHA-256 required')
    if not page_sizes or not isinstance(regions, (list, tuple)) or not regions:
        raise ValueError('page dimensions and explicit regions required')
    if len(page_sizes) != len(frame):
        raise ValueError('incomplete geometry')
    for size in page_sizes:
        if len(size) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in size):
            raise ValueError('invalid page dimensions')
    by_page = {}
    canonical = []
    for region in regions:
        if not isinstance(region, dict):
            raise ValueError('invalid region')
        page = region.get('physical_page')
        box = region.get('bbox')
        instrument = region.get('instrument_id')
        if type(page) is not int or not 1 <= page <= len(page_sizes) or not isinstance(instrument, str) or not instrument.strip():
            raise ValueError('invalid instrument or physical page')
        if (not isinstance(box, (list, tuple)) or len(box) != 4
                or any(type(v) not in (int, float) for v in box)):
            raise ValueError('invalid coordinates')
        label = region.get('printed_page')
        if label is not None and (not isinstance(label, str) or not label.strip()):
            raise ValueError('printed page must be an immutable nonempty string or null')
        w, h = page_sizes[page - 1]
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise ValueError('region outside physical page')
        box = [float(v) if v != 0 else 0.0 for v in box]
        for old in by_page.get(page, []):
            a, b, c, d = old
            if max(a, x0) < min(c, x1) and max(b, y0) < min(d, y1):
                raise ValueError('overlapping instrument regions')
        by_page.setdefault(page, []).append(box)
        canonical.append({'physical_page': page, 'instrument_id': instrument, 'bbox': list(box),
                          'printed_page': label, 'eligible_for_exact_anchor': False})
    canonical.sort(key=lambda r: (r['physical_page'], r['bbox'], r['instrument_id']))
    result = {'source_sha256': source_sha256, 'physical_page_count': len(page_sizes),
              'scope_version': 'c14-frame-v2', 'coordinate_system': 'ROTATED_DISPLAY_POINTS_TOP_LEFT',
              'page_frames': frame, 'regions': canonical,
              'unassigned_full_pages': [i for i in range(1, len(page_sizes) + 1) if i not in by_page],
              'unassigned_partial_regions_policy': 'DO_NOT_INDEX', 'status': 'CANDIDATE_NOT_REVIEWED',
              'research_eligible': False}
    result['scope_id'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode('utf-8')).hexdigest()
    return result


def validate_scope(source_sha256, raw, regions):
    """Accept only actual PDF bytes; derive all geometry from the same hashed input.

    Coordinates refer to the rotated page.rect viewport (not a raw PDF box).
    Mapping to pixels and exact-anchor approval remain separate review gates.
    """
    import pymupdf
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 50_000_000:
        raise ValueError('bounded immutable PDF bytes required')
    if hashlib.sha256(raw).hexdigest() != source_sha256:
        raise ValueError('source bytes do not match SHA-256')
    if not raw.rstrip().endswith(b'%%EOF'):
        raise ValueError('PDF EOF not established')
    sizes, frames = [], []
    def nums(seq):
        values = [float(v) if v != 0 else 0.0 for v in seq]
        if not all(math.isfinite(v) for v in values):
            raise ValueError('nonfinite page frame')
        return values
    with pymupdf.open(stream=raw, filetype='pdf') as pdf:
        if pdf.needs_pass or pdf.is_repaired or not pdf.is_pdf or not 0 < pdf.page_count <= 500:
            raise ValueError('unsupported PDF')
        for p in pdf:
            sizes.append([float(p.rect.width), float(p.rect.height)])
            frames.append({'viewport': nums(p.rect), 'cropbox': nums(p.cropbox),
                           'mediabox': nums(p.mediabox), 'rotation': p.rotation,
                           'rotation_matrix': nums(p.rotation_matrix),
                           'derotation_matrix': nums(p.derotation_matrix),
                           'transformation_matrix': nums(p.transformation_matrix),
                           'renderer_version': str(pymupdf.VersionBind)})
    return _validate_scope(source_sha256, sizes, regions, frames)
