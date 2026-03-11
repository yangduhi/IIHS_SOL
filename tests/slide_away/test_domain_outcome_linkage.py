from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from scripts.tools.slide_away.review_domain_outcome_linkage import rowwise_max, rowwise_mean


class DomainOutcomeLinkageTests(unittest.TestCase):
    def test_rowwise_mean_ignores_missing_values(self) -> None:
        result = rowwise_mean(
            [
                pd.Series([1.0, np.nan, 3.0]),
                pd.Series([3.0, 5.0, np.nan]),
            ]
        )
        self.assertAlmostEqual(float(result.iloc[0]), 2.0, places=6)
        self.assertAlmostEqual(float(result.iloc[1]), 5.0, places=6)
        self.assertAlmostEqual(float(result.iloc[2]), 3.0, places=6)

    def test_rowwise_max_takes_maximum_of_available_values(self) -> None:
        result = rowwise_max(
            [
                pd.Series([1.0, np.nan, 3.0]),
                pd.Series([3.0, 5.0, 2.0]),
            ]
        )
        self.assertAlmostEqual(float(result.iloc[0]), 3.0, places=6)
        self.assertAlmostEqual(float(result.iloc[1]), 5.0, places=6)
        self.assertAlmostEqual(float(result.iloc[2]), 3.0, places=6)


if __name__ == "__main__":
    unittest.main()
