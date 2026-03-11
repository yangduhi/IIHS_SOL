from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from scripts.tools.slide_away.review_domain_score_sensitivity import build_component_series, build_domain_scenarios, build_lower_ext_variants


def make_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "leg_foot_index_left": [0.4, 0.5, 0.7],
            "leg_foot_index_right": [0.6, 0.3, 0.8],
            "foot_resultant_accel_left_g": [80.0, 100.0, 120.0],
            "foot_resultant_accel_right_g": [90.0, 70.0, 110.0],
            "thigh_hip_risk_proxy": [0.2, 0.5, 0.9],
            "intrusion_max_resultant_cm": [5.0, 7.0, 9.0],
            "intrusion_footrest_resultant_cm": [3.0, 4.0, 6.0],
            "intrusion_left_toepan_resultant_cm": [2.0, 4.0, 5.0],
            "intrusion_brake_pedal_resultant_cm": [1.0, 3.0, 4.0],
            "dummy_clearance_min_mm": [120.0, 100.0, 80.0],
            "pretensioner_time_ms": [12.0, 13.0, 14.0],
            "airbag_first_contact_time_ms": [28.0, 30.0, 32.0],
            "airbag_full_inflation_time_ms": [42.0, 44.0, 46.0],
            "head_hic15": [100.0, 150.0, 220.0],
            "neck_tension_extension_nij": [0.5, 0.7, 0.9],
            "chest_rib_compression_mm": [18.0, 22.0, 28.0],
            "chest_viscous_criteria_ms": [0.5, 0.7, 0.8],
            "structure_intrusion_score": [0.1, 0.2, 0.3],
            "lower_extremity_score": [0.2, 0.4, 0.6],
            "restraint_kinematics_score": [0.1, 0.3, 0.2],
            "head_neck_chest_score": [0.2, 0.1, 0.4],
        }
    )


class DomainScoreSensitivityTests(unittest.TestCase):
    def test_build_component_series_exposes_expected_keys(self) -> None:
        components = build_component_series(make_frame())
        self.assertIn("leg_index_max_z", components)
        self.assertIn("foot_accel_max_z", components)
        self.assertIn("dummy_clearance_inverse_z", components)
        self.assertEqual(len(components["foot_accel_max_z"]), 3)

    def test_build_domain_scenarios_contains_expected_scenarios(self) -> None:
        scenarios = build_domain_scenarios(make_frame())
        self.assertIn("baseline", scenarios)
        self.assertIn("lower_foot_only", scenarios)
        self.assertIn("head_neck_core", scenarios)
        self.assertTrue(np.isfinite(scenarios["lower_foot_only"]["lower_extremity_score"]).any())

    def test_build_lower_ext_variants_contains_component_slices(self) -> None:
        variants = build_lower_ext_variants(make_frame())
        self.assertEqual(set(variants.keys()), {"current", "leg_foot_only", "leg_thigh_only", "foot_thigh_only", "leg_only", "foot_only", "thigh_only"})
        self.assertTrue(np.isfinite(variants["foot_only"]).any())


if __name__ == "__main__":
    unittest.main()
