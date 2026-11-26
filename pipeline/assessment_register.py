"""C14 candidate-only assessment journal.

A caller supplies an isolated SQLite connection. No corpus paths, source bytes,
network, or application database are opened here. This is an append-only
application contract, not an OS security boundary or a legal release ledger.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3

HEX = re.compile(r'[0-9a-f]{64}\Z')
SCHEMA = 'c14-assessment-journal-v1'
STATES = frozenset(('RELEVANT', 'INSUFFICIENT_TEXT', 'OCR_REQUIRED',
                    'EXTRACTION_FAILED', 'CLASSIFICATION_UNCERTAIN',
                    'SOURCE_INCOMPLETE', 'MANUAL_REVIEW_REQUIRED'))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def valid_hash(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def check_assessment(value):
    if not isinstance(value, dict):
        raise ValueError('assessment object required')
    a = json.loads(canonical(value))
    identity = a.pop('assessment_id', None)
    # Shadow v2 uses the default JSON separators for its existing identity.
    expected = hashlib.sha256(json.dumps(a, sort_keys=True, ensure_ascii=False,
                                        allow_nan=False).encode('utf-8')).hexdigest()
    if identity != expected:
        raise ValueError('assessment identity mismatch')
    if (a.get('version') != 'c14-shadow-v2'
            or not isinstance(a.get('doc_id'), str)
            or not a['doc_id'].strip() or len(a['doc_id']) > 120
            or not valid_hash(a.get('source_sha256'))
            or not valid_hash(a.get('metadata_sha256'))
            or a.get('relevance') not in STATES):
        raise ValueError('invalid or unbound assessment')
    for flag in ('research_eligible', 'eligible_for_documentary_review',
                 'complete_native_evidence'):
        if a.get(flag) is not False:
            raise ValueError('candidate cannot grant eligibility')
    if not isinstance(a.get('pages'), list) or len(a['pages']) > 500:
        raise ValueError('invalid pages')
    for i, page in enumerate(a['pages'], 1):
        if (not isinstance(page, dict) or page.get('physical_page') != i
                or not valid_hash(page.get('text_sha256'))
                or page.get('usable_for_negative_evidence') is not False):
            raise ValueError('invalid candidate page evidence')
    a['assessment_id'] = identity
    return a


class Journal:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        # Dedicated database only; do not create tables in a preexisting corpus DB.
        names = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        if names - {'candidate_events'}:
            raise ValueError('not a dedicated assessment journal')
        db.executescript("""
        CREATE TABLE IF NOT EXISTS candidate_events (
            event_id TEXT PRIMARY KEY,
            assessment_id TEXT NOT NULL UNIQUE,
            doc_id TEXT NOT NULL,
            previous_event_id TEXT REFERENCES candidate_events(event_id),
            payload BLOB NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS candidate_successor
            ON candidate_events(previous_event_id) WHERE previous_event_id IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS candidate_root
            ON candidate_events(doc_id) WHERE previous_event_id IS NULL;
        CREATE TRIGGER IF NOT EXISTS candidate_no_update BEFORE UPDATE ON candidate_events
            BEGIN SELECT RAISE(ABORT, 'append only'); END;
        CREATE TRIGGER IF NOT EXISTS candidate_no_delete BEFORE DELETE ON candidate_events
            BEGIN SELECT RAISE(ABORT, 'append only'); END;
        """)
        db.execute('PRAGMA foreign_keys=ON')

    def append(self, assessment, *, previous_event_id=None):
        a = check_assessment(assessment)
        if previous_event_id is not None and not valid_hash(previous_event_id):
            raise ValueError('invalid predecessor')
        event = {'schema': SCHEMA, 'assessment': a,
                 'previous_event_id': previous_event_id,
                 'disposition': 'CANDIDATE_NOT_RELEASED', 'research_eligible': False}
        event_id = digest(event)
        body = canonical(event)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            # Exact reruns are idempotent; identical assessments with another
            # predecessor cannot silently create an alternative history.
            existing = self.db.execute(
                'SELECT event_id,payload FROM candidate_events WHERE assessment_id=?',
                (a['assessment_id'],)).fetchone()
            if existing is not None:
                if tuple(existing) != (event_id, body):
                    raise ValueError('assessment already bound to another history')
                self.db.commit()
                return event_id
            head = self.db.execute("""
                SELECT e.event_id FROM candidate_events e
                WHERE e.doc_id=? AND NOT EXISTS (
                    SELECT 1 FROM candidate_events n WHERE n.previous_event_id=e.event_id)
                """, (a['doc_id'],)).fetchall()
            if len(head) > 1 or (head[0][0] if head else None) != previous_event_id:
                raise ValueError('explicit current predecessor required')
            self.db.execute('INSERT INTO candidate_events VALUES (?,?,?,?,?)',
                            (event_id, a['assessment_id'], a['doc_id'], previous_event_id, body))
            self.db.commit()
            return event_id
        except BaseException:
            self.db.rollback()
            raise

    def audit(self):
        """Verify identities and chain membership; do not produce retrieval records."""
        events = {}
        children = {}
        roots = set()
        for eid, aid, doc, prev, body in self.db.execute(
                'SELECT event_id,assessment_id,doc_id,previous_event_id,payload FROM candidate_events'):
            event = json.loads(body)
            a = check_assessment(event['assessment'])
            if (canonical(event) != body or digest(event) != eid
                    or event.get('schema') != SCHEMA
                    or event.get('disposition') != 'CANDIDATE_NOT_RELEASED'
                    or event.get('research_eligible') is not False
                    or a['assessment_id'] != aid or a['doc_id'] != doc
                    or event['previous_event_id'] != prev):
                raise ValueError('journal identity mismatch')
            events[eid] = (doc, prev)
            if prev is None:
                if doc in roots:
                    raise ValueError('multiple document roots')
                roots.add(doc)
            else:
                if prev in children:
                    raise ValueError('forked history')
                children[prev] = eid
        for eid, (doc, prev) in events.items():
            visited = {eid}
            while prev is not None:
                if prev in visited or prev not in events or events[prev][0] != doc:
                    raise ValueError('invalid history chain')
                visited.add(prev)
                prev = events[prev][1]
        return {'events': len(events), 'documents': len(roots),
                'research_eligible': False, 'status': 'CANDIDATE_JOURNAL_AUDITED'}
