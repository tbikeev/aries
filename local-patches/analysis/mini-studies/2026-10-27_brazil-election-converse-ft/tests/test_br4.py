"""Smoke tests for BR-4 differential metrics."""

from __future__ import annotations

import unittest

import numpy as np

from br4_differences import _metrics, _pooled_stats


class TestBr4Metrics(unittest.TestCase):
    def test_metrics_nan_when_empty_tail(self):
        m = _metrics(0, 0, 0.0, 10, 2, 3.0)
        self.assertTrue(np.isnan(m["F_neg"]))
        self.assertTrue(np.isnan(m["delta_F"]))
        self.assertEqual(m["F_pos"], 0.2)

    def test_pooled_stats_respects_eligibility(self):
        active = np.zeros((2, 2), dtype=bool)
        power = np.ones((2, 2), dtype=float)
        eligible = np.array([[True, False], [True, True]])
        active[0, 0] = True
        N, n, s = _pooled_stats(active, power, eligible, np.array([0, 1]))
        self.assertEqual(N, 3)
        self.assertEqual(n, 1)
        self.assertEqual(s, 1.0)

    def test_delta_a_conditional(self):
        m = _metrics(10, 5, 25.0, 10, 5, 10.0)
        self.assertEqual(m["A_neg"], 5.0)
        self.assertEqual(m["A_pos"], 2.0)
        self.assertEqual(m["delta_A"], 3.0)


if __name__ == "__main__":
    unittest.main()
