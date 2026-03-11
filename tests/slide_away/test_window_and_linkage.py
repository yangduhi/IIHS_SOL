from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.tools.slide_away.common import WINDOW_GRID_MS
from scripts.tools.slide_away.modeling import window_feature_columns
from scripts.tools.slide_away.review_domain_outcome_linkage import build_linkage_frame
from scripts.tools.slide_away.run_window_sweep import build_window_sweep


def synthetic_outcomes(filegroup_ids: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "filegroup_id": filegroup_ids,
            "intrusion_max_resultant_cm": [10.0 + value for value in filegroup_ids],
            "leg_foot_index_left": [0.5 + (0.1 * value) for value in filegroup_ids],
            "leg_foot_index_right": [0.6 + (0.1 * value) for value in filegroup_ids],
            "foot_resultant_accel_left_g": [20.0 + value for value in filegroup_ids],
            "foot_resultant_accel_right_g": [21.0 + value for value in filegroup_ids],
            "head_hic15": [100.0 + (5.0 * value) for value in filegroup_ids],
            "chest_rib_compression_mm": [20.0 + value for value in filegroup_ids],
            "chest_viscous_criteria_ms": [0.2 + (0.01 * value) for value in filegroup_ids],
            "neck_tension_extension_nij": [0.3 + (0.01 * value) for value in filegroup_ids],
            "thigh_hip_risk_proxy": [2.0 + (0.2 * value) for value in filegroup_ids],
            "intrusion_footrest_resultant_cm": [8.0 + value for value in filegroup_ids],
            "intrusion_left_toepan_resultant_cm": [7.0 + value for value in filegroup_ids],
            "intrusion_brake_pedal_resultant_cm": [6.0 + value for value in filegroup_ids],
            "dummy_clearance_min_mm": [150.0 - value for value in filegroup_ids],
            "pretensioner_time_ms": [15.0 + value for value in filegroup_ids],
            "airbag_first_contact_time_ms": [20.0 + value for value in filegroup_ids],
            "airbag_full_inflation_time_ms": [30.0 + value for value in filegroup_ids],
        }
    )


class WindowAndLinkageTests(unittest.TestCase):
    def test_build_linkage_frame_uses_vertical_and_resultant_harshness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            features = pd.DataFrame(
                {
                    "filegroup_id": [1, 2],
                    "test_code": ["A", "B"],
                    "test_side": ["driver", "passenger"],
                    "era": ["2001-2014", "2015-2017"],
                    "window_100_ri": [0.5, 1.0],
                    "window_100_max_abs_az_g": [5.0, 15.0],
                    "window_100_max_abs_resultant_g": [10.0, 30.0],
                    "window_100_seat_twist_peak_mm": [2.0, 5.0],
                    "window_100_foot_resultant_asymmetry_g": [1.0, 4.0],
                }
            )
            outcomes = synthetic_outcomes([1, 2])
            assignments = pd.DataFrame({"filegroup_id": [1, 2], "working_mode_label": ["mode_0", "mode_1"]})
            features_path = root / "features.parquet"
            outcomes_path = root / "outcomes.parquet"
            assignments_path = root / "assignments.csv"
            features.to_parquet(features_path, index=False)
            outcomes.to_parquet(outcomes_path, index=False)
            assignments.to_csv(assignments_path, index=False)

            frame = build_linkage_frame(features_path, outcomes_path, assignments_path)

            harsh_case_a = float(frame.loc[frame["filegroup_id"].eq(1), "harshness_proxy_z"].iloc[0])
            harsh_case_b = float(frame.loc[frame["filegroup_id"].eq(2), "harshness_proxy_z"].iloc[0])
            self.assertLess(harsh_case_a, harsh_case_b)
            self.assertEqual(frame.loc[frame["filegroup_id"].eq(2), "working_mode_label"].iloc[0], "mode_1")

    def test_build_window_sweep_prefers_100ms_when_100ms_clusters_are_cleaner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = []
            filegroup_ids = list(range(1, 9))
            for filegroup_id in filegroup_ids:
                row = {"filegroup_id": filegroup_id, "cluster_input_flag": 1}
                high_group = filegroup_id > 4
                for window_ms in WINDOW_GRID_MS:
                    for column in window_feature_columns(window_ms):
                        row[column] = 0.0
                    if window_ms == 100:
                        row[f"window_{window_ms:03d}_delta_vx_mps"] = -20.0 if high_group else -5.0
                        row[f"window_{window_ms:03d}_delta_vy_away_mps"] = 15.0 if high_group else 1.0
                        row[f"window_{window_ms:03d}_ri"] = 2.0 if high_group else 0.2
                        row[f"window_{window_ms:03d}_max_abs_ax_g"] = 30.0 if high_group else 10.0
                        row[f"window_{window_ms:03d}_max_abs_ay_g"] = 18.0 if high_group else 4.0
                        row[f"window_{window_ms:03d}_max_abs_az_g"] = 22.0 if high_group else 3.0
                        row[f"window_{window_ms:03d}_max_abs_resultant_g"] = 40.0 if high_group else 12.0
                    elif window_ms == 150:
                        row[f"window_{window_ms:03d}_delta_vx_mps"] = -12.0 if high_group else -8.0
                        row[f"window_{window_ms:03d}_delta_vy_away_mps"] = 8.0 if high_group else 4.0
                        row[f"window_{window_ms:03d}_ri"] = 0.9 if high_group else 0.4
                        row[f"window_{window_ms:03d}_max_abs_ax_g"] = 20.0 if high_group else 14.0
                        row[f"window_{window_ms:03d}_max_abs_ay_g"] = 10.0 if high_group else 6.0
                        row[f"window_{window_ms:03d}_max_abs_az_g"] = 12.0 if high_group else 8.0
                        row[f"window_{window_ms:03d}_max_abs_resultant_g"] = 26.0 if high_group else 20.0
                    else:
                        row[f"window_{window_ms:03d}_delta_vx_mps"] = -10.0
                        row[f"window_{window_ms:03d}_delta_vy_away_mps"] = 5.0
                        row[f"window_{window_ms:03d}_ri"] = 0.5
                        row[f"window_{window_ms:03d}_max_abs_ax_g"] = 15.0
                        row[f"window_{window_ms:03d}_max_abs_ay_g"] = 6.0
                        row[f"window_{window_ms:03d}_max_abs_az_g"] = 7.0
                        row[f"window_{window_ms:03d}_max_abs_resultant_g"] = 18.0
                rows.append(row)
            features = pd.DataFrame(rows)
            outcomes = synthetic_outcomes(filegroup_ids)
            features_path = root / "features.parquet"
            outcomes_path = root / "outcomes.parquet"
            features.to_parquet(features_path, index=False)
            outcomes.to_parquet(outcomes_path, index=False)

            summary = build_window_sweep(features_path, outcomes_path)

            selected = int(summary.loc[summary["selected_operating_window"].eq(1), "window_ms"].iloc[0])
            self.assertEqual(selected, 100)


if __name__ == "__main__":
    unittest.main()
