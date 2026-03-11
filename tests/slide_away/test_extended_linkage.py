from __future__ import annotations

import unittest

import pandas as pd

from scripts.tools.slide_away.review_extended_linkage import fit_linear_summary, robust_zscore


class ExtendedLinkageTests(unittest.TestCase):
    def test_robust_zscore_centers_on_median(self) -> None:
        series = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0])
        result = robust_zscore(series)
        self.assertAlmostEqual(float(result.iloc[2]), 0.0, places=6)

    def test_fit_linear_summary_returns_high_r2_for_linear_signal(self) -> None:
        ri_values = list(range(12))
        dataframe = pd.DataFrame(
            {
                "ri_100_z": ri_values,
                "safety_severity_score": [1.0 + (2.0 * value) for value in ri_values],
            }
        )
        summary = fit_linear_summary(dataframe, ["ri_100_z"], "safety_severity_score")
        self.assertGreater(float(summary["r2"]), 0.99)
        self.assertGreater(float(summary["adj_r2"]), 0.99)


if __name__ == "__main__":
    unittest.main()
