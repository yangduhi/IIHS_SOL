from __future__ import annotations

import math
import unittest

import pandas as pd

from scripts.tools.slide_away.common import compute_slide_away_metrics, normalize_make_model_family


def synthetic_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time_s": [0.0, 0.02, 0.04, 0.06, 0.08, 0.10],
            "vehicle_longitudinal_accel_g": [-5.0, -5.0, -5.0, -5.0, 0.0, 0.0],
            "vehicle_lateral_accel_g": [2.0, 2.0, 2.0, 2.0, 0.0, 0.0],
            "vehicle_vertical_accel_g": [1.0, 1.5, 2.0, 2.5, 0.5, 0.0],
            "vehicle_resultant_accel_g": [5.5, 5.6, 5.9, 6.3, 0.5, 0.0],
            "seat_mid_deflection_mm": [0.0, 1.0, 2.0, 3.0, 3.5, 3.5],
            "seat_inner_deflection_mm": [0.0, 2.0, 4.0, 6.0, 6.5, 6.5],
            "foot_left_x_accel_g": [0.0, 5.0, 10.0, 15.0, 5.0, 0.0],
            "foot_left_z_accel_g": [0.0, 2.0, 4.0, 6.0, 2.0, 0.0],
            "foot_right_x_accel_g": [0.0, 3.0, 6.0, 9.0, 3.0, 0.0],
            "foot_right_z_accel_g": [0.0, 1.0, 2.0, 3.0, 1.0, 0.0],
        }
    )


class SlideAwayCommonTests(unittest.TestCase):
    def test_normalize_make_model_family(self) -> None:
        self.assertEqual(
            normalize_make_model_family("2013 Honda Accord 4-door (R&D) - Small Overlap"),
            "Honda Accord 4 door",
        )

    def test_passenger_side_flips_delta_vy_away_sign(self) -> None:
        frame = synthetic_frame()
        driver_metrics = compute_slide_away_metrics(frame, "driver", 17.0)
        passenger_metrics = compute_slide_away_metrics(frame, "passenger", 17.0)
        self.assertGreater(driver_metrics.default_metrics["delta_vy_away_mps"], 0.0)
        self.assertLess(passenger_metrics.default_metrics["delta_vy_away_mps"], 0.0)
        self.assertAlmostEqual(
            abs(driver_metrics.default_metrics["delta_vy_away_mps"]),
            abs(passenger_metrics.default_metrics["delta_vy_away_mps"]),
            places=6,
        )

    def test_ri_is_nan_when_delta_vx_is_too_small(self) -> None:
        frame = synthetic_frame().copy()
        frame["vehicle_longitudinal_accel_g"] = 0.0
        metrics = compute_slide_away_metrics(frame, "driver", 17.0)
        self.assertTrue(math.isnan(metrics.default_metrics["ri"]))

    def test_vertical_and_resultant_metrics_are_exposed(self) -> None:
        metrics = compute_slide_away_metrics(synthetic_frame(), "driver", 17.0)
        self.assertGreater(metrics.default_metrics["max_abs_az_g"], 0.0)
        self.assertGreater(metrics.default_metrics["max_abs_resultant_g"], 0.0)
        self.assertIn("max_abs_az_g", metrics.window_metrics[100])
        self.assertIn("max_abs_resultant_g", metrics.window_metrics[100])
        self.assertIn("pulse_duration_z_ms", metrics.window_metrics[100])


if __name__ == "__main__":
    unittest.main()
