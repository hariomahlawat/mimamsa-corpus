"""Candidate-only release denial tests; no application or site changes."""
import unittest
from pipeline.candidate_release_guard import preflight, KINDS


class CandidateReleaseTests(unittest.TestCase):
    def test_all_known_channels_denied(self):
        r=preflight([{'kind':k,'record':{'doc_id':'fixture'}} for k in sorted(KINDS)],
                    workstream='C14')
        self.assertFalse(r['release_allowed'])
        self.assertEqual(r['records_allowed'],0)
        self.assertEqual(len(r['denials']),len(KINDS))

    def test_nested_candidate_report(self):
        r=preflight([{'kind':'report','record':{'nested':[{'schema':'c14-ocr-evidence-v1'}]}}],
                    workstream='C14')
        self.assertEqual(r['denials'][0]['reason'],'C14_CANDIDATE_ARTIFACT')

    def test_claimed_approval_cannot_override(self):
        r=preflight([{'kind':'candidates_jsonl','record':{'research_eligible':True,'signed':True}}],
                    workstream='C14')
        self.assertFalse(r['release_allowed'])

    def test_stripped_markers_still_denied(self):
        r=preflight([{'kind':'report','record':{'title':'ordinary-looking record'}}],workstream='C14')
        self.assertEqual(r['denials'][0]['reason'],'C14_RELEASE_NOT_AUTHORIZED')

    def test_unknown_channel_and_malformed(self):
        r=preflight([{'kind':'unknown'},None],workstream='C14')
        self.assertEqual([d['reason'] for d in r['denials']],['UNKNOWN_RELEASE_KIND','INVALID_RECORD'])

    def test_other_workstreams_not_permitted_by_guard(self):
        with self.assertRaises(ValueError):preflight([],workstream='B1')

    def test_empty_input_not_permission(self):
        self.assertFalse(preflight([],workstream='C14')['release_allowed'])

if __name__=='__main__':unittest.main()
