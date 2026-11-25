"""C13-A0 statistics module: known values and determinism (fast, standard library only)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "legal_knowledge/audit_work/C13-A0-EVAL/tools"))
import c13_stats as S  # noqa: E402


class Stats(unittest.TestCase):
    def test_wilson_known_value(self):
        p, lo, hi = S.wilson(81, 263)        # Wilson (1927) style check against published 0.2553-0.3662
        self.assertAlmostEqual(lo, 0.2553, places=3)
        self.assertAlmostEqual(hi, 0.3662, places=3)
        self.assertEqual(S.wilson(0, 0), (None, None, None))

    def test_cohen_kappa_known_value(self):
        # 2x2 example: 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no -> kappa 0.4
        pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15
        self.assertAlmostEqual(S.cohen_kappa(pairs), 0.4, places=6)

    def test_krippendorff_alpha_known_value(self):
        # Krippendorff (2011) nominal example, 4 coders x 12 units, published alpha = 0.743
        data = [[1, 1, None, 1], [2, 2, 3, 2], [3, 3, 3, 3], [3, 3, 3, 3], [2, 2, 2, 2], [1, 2, 3, 4],
                [4, 4, 4, 4], [1, 1, 2, 1], [2, 2, 2, 2], [None, 5, 5, 5], [None, None, 1, 1], [None, None, 3, None]]
        self.assertAlmostEqual(S.krippendorff_alpha_nominal(data), 0.743, places=3)

    def test_alpha_equals_kappa_like_for_perfect(self):
        self.assertEqual(S.krippendorff_alpha_nominal([["a", "a"], ["b", "b"]]), 1.0)

    def test_ht_ratio_and_kish(self):
        units = [("j1", "A", 1.0, 1, 1), ("j2", "A", 1.0, 0, 1), ("j3", "B", 4.0, 2, 2)]
        self.assertAlmostEqual(S.ht_ratio(units), (1 + 8) / (1 + 1 + 8))
        self.assertAlmostEqual(S.kish_deff([1, 1, 1, 1]), 1.0)
        self.assertGreater(S.kish_deff([1, 1, 10]), 1.0)

    def test_bootstrap_deterministic_and_brackets(self):
        units = [(f"j{i}", "A" if i % 2 else "B", 1.0 + (i % 3), int(i % 5 != 0), 1) for i in range(60)]
        a = S.stratified_cluster_bootstrap(units, 500, "seed")
        b = S.stratified_cluster_bootstrap(units, 500, "seed")
        self.assertEqual(a, b)
        p = S.ht_ratio(units)
        self.assertLessEqual(a[0], p)
        self.assertGreaterEqual(a[1], p)

    def test_sample_size_helpers(self):
        n = S.n_for_halfwidth(0.6, 0.07)
        self.assertLessEqual(S.wilson_halfwidth(0.6, n), 0.07)
        self.assertGreater(S.wilson_halfwidth(0.6, n - 1), 0.07)
        self.assertEqual(S.n_one_sided_power(0.95, 0.98), 253)
        self.assertAlmostEqual(S._zinv(0.975), 1.959964, places=5)

    def test_icc(self):
        self.assertAlmostEqual(S.icc_anova([[1, 1], [0, 0], [1, 1], [0, 0]]), 1.0)
        self.assertEqual(S.icc_anova([[1, 0], [1, 0], [0, 1]]), 0.0)


if __name__ == "__main__":
    unittest.main()
