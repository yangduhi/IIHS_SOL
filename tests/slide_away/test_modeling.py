from __future__ import annotations

import unittest

import pandas as pd

from scripts.tools.slide_away.modeling import prepare_window_frame, window_feature_columns


class ModelingTests(unittest.TestCase):
    def test_prepare_window_frame_filters_low_coverage_and_imputes(self) -> None:
        columns = window_feature_columns(100)
        rows = []
        for filegroup_id in (1, 2, 3):
            row = {"filegroup_id": filegroup_id, "cluster_input_flag": 1}
            for index, column in enumerate(columns):
                row[column] = float(index + filegroup_id)
            rows.append(row)
        rows[1][columns[0]] = None
        for column in columns[:8]:
            rows[2][column] = None
        features = pd.DataFrame(rows)

        prepared, returned_columns = prepare_window_frame(features, 100)

        self.assertEqual(returned_columns, columns)
        self.assertEqual(len(prepared), 2)
        self.assertTrue(prepared[columns].notna().all().all())
        imputed_value = float(prepared.loc[prepared["filegroup_id"].eq(2), columns[0]].iloc[0])
        self.assertAlmostEqual(imputed_value, float(prepared.loc[prepared["filegroup_id"].eq(1), columns[0]].iloc[0]), places=6)


if __name__ == "__main__":
    unittest.main()
