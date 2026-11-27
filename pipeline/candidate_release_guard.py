"""C14 candidate quarantine: a negative-only release preflight.

This is a build-side guard for the C14 workstream, not an alternative importer,
release signer, exclusion register, or authority ledger. No C14 candidate
assessment or OCR artifact is eligible for export in this version.
"""
from __future__ import annotations
import re
from collections.abc import Mapping

HEX = re.compile(r'[0-9a-f]{64}\Z')
KINDS = frozenset(('documents_jsonl', 'derived_text_jsonl', 'candidates_jsonl', 'report',
                   'source_copy', 'derived_text', 'research_file'))
C14_MARKERS = frozenset(('assessment_id', 'previous_event_id', 'scope_id',
                         'classifier_candidate_state', 'visual_concordance',
                         'native_heuristics_complete', 'source_integrity_holds',
                         'recovered_path_candidates', 'ocr_evidence_id'))
QUARANTINE_FLAGS = frozenset(('research_eligible', 'eligible_for_documentary_review',
                              'eligible_for_exact_anchor', 'usable_for_negative_evidence'))


def _candidate_shape(value):
    if isinstance(value, Mapping):
        if set(value) & C14_MARKERS:
            return True
        if any(value.get(k) is False for k in QUARANTINE_FLAGS):
            return True
        if any(isinstance(value.get(k), str) and value[k].lower().startswith('c14-')
               for k in ('schema', 'version', 'scope_version')):
            return True
        return any(_candidate_shape(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_candidate_shape(v) for v in value)
    return False


def preflight(records, *, workstream):
    """Deny C14 publication regardless of metadata flags or claimed signature.

    The caller must establish provenance; passing a different workstream is
    not an authorization mechanism. Other release workstreams are deliberately
    outside this API. Return a denial, never a list of permitted records.
    """
    if workstream != 'C14':
        raise ValueError('only C14 quarantine preflight is supported')
    reasons = []
    for n, item in enumerate(records, 1):
        if not isinstance(item, Mapping):
            reasons.append({'ordinal': n, 'reason': 'INVALID_RECORD'})
            continue
        kind = item.get('kind')
        if not isinstance(kind, str) or kind not in KINDS:
            why = 'UNKNOWN_RELEASE_KIND'
        elif _candidate_shape(item):
            why = 'C14_CANDIDATE_ARTIFACT'
        else:
            why = 'C14_RELEASE_NOT_AUTHORIZED'
        reasons.append({'ordinal': n, 'reason': why})
    return {'status': 'DENIED', 'workstream': 'C14',
            'release_allowed': False, 'records_allowed': 0,
            'denials': reasons}
