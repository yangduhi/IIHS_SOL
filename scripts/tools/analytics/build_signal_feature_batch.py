from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.core.signals.preprocess_known_signal_families import ensure_preprocessing_schema, resolve_repo_path, utc_now_iso


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = REPO_ROOT / "output" / "small_overlap" / "tables"
PARSER_VERSION = "signal-feature-batch:v3-window015"
DEFAULT_SOURCE_MODE = "standard_baseline"
DEFAULT_FEATURE_SPACE = "official_known_harmonized_v3_window015"
NEIGHBOR_ALGORITHM = "hybrid_similarity_v3_window015"
CLUSTER_ALGORITHM = "kmedoids_multiview_v3_window015"
REPRESENTATIVE_ALGORITHM = CLUSTER_ALGORITHM
ANALYSIS_WINDOW_START_S = 0.0
ANALYSIS_WINDOW_END_S = 0.15
DTW_PRIORITY_CHANNELS = (
    "vehicle_longitudinal_accel_g",
    "vehicle_resultant_accel_g",
    "vehicle_lateral_accel_g",
    "seat_mid_deflection_mm",
    "foot_left_x_accel_g",
    "foot_right_x_accel_g",
)
VIEW_CHANNELS = {
    "pulse": (
        "vehicle_longitudinal_accel_g",
        "vehicle_lateral_accel_g",
        "vehicle_vertical_accel_g",
        "vehicle_resultant_accel_g",
        "vehicle_longitudinal_accel_g__jerk",
        "vehicle_resultant_accel_g__jerk",
        "vehicle_longitudinal_accel_g__delta_v",
        "vehicle_resultant_accel_g__delta_v",
    ),
    "occupant": (
        "seat_mid_deflection_mm",
        "seat_inner_deflection_mm",
        "seat_mid_deflection_mm__rate",
        "seat_inner_deflection_mm__rate",
    ),
    "lower_extremity": (
        "foot_left_x_accel_g",
        "foot_left_z_accel_g",
        "foot_right_x_accel_g",
        "foot_right_z_accel_g",
        "foot_left_x_accel_g__jerk",
        "foot_right_x_accel_g__jerk",
    ),
}
VIEW_WEIGHTS = {
    "pulse": 0.46,
    "occupant": 0.30,
    "lower_extremity": 0.24,
}
PHASE_NAMES = ("build", "rebound", "settle")
PHASE_WEIGHTS = {
    "build": 0.46,
    "rebound": 0.34,
    "settle": 0.20,
}
PHASE_RESAMPLE_POINTS = 32
DERIVED_SIGNAL_SPECS = {
    "vehicle_longitudinal_accel_g__jerk": ("vehicle_longitudinal_accel_g", "jerk"),
    "vehicle_resultant_accel_g__jerk": ("vehicle_resultant_accel_g", "jerk"),
    "foot_left_x_accel_g__jerk": ("foot_left_x_accel_g", "jerk"),
    "foot_right_x_accel_g__jerk": ("foot_right_x_accel_g", "jerk"),
    "seat_mid_deflection_mm__rate": ("seat_mid_deflection_mm", "rate"),
    "seat_inner_deflection_mm__rate": ("seat_inner_deflection_mm", "rate"),
    "vehicle_longitudinal_accel_g__delta_v": ("vehicle_longitudinal_accel_g", "delta_v"),
    "vehicle_resultant_accel_g__delta_v": ("vehicle_resultant_accel_g", "delta_v"),
}
DERIVED_VECTOR_FEATURES = (
    "peak_abs",
    "peak_abs_time_s",
    "area_abs",
    "energy_proxy",
    "centroid_time_abs",
    "max_abs_slope",
    "end_value",
)
CHANNEL_ORDER = (
    "vehicle_longitudinal_accel_g",
    "vehicle_lateral_accel_g",
    "vehicle_vertical_accel_g",
    "vehicle_resultant_accel_g",
    "seat_mid_deflection_mm",
    "seat_inner_deflection_mm",
    "foot_left_x_accel_g",
    "foot_left_z_accel_g",
    "foot_right_x_accel_g",
    "foot_right_z_accel_g",
)
CHANNEL_WEIGHTS = {
    "vehicle_longitudinal_accel_g": 1.30,
    "vehicle_lateral_accel_g": 0.85,
    "vehicle_vertical_accel_g": 0.85,
    "vehicle_resultant_accel_g": 1.10,
    "seat_mid_deflection_mm": 1.20,
    "seat_inner_deflection_mm": 1.10,
    "foot_left_x_accel_g": 0.70,
    "foot_left_z_accel_g": 0.55,
    "foot_right_x_accel_g": 0.70,
    "foot_right_z_accel_g": 0.55,
}
ALL_FEATURES = (
    "coverage_ratio",
    "peak_abs",
    "peak_abs_time_s",
    "peak_positive",
    "peak_positive_time_s",
    "peak_negative",
    "peak_negative_time_s",
    "mean",
    "std",
    "area",
    "area_abs",
    "energy_proxy",
    "zero_crossing_count",
    "onset_time_abs",
    "rise_time_abs_10_90",
    "peak_to_peak",
    "centroid_time_abs",
    "impulse_width_10_abs",
    "duration_above_50pct_abs",
    "late_energy_ratio",
    "rebound_abs",
    "rebound_time_s",
    "max_abs_slope",
    "major_extrema_count",
    "settle_time_abs",
    "onset_to_peak_s",
    "peak_to_rebound_s",
    "peak_to_settle_s",
    "end_value",
)
VECTOR_FEATURES = (
    "coverage_ratio",
    "peak_abs",
    "peak_abs_time_s",
    "peak_positive",
    "peak_negative",
    "mean",
    "std",
    "area_abs",
    "energy_proxy",
    "zero_crossing_count",
    "onset_time_abs",
    "rise_time_abs_10_90",
    "peak_to_peak",
    "centroid_time_abs",
    "impulse_width_10_abs",
    "duration_above_50pct_abs",
    "late_energy_ratio",
    "rebound_abs",
    "rebound_time_s",
    "max_abs_slope",
    "major_extrema_count",
    "settle_time_abs",
    "onset_to_peak_s",
    "peak_to_rebound_s",
    "peak_to_settle_s",
    "end_value",
)
FEATURE_WEIGHTS = {
    "coverage_ratio": 0.45,
    "peak_abs": 1.25,
    "peak_abs_time_s": 1.00,
    "peak_positive": 0.95,
    "peak_negative": 0.95,
    "mean": 0.55,
    "std": 0.85,
    "area_abs": 0.95,
    "energy_proxy": 1.10,
    "zero_crossing_count": 0.40,
    "onset_time_abs": 1.05,
    "rise_time_abs_10_90": 0.95,
    "peak_to_peak": 1.05,
    "centroid_time_abs": 0.90,
    "impulse_width_10_abs": 0.85,
    "duration_above_50pct_abs": 0.80,
    "late_energy_ratio": 0.80,
    "rebound_abs": 0.90,
    "rebound_time_s": 0.75,
    "max_abs_slope": 0.85,
    "major_extrema_count": 0.40,
    "settle_time_abs": 0.70,
    "onset_to_peak_s": 0.90,
    "peak_to_rebound_s": 0.75,
    "peak_to_settle_s": 0.60,
    "end_value": 0.55,
}
CROSS_CHANNEL_FEATURE_WEIGHTS = {
    "seat_mid_onset_minus_vehicle_longitudinal_onset_s": 1.20,
    "seat_inner_onset_minus_vehicle_longitudinal_onset_s": 1.10,
    "seat_mid_peak_minus_vehicle_longitudinal_peak_s": 1.10,
    "seat_inner_peak_minus_vehicle_longitudinal_peak_s": 1.05,
    "foot_left_x_peak_minus_vehicle_longitudinal_peak_s": 1.00,
    "foot_right_x_peak_minus_vehicle_longitudinal_peak_s": 1.00,
    "foot_left_z_peak_minus_vehicle_longitudinal_peak_s": 0.90,
    "foot_right_z_peak_minus_vehicle_longitudinal_peak_s": 0.90,
    "vehicle_resultant_peak_minus_vehicle_longitudinal_peak_s": 0.85,
    "seat_mid_rebound_minus_vehicle_longitudinal_rebound_s": 0.80,
    "seat_inner_rebound_minus_vehicle_longitudinal_rebound_s": 0.75,
    "lower_extremity_peak_spread_s": 0.85,
}


@dataclass(frozen=True)
class CaseRow:
    preprocessing_case_id: int
    filegroup_id: int
    test_code: str | None
    vehicle_year: int | None
    vehicle_make_model: str
    source_mode: str
    harmonized_wide_path: Path


@dataclass
class CaseFeature:
    case: CaseRow
    time_s: np.ndarray
    channel_features: dict[str, dict[str, float]]
    signal_bank: dict[str, np.ndarray]
    derived_signal_bank: dict[str, np.ndarray]
    landmark_map: dict[str, dict[str, float]]
    phase_bank: dict[str, dict[str, np.ndarray]]
    feature_values: list[dict[str, Any]]
    vector_map: dict[str, float]
    coverage_map: dict[str, float]


def analysis_window_mask(time_s: np.ndarray) -> np.ndarray:
    finite = np.isfinite(time_s)
    return finite & (time_s >= (ANALYSIS_WINDOW_START_S - 1e-12)) & (time_s <= (ANALYSIS_WINDOW_END_S + 1e-12))


def crop_time_and_values_to_analysis_window(time_s: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = analysis_window_mask(time_s)
    if np.any(mask):
        return time_s[mask], values[mask]
    return time_s.copy(), values.copy()


def crop_frame_to_analysis_window(dataframe: pd.DataFrame) -> pd.DataFrame:
    if "time_s" not in dataframe.columns:
        return dataframe.copy()
    time_s = pd.to_numeric(dataframe["time_s"], errors="coerce").to_numpy(dtype=float)
    mask = analysis_window_mask(time_s)
    if not np.any(mask):
        return dataframe.copy()
    return dataframe.loc[mask].reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build explainable signal features, clustering, representatives, and neighbors from harmonized preprocessing outputs."
    )
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE)
    parser.add_argument("--feature-space", default=DEFAULT_FEATURE_SPACE)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--candidate-k", type=int, default=24)
    parser.add_argument("--dtw-step", type=int, default=10)
    parser.add_argument("--dtw-window", type=int, default=16)
    parser.add_argument("--min-clusters", type=int, default=2)
    parser.add_argument("--max-clusters", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def sanitize_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()


def json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_clean(item) for item in value]
    if isinstance(value, tuple):
        return [json_clean(item) for item in value]
    if isinstance(value, np.ndarray):
        return [json_clean(item) for item in value.tolist()]
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.integer, int)):
        return int(value)
    return value


def standard_base_name(standard_name: str) -> str:
    for suffix in ("__jerk", "__rate", "__delta_v"):
        if standard_name.endswith(suffix):
            return standard_name[: -len(suffix)]
    return standard_name


def standard_transform_name(standard_name: str) -> str:
    if standard_name.endswith("__jerk"):
        return "jerk"
    if standard_name.endswith("__rate"):
        return "rate"
    if standard_name.endswith("__delta_v"):
        return "delta_v"
    return "raw"


def unit_for_channel(channel_name: str) -> str:
    base_name = standard_base_name(channel_name)
    transform = standard_transform_name(channel_name)
    if base_name.endswith("_mm"):
        base_unit = "mm"
    elif base_name.endswith("_g"):
        base_unit = "g"
    else:
        base_unit = ""
    if transform == "jerk" and base_unit:
        return f"{base_unit}/s"
    if transform == "rate" and base_unit:
        return f"{base_unit}/s"
    if transform == "delta_v" and base_unit:
        return f"{base_unit}*s"
    if base_unit:
        return base_unit
    return ""


def unit_for_feature(channel_name: str, feature_name: str) -> str:
    base_unit = unit_for_channel(channel_name)
    if feature_name.endswith("_time_s") or feature_name in {
        "onset_time_abs",
        "rise_time_abs_10_90",
        "centroid_time_abs",
        "impulse_width_10_abs",
        "duration_above_50pct_abs",
        "settle_time_abs",
        "onset_to_peak_s",
        "peak_to_rebound_s",
        "peak_to_settle_s",
    }:
        return "s"
    if feature_name in {"coverage_ratio", "late_energy_ratio"}:
        return "ratio"
    if feature_name in {"zero_crossing_count", "major_extrema_count"}:
        return "count"
    if feature_name in {"area", "area_abs"} and base_unit:
        return f"{base_unit}*s"
    if feature_name == "energy_proxy" and base_unit:
        return f"{base_unit}^2*s"
    if feature_name == "max_abs_slope" and base_unit:
        return f"{base_unit}/s"
    return base_unit


def load_cases(
    connection: sqlite3.Connection,
    source_mode: str,
    limit: int | None,
) -> list[CaseRow]:
    rows = connection.execute(
        """
        SELECT pc.preprocessing_case_id,
               pc.filegroup_id,
               fg.test_code,
               v.vehicle_year,
               v.vehicle_make_model,
               pc.mode AS source_mode,
               pc.harmonized_wide_path
          FROM preprocessing_cases pc
          JOIN filegroups fg
            ON fg.filegroup_id = pc.filegroup_id
          JOIN vehicles v
            ON v.vehicle_id = fg.vehicle_id
         WHERE pc.mode = ?
           AND pc.status = 'done'
           AND pc.harmonized_wide_path IS NOT NULL
         ORDER BY pc.filegroup_id
        """,
        (source_mode,),
    ).fetchall()
    cases: list[CaseRow] = []
    for row in rows[:limit]:
        parquet_path = Path(row["harmonized_wide_path"])
        parquet_path = parquet_path if parquet_path.is_absolute() else REPO_ROOT / parquet_path
        cases.append(
            CaseRow(
                preprocessing_case_id=int(row["preprocessing_case_id"]),
                filegroup_id=int(row["filegroup_id"]),
                test_code=row["test_code"],
                vehicle_year=int(row["vehicle_year"]) if row["vehicle_year"] is not None else None,
                vehicle_make_model=row["vehicle_make_model"],
                source_mode=row["source_mode"],
                harmonized_wide_path=parquet_path,
            )
        )
    return cases


def finite_xy(time_s: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(time_s) & np.isfinite(values)
    return time_s[mask], values[mask]


def count_zero_crossings(values: np.ndarray) -> int:
    if values.size < 2:
        return 0
    sign = np.sign(values).astype(float)
    for index in range(1, sign.size):
        if sign[index] == 0:
            sign[index] = sign[index - 1]
    for index in range(sign.size - 2, -1, -1):
        if sign[index] == 0:
            sign[index] = sign[index + 1]
    return int(np.sum(sign[1:] * sign[:-1] < 0))


def count_major_extrema(values: np.ndarray, threshold: float) -> int:
    if values.size < 3 or threshold <= 0:
        return 0
    count = 0
    for index in range(1, values.size - 1):
        current = values[index]
        if abs(current) < threshold:
            continue
        if (current >= values[index - 1] and current > values[index + 1]) or (
            current <= values[index - 1] and current < values[index + 1]
        ):
            count += 1
    return count


def safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) < 1e-12:
        return float("nan")
    return numerator / denominator


def sustained_settle_index(abs_values: np.ndarray, start_idx: int, threshold: float, min_run: int = 20) -> int:
    if abs_values.size == 0:
        return 0
    run_length = 0
    for index in range(start_idx, abs_values.size):
        if abs_values[index] <= threshold:
            run_length += 1
            if run_length >= min_run:
                return index - run_length + 1
        else:
            run_length = 0
    return abs_values.size - 1


def detect_landmarks(time_s: np.ndarray, values: np.ndarray) -> dict[str, float]:
    x, y = finite_xy(time_s, values)
    if x.size == 0:
        return {}
    abs_y = np.abs(y)
    peak_idx = int(np.argmax(abs_y))
    peak_abs = float(abs_y[peak_idx])
    onset_idx = int(np.flatnonzero(abs_y >= (peak_abs * 0.10))[0]) if peak_abs > 0 and np.any(abs_y >= (peak_abs * 0.10)) else 0
    peak_sign = 1.0 if y[peak_idx] >= 0 else -1.0

    rebound_idx = peak_idx
    rebound_threshold = peak_abs * 0.15
    if peak_idx + 2 < y.size:
        search_indices = range(peak_idx + 1, y.size - 1)
        candidates: list[int] = []
        for index in search_indices:
            current = y[index]
            if abs(current) < rebound_threshold:
                continue
            if current * peak_sign >= 0:
                continue
            if (current >= y[index - 1] and current > y[index + 1]) or (current <= y[index - 1] and current < y[index + 1]):
                candidates.append(index)
        if candidates:
            rebound_idx = candidates[0]
        else:
            tail = abs_y[peak_idx + 1 :]
            if tail.size:
                rebound_idx = peak_idx + 1 + int(np.argmax(tail))

    settle_idx = sustained_settle_index(abs_y, start_idx=max(peak_idx + 1, rebound_idx), threshold=max(peak_abs * 0.10, 1e-9))
    return {
        "onset_idx": float(onset_idx),
        "onset_time_s": float(x[onset_idx]),
        "peak_idx": float(peak_idx),
        "peak_time_s": float(x[peak_idx]),
        "peak_abs": peak_abs,
        "peak_sign": peak_sign,
        "rebound_idx": float(rebound_idx),
        "rebound_time_s": float(x[rebound_idx]),
        "settle_idx": float(settle_idx),
        "settle_time_s": float(x[settle_idx]),
        "onset_to_peak_s": float(x[peak_idx] - x[onset_idx]),
        "peak_to_rebound_s": float(x[rebound_idx] - x[peak_idx]),
        "peak_to_settle_s": float(x[settle_idx] - x[peak_idx]),
    }


def resample_phase_segment(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    if x.size < 2:
        return np.full(PHASE_RESAMPLE_POINTS, np.nan, dtype=float)
    span = float(x[-1] - x[0])
    if span <= 1e-12:
        return np.full(PHASE_RESAMPLE_POINTS, np.nan, dtype=float)
    normalized_x = (x - x[0]) / span
    normalized_y = y.astype(float)
    amplitude = float(np.max(np.abs(normalized_y)))
    if amplitude > 1e-9:
        normalized_y = normalized_y / amplitude
    target = np.linspace(0.0, 1.0, PHASE_RESAMPLE_POINTS)
    return np.interp(target, normalized_x, normalized_y).astype(float)


def build_phase_segments(time_s: np.ndarray, values: np.ndarray, landmarks: dict[str, float]) -> dict[str, np.ndarray]:
    x, y = finite_xy(time_s, values)
    if x.size == 0 or not landmarks:
        return {}
    onset_idx = int(landmarks["onset_idx"])
    peak_idx = int(landmarks["peak_idx"])
    rebound_idx = int(max(landmarks["rebound_idx"], peak_idx))
    settle_idx = int(max(landmarks["settle_idx"], rebound_idx))
    phase_map: dict[str, np.ndarray] = {}

    build_end = max(onset_idx + 1, peak_idx)
    if build_end > onset_idx:
        phase_map["build"] = resample_phase_segment(x[onset_idx : build_end + 1], y[onset_idx : build_end + 1])
    rebound_end = max(peak_idx + 1, rebound_idx)
    if rebound_end > peak_idx:
        phase_map["rebound"] = resample_phase_segment(x[peak_idx : rebound_end + 1], y[peak_idx : rebound_end + 1])
    settle_end = max(rebound_idx + 1, settle_idx)
    if settle_end > rebound_idx:
        phase_map["settle"] = resample_phase_segment(x[rebound_idx : settle_end + 1], y[rebound_idx : settle_end + 1])
    return phase_map


def derivative_signal(time_s: np.ndarray, values: np.ndarray) -> np.ndarray:
    result = np.full(values.shape, np.nan, dtype=float)
    x, y = finite_xy(time_s, values)
    if x.size < 2:
        return result
    derivative = np.gradient(y, x)
    mask = np.isfinite(time_s) & np.isfinite(values)
    result[mask] = derivative
    return result


def cumulative_integral_signal(time_s: np.ndarray, values: np.ndarray) -> np.ndarray:
    result = np.full(values.shape, np.nan, dtype=float)
    x, y = finite_xy(time_s, values)
    if x.size < 2:
        return result
    trapezoids = np.diff(x) * ((y[1:] + y[:-1]) * 0.5)
    cumulative = np.concatenate([[0.0], np.cumsum(trapezoids)])
    mask = np.isfinite(time_s) & np.isfinite(values)
    result[mask] = cumulative
    return result


def derived_signal(values_name: str, time_s: np.ndarray, values: np.ndarray) -> np.ndarray:
    _, transform = DERIVED_SIGNAL_SPECS[values_name]
    if transform in {"jerk", "rate"}:
        return derivative_signal(time_s, values)
    if transform == "delta_v":
        return cumulative_integral_signal(time_s, values)
    return np.full(values.shape, np.nan, dtype=float)


def compute_cross_channel_lag_features(channel_features: dict[str, dict[str, float]]) -> dict[str, float]:
    def metric(channel_name: str, feature_name: str) -> float:
        return float(channel_features.get(channel_name, {}).get(feature_name, float("nan")))

    feature_map = {
        "seat_mid_onset_minus_vehicle_longitudinal_onset_s": metric("seat_mid_deflection_mm", "onset_time_abs") - metric("vehicle_longitudinal_accel_g", "onset_time_abs"),
        "seat_inner_onset_minus_vehicle_longitudinal_onset_s": metric("seat_inner_deflection_mm", "onset_time_abs") - metric("vehicle_longitudinal_accel_g", "onset_time_abs"),
        "seat_mid_peak_minus_vehicle_longitudinal_peak_s": metric("seat_mid_deflection_mm", "peak_abs_time_s") - metric("vehicle_longitudinal_accel_g", "peak_abs_time_s"),
        "seat_inner_peak_minus_vehicle_longitudinal_peak_s": metric("seat_inner_deflection_mm", "peak_abs_time_s") - metric("vehicle_longitudinal_accel_g", "peak_abs_time_s"),
        "foot_left_x_peak_minus_vehicle_longitudinal_peak_s": metric("foot_left_x_accel_g", "peak_abs_time_s") - metric("vehicle_longitudinal_accel_g", "peak_abs_time_s"),
        "foot_right_x_peak_minus_vehicle_longitudinal_peak_s": metric("foot_right_x_accel_g", "peak_abs_time_s") - metric("vehicle_longitudinal_accel_g", "peak_abs_time_s"),
        "foot_left_z_peak_minus_vehicle_longitudinal_peak_s": metric("foot_left_z_accel_g", "peak_abs_time_s") - metric("vehicle_longitudinal_accel_g", "peak_abs_time_s"),
        "foot_right_z_peak_minus_vehicle_longitudinal_peak_s": metric("foot_right_z_accel_g", "peak_abs_time_s") - metric("vehicle_longitudinal_accel_g", "peak_abs_time_s"),
        "vehicle_resultant_peak_minus_vehicle_longitudinal_peak_s": metric("vehicle_resultant_accel_g", "peak_abs_time_s") - metric("vehicle_longitudinal_accel_g", "peak_abs_time_s"),
        "seat_mid_rebound_minus_vehicle_longitudinal_rebound_s": metric("seat_mid_deflection_mm", "rebound_time_s") - metric("vehicle_longitudinal_accel_g", "rebound_time_s"),
        "seat_inner_rebound_minus_vehicle_longitudinal_rebound_s": metric("seat_inner_deflection_mm", "rebound_time_s") - metric("vehicle_longitudinal_accel_g", "rebound_time_s"),
        "lower_extremity_peak_spread_s": abs(metric("foot_left_x_accel_g", "peak_abs_time_s") - metric("foot_right_x_accel_g", "peak_abs_time_s")),
    }
    for key, value in list(feature_map.items()):
        if not math.isfinite(value):
            feature_map[key] = float("nan")
    return feature_map


def compute_channel_features(time_s: np.ndarray, values: np.ndarray) -> dict[str, float]:
    x, y = finite_xy(time_s, values)
    coverage_ratio = float(np.isfinite(values).sum() / values.size) if values.size else 0.0
    result = {feature_name: float("nan") for feature_name in ALL_FEATURES}
    result["coverage_ratio"] = coverage_ratio
    if x.size == 0:
        result["zero_crossing_count"] = 0.0
        return result

    abs_y = np.abs(y)
    peak_abs_idx = int(np.argmax(abs_y))
    peak_pos_idx = int(np.argmax(y))
    peak_neg_idx = int(np.argmin(y))
    peak_abs = float(abs_y[peak_abs_idx])
    landmarks = detect_landmarks(time_s, values)
    threshold_10 = peak_abs * 0.10
    threshold_90 = peak_abs * 0.90

    result["peak_abs"] = peak_abs
    result["peak_abs_time_s"] = float(x[peak_abs_idx])
    result["peak_positive"] = float(y[peak_pos_idx])
    result["peak_positive_time_s"] = float(x[peak_pos_idx])
    result["peak_negative"] = float(y[peak_neg_idx])
    result["peak_negative_time_s"] = float(x[peak_neg_idx])
    result["mean"] = float(np.mean(y))
    result["std"] = float(np.std(y))
    result["area"] = float(np.trapezoid(y, x)) if x.size >= 2 else 0.0
    result["area_abs"] = float(np.trapezoid(abs_y, x)) if x.size >= 2 else 0.0
    result["energy_proxy"] = float(np.trapezoid(np.square(y), x)) if x.size >= 2 else 0.0
    result["zero_crossing_count"] = float(count_zero_crossings(y))
    result["peak_to_peak"] = float(y[peak_pos_idx] - y[peak_neg_idx])
    result["end_value"] = float(y[-1])
    if landmarks:
        result["settle_time_abs"] = float(landmarks["settle_time_s"])
        result["onset_to_peak_s"] = float(landmarks["onset_to_peak_s"])
        result["peak_to_rebound_s"] = float(landmarks["peak_to_rebound_s"])
        result["peak_to_settle_s"] = float(landmarks["peak_to_settle_s"])

    onset_indices = np.flatnonzero(abs_y >= threshold_10) if peak_abs > 0 else np.array([], dtype=int)
    if onset_indices.size:
        onset_idx = int(onset_indices[0])
        result["onset_time_abs"] = float(x[onset_idx])
        result["impulse_width_10_abs"] = float(x[int(onset_indices[-1])] - x[onset_idx])
    if peak_abs > 0:
        rise_10 = np.flatnonzero(abs_y >= threshold_10)
        rise_90 = np.flatnonzero(abs_y >= threshold_90)
        if rise_10.size and rise_90.size:
            t10 = float(x[int(rise_10[0])])
            t90 = float(x[int(rise_90[0])])
            if t90 >= t10:
                result["rise_time_abs_10_90"] = t90 - t10
        over_50 = np.flatnonzero(abs_y >= (peak_abs * 0.50))
        if over_50.size:
            result["duration_above_50pct_abs"] = float(x[int(over_50[-1])] - x[int(over_50[0])])

    if x.size >= 2:
        dt = np.diff(x)
        dy = np.diff(y)
        valid = np.abs(dt) > 1e-12
        if np.any(valid):
            slopes = np.abs(dy[valid] / dt[valid])
            result["max_abs_slope"] = float(np.max(slopes))

    if result["area_abs"] and math.isfinite(result["area_abs"]) and result["area_abs"] > 0:
        result["centroid_time_abs"] = float(np.trapezoid(x * abs_y, x) / result["area_abs"]) if x.size >= 2 else float(x[peak_abs_idx])

    if x.size >= 2 and result["energy_proxy"] and math.isfinite(result["energy_proxy"]) and result["energy_proxy"] > 0:
        peak_time = float(x[peak_abs_idx])
        late_mask = x >= peak_time
        if np.count_nonzero(late_mask) >= 2:
            late_energy = float(np.trapezoid(np.square(y[late_mask]), x[late_mask]))
            result["late_energy_ratio"] = safe_ratio(late_energy, result["energy_proxy"])

    if peak_abs_idx + 2 < y.size:
        rebound_abs_y = abs_y[peak_abs_idx + 1 :]
        rebound_x = x[peak_abs_idx + 1 :]
        if rebound_abs_y.size:
            rebound_idx = int(np.argmax(rebound_abs_y))
            result["rebound_abs"] = float(rebound_abs_y[rebound_idx])
            result["rebound_time_s"] = float(rebound_x[rebound_idx])

    result["major_extrema_count"] = float(count_major_extrema(y, threshold=max(peak_abs * 0.20, 1e-9)))
    return result


def load_case_feature(case: CaseRow) -> CaseFeature:
    dataframe = pd.read_parquet(case.harmonized_wide_path)
    if "time_s" not in dataframe.columns:
        raise ValueError(f"time_s column missing: {case.harmonized_wide_path}")
    dataframe = crop_frame_to_analysis_window(dataframe)
    time_s = pd.to_numeric(dataframe["time_s"], errors="coerce").to_numpy(dtype=float)

    channel_features: dict[str, dict[str, float]] = {}
    signal_bank: dict[str, np.ndarray] = {}
    derived_signal_bank: dict[str, np.ndarray] = {}
    landmark_map: dict[str, dict[str, float]] = {}
    phase_bank: dict[str, dict[str, np.ndarray]] = {}
    feature_values: list[dict[str, Any]] = []
    vector_map: dict[str, float] = {}
    coverage_map: dict[str, float] = {}

    for channel_name in CHANNEL_ORDER:
        if channel_name in dataframe.columns:
            values = pd.to_numeric(dataframe[channel_name], errors="coerce").to_numpy(dtype=float)
        else:
            values = np.full(time_s.shape, np.nan, dtype=float)
        signal_bank[channel_name] = values
        features = compute_channel_features(time_s, values)
        landmarks = detect_landmarks(time_s, values)
        channel_features[channel_name] = features
        landmark_map[channel_name] = landmarks
        phase_bank[channel_name] = build_phase_segments(time_s, values, landmarks)
        coverage_map[channel_name] = float(features["coverage_ratio"])
        for feature_name, feature_value in features.items():
            feature_values.append(
                {
                    "standard_name": channel_name,
                    "feature_name": feature_name,
                    "feature_value_number": feature_value,
                    "feature_unit": unit_for_feature(channel_name, feature_name),
                }
            )
        for feature_name in VECTOR_FEATURES:
            vector_map[f"{channel_name}::{feature_name}"] = float(features[feature_name])

    for derived_name, (base_name, _transform) in DERIVED_SIGNAL_SPECS.items():
        derived_values = derived_signal(derived_name, time_s, signal_bank.get(base_name, np.full(time_s.shape, np.nan, dtype=float)))
        derived_signal_bank[derived_name] = derived_values
        derived_features = compute_channel_features(time_s, derived_values)
        coverage_map[derived_name] = float(derived_features["coverage_ratio"])
        for feature_name, feature_value in derived_features.items():
            feature_values.append(
                {
                    "standard_name": derived_name,
                    "feature_name": feature_name,
                    "feature_value_number": feature_value,
                    "feature_unit": unit_for_feature(derived_name, feature_name),
                }
            )
        for feature_name in DERIVED_VECTOR_FEATURES:
            vector_map[f"{derived_name}::{feature_name}"] = float(derived_features[feature_name])

    cross_channel_lags = compute_cross_channel_lag_features(channel_features)
    coverage_map["cross_channel_lag"] = float(np.mean([value for value in coverage_map.values() if math.isfinite(value)])) if coverage_map else 0.0
    for feature_name, feature_value in cross_channel_lags.items():
        feature_values.append(
            {
                "standard_name": "cross_channel_lag",
                "feature_name": feature_name,
                "feature_value_number": feature_value,
                "feature_unit": "s",
            }
        )
        vector_map[f"cross_channel_lag::{feature_name}"] = float(feature_value)

    return CaseFeature(
        case=case,
        time_s=time_s,
        channel_features=channel_features,
        signal_bank=signal_bank,
        derived_signal_bank=derived_signal_bank,
        landmark_map=landmark_map,
        phase_bank=phase_bank,
        feature_values=feature_values,
        vector_map=vector_map,
        coverage_map=coverage_map,
    )


def column_weight(column_name: str) -> float:
    standard_name, feature_name = column_name.split("::", 1)
    base_name = standard_base_name(standard_name)
    transform = standard_transform_name(standard_name)
    if standard_name == "cross_channel_lag":
        return 1.10 * CROSS_CHANNEL_FEATURE_WEIGHTS.get(feature_name, 1.0)
    base_weight = CHANNEL_WEIGHTS.get(base_name, 1.0)
    if transform == "jerk":
        base_weight *= 0.82
    elif transform == "rate":
        base_weight *= 0.86
    elif transform == "delta_v":
        base_weight *= 1.05
    return base_weight * FEATURE_WEIGHTS.get(feature_name, 1.0)


def view_for_standard_name(standard_name: str, feature_name: str) -> str | None:
    if standard_name == "cross_channel_lag":
        if "seat_" in feature_name:
            return "occupant"
        if "foot_" in feature_name or "lower_" in feature_name:
            return "lower_extremity"
        return "pulse"
    for view_name, channels in VIEW_CHANNELS.items():
        if standard_name in channels:
            return view_name
    base_name = standard_base_name(standard_name)
    for view_name, channels in VIEW_CHANNELS.items():
        if base_name in channels:
            return view_name
    return None


def build_view_indices(column_names: list[str]) -> dict[str, np.ndarray]:
    view_indices: dict[str, list[int]] = {view_name: [] for view_name in VIEW_CHANNELS}
    for index, column_name in enumerate(column_names):
        standard_name, feature_name = column_name.split("::", 1)
        view_name = view_for_standard_name(standard_name, feature_name)
        if view_name is not None:
            view_indices[view_name].append(index)
    return {view_name: np.array(indices, dtype=int) for view_name, indices in view_indices.items() if indices}


def build_feature_matrix(case_features: list[CaseFeature]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    column_names = sorted({column_name for case_feature in case_features for column_name in case_feature.vector_map})
    raw_matrix = np.full((len(case_features), len(column_names)), np.nan, dtype=float)
    for row_index, case_feature in enumerate(case_features):
        for col_index, column_name in enumerate(column_names):
            raw_matrix[row_index, col_index] = case_feature.vector_map.get(column_name, float("nan"))

    medians = np.zeros(raw_matrix.shape[1], dtype=float)
    scales = np.ones(raw_matrix.shape[1], dtype=float)
    for col_index in range(raw_matrix.shape[1]):
        column = raw_matrix[:, col_index]
        finite = column[np.isfinite(column)]
        if not finite.size:
            medians[col_index] = 0.0
            scales[col_index] = 1.0
            continue
        median = float(np.median(finite))
        q75, q25 = np.percentile(finite, [75, 25])
        iqr = float(q75 - q25)
        mad = float(np.median(np.abs(finite - median)) * 1.4826)
        scale = iqr / 1.349 if iqr > 1e-9 else mad
        if scale <= 1e-9:
            scale = float(np.std(finite))
        medians[col_index] = median
        scales[col_index] = scale if scale > 1e-9 else 1.0
    imputed = np.where(np.isfinite(raw_matrix), raw_matrix, medians)
    standardized = (imputed - medians) / scales
    standardized = np.clip(standardized, -8.0, 8.0)
    weights = np.sqrt(np.array([column_weight(column_name) for column_name in column_names], dtype=float))
    standardized = standardized * weights
    return raw_matrix, standardized, column_names


def cosine_similarity_matrix(standardized_matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(standardized_matrix, axis=1, keepdims=True)
    norms = np.where(norms > 1e-9, norms, 1.0)
    normalized = standardized_matrix / norms
    return normalized @ normalized.T


def euclidean_distance_matrix(standardized_matrix: np.ndarray) -> np.ndarray:
    squared = np.sum(np.square(standardized_matrix), axis=1, keepdims=True)
    distance_sq = np.maximum(squared + squared.T - (2.0 * (standardized_matrix @ standardized_matrix.T)), 0.0)
    return np.sqrt(distance_sq)


def series_overlap(values_a: np.ndarray, values_b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = np.isfinite(values_a) & np.isfinite(values_b)
    return values_a[mask], values_b[mask]


def weighted_signal_correlation(
    source: CaseFeature,
    target: CaseFeature,
) -> tuple[float, int]:
    weighted_sum = 0.0
    weight_total = 0.0
    overlap_channel_count = 0
    for channel_name in CHANNEL_ORDER:
        source_values = source.signal_bank[channel_name]
        target_values = target.signal_bank[channel_name]
        x, y = series_overlap(source_values, target_values)
        if x.size < 25:
            continue
        source_std = float(np.std(x))
        target_std = float(np.std(y))
        if source_std < 1e-9 or target_std < 1e-9:
            continue
        correlation = float(np.corrcoef(x, y)[0, 1])
        weight = CHANNEL_WEIGHTS.get(channel_name, 1.0)
        weighted_sum += weight * correlation
        weight_total += weight
        overlap_channel_count += 1
    if weight_total == 0.0:
        return float("nan"), 0
    return weighted_sum / weight_total, overlap_channel_count


def weighted_signal_rmse(source: CaseFeature, target: CaseFeature) -> tuple[float, int]:
    weighted_sum = 0.0
    weight_total = 0.0
    overlap_channel_count = 0
    for channel_name in CHANNEL_ORDER:
        source_values = source.signal_bank[channel_name]
        target_values = target.signal_bank[channel_name]
        x, y = series_overlap(source_values, target_values)
        if x.size < 25:
            continue
        amplitude = max(float(np.nanmax(np.abs(x))), float(np.nanmax(np.abs(y))), 1e-6)
        rmse = float(np.sqrt(np.mean(np.square(x - y))) / amplitude)
        weight = CHANNEL_WEIGHTS.get(channel_name, 1.0)
        weighted_sum += weight * rmse
        weight_total += weight
        overlap_channel_count += 1
    if weight_total == 0.0:
        return float("nan"), 0
    return weighted_sum / weight_total, overlap_channel_count


def downsample_valid(values: np.ndarray, step: int) -> np.ndarray:
    finite_mask = np.isfinite(values)
    if finite_mask.sum() < 30:
        return np.array([], dtype=float)
    index = np.flatnonzero(finite_mask)
    valid_values = values[index]
    sampled = valid_values[:: max(step, 1)]
    if sampled.size == 0 or sampled[-1] != valid_values[-1]:
        sampled = np.concatenate([sampled, valid_values[-1:]])
    sampled = sampled.astype(float)
    sampled -= float(np.mean(sampled))
    sampled_std = float(np.std(sampled))
    if sampled_std > 1e-9:
        sampled /= sampled_std
    return sampled


def banded_dtw_distance(sequence_a: np.ndarray, sequence_b: np.ndarray, window: int) -> float:
    if sequence_a.size == 0 or sequence_b.size == 0:
        return float("nan")
    band = max(window, abs(sequence_a.size - sequence_b.size))
    previous = np.full(sequence_b.size + 1, np.inf, dtype=float)
    previous[0] = 0.0
    for i in range(1, sequence_a.size + 1):
        current = np.full(sequence_b.size + 1, np.inf, dtype=float)
        start = max(1, i - band)
        stop = min(sequence_b.size, i + band) + 1
        for j in range(start, stop):
            cost = abs(sequence_a[i - 1] - sequence_b[j - 1])
            current[j] = cost + min(current[j - 1], previous[j], previous[j - 1])
        previous = current
    return float(previous[sequence_b.size] / (sequence_a.size + sequence_b.size))


def approximate_dtw_distance(source: CaseFeature, target: CaseFeature, step: int, window: int) -> float:
    weighted_sum = 0.0
    weight_total = 0.0
    for channel_name in DTW_PRIORITY_CHANNELS:
        sequence_a = downsample_valid(source.signal_bank[channel_name], step=step)
        sequence_b = downsample_valid(target.signal_bank[channel_name], step=step)
        if sequence_a.size >= 25 and sequence_b.size >= 25:
            weight = CHANNEL_WEIGHTS.get(channel_name, 1.0)
            weighted_sum += weight * banded_dtw_distance(sequence_a, sequence_b, window=window)
            weight_total += weight
    if weight_total == 0.0:
        return float("nan")
    return weighted_sum / weight_total


def build_view_matrices(
    standardized_matrix: np.ndarray,
    column_names: list[str],
) -> dict[str, dict[str, Any]]:
    view_indices = build_view_indices(column_names)
    payload: dict[str, dict[str, Any]] = {}
    for view_name, indices in view_indices.items():
        submatrix = standardized_matrix[:, indices]
        cosine = cosine_similarity_matrix(submatrix)
        distance = euclidean_distance_matrix(submatrix)
        scale = distance_scale(distance)
        distance_norm = distance / max(scale, 1e-6)
        payload[view_name] = {
            "indices": indices,
            "cosine": cosine,
            "distance": distance_norm,
            "weight": VIEW_WEIGHTS[view_name],
            "column_count": int(indices.size),
        }
    return payload


def phase_similarity_for_view(
    source: CaseFeature,
    target: CaseFeature,
    view_name: str,
) -> tuple[float, int]:
    weighted_sum = 0.0
    weight_total = 0.0
    comparisons = 0
    for channel_name in VIEW_CHANNELS[view_name]:
        source_phases = source.phase_bank.get(channel_name, {})
        target_phases = target.phase_bank.get(channel_name, {})
        if not source_phases or not target_phases:
            continue
        channel_weight = CHANNEL_WEIGHTS.get(standard_base_name(channel_name), 1.0)
        for phase_name in PHASE_NAMES:
            phase_a = source_phases.get(phase_name)
            phase_b = target_phases.get(phase_name)
            if phase_a is None or phase_b is None:
                continue
            if not np.isfinite(phase_a).all() or not np.isfinite(phase_b).all():
                continue
            corr = float(np.corrcoef(phase_a, phase_b)[0, 1]) if np.std(phase_a) > 1e-9 and np.std(phase_b) > 1e-9 else 0.0
            rmse = float(np.sqrt(np.mean(np.square(phase_a - phase_b))))
            score = 0.62 * ((corr + 1.0) / 2.0) + 0.38 * (1.0 / (1.0 + rmse))
            weight = channel_weight * PHASE_WEIGHTS[phase_name]
            weighted_sum += weight * score
            weight_total += weight
            comparisons += 1
    if weight_total == 0.0:
        return float("nan"), 0
    return weighted_sum / weight_total, comparisons


def phase_similarity_all_views(
    source: CaseFeature,
    target: CaseFeature,
) -> dict[str, dict[str, float]]:
    payload: dict[str, dict[str, float]] = {}
    for view_name in VIEW_CHANNELS:
        score, comparisons = phase_similarity_for_view(source, target, view_name)
        payload[view_name] = {
            "score": score,
            "comparisons": float(comparisons),
        }
    return payload


def multiview_similarity(
    row_index: int,
    candidate_index: int,
    view_matrices: dict[str, dict[str, Any]],
    phase_payload: dict[str, dict[str, float]],
) -> tuple[float, dict[str, float]]:
    weighted_sum = 0.0
    weight_total = 0.0
    detail: dict[str, float] = {}
    for view_name, view_matrix in view_matrices.items():
        base_score = 0.58 * ((float(view_matrix["cosine"][row_index, candidate_index]) + 1.0) / 2.0) + 0.42 * (
            1.0 / (1.0 + float(view_matrix["distance"][row_index, candidate_index]))
        )
        phase_score = phase_payload.get(view_name, {}).get("score", float("nan"))
        if math.isfinite(phase_score):
            score = 0.68 * base_score + 0.32 * phase_score
        else:
            score = base_score
        detail[view_name] = score
        weight = float(view_matrix["weight"])
        weighted_sum += weight * score
        weight_total += weight
    if weight_total == 0.0:
        return float("nan"), detail
    return weighted_sum / weight_total, detail


def silhouette_score(distance_matrix: np.ndarray, labels: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    if unique_labels.size < 2:
        return -1.0
    scores: list[float] = []
    for row_index in range(distance_matrix.shape[0]):
        same_mask = labels == labels[row_index]
        same_count = int(np.sum(same_mask))
        if same_count <= 1:
            scores.append(0.0)
            continue
        intra = float(np.sum(distance_matrix[row_index, same_mask]) / (same_count - 1))
        inter_candidates: list[float] = []
        for cluster_label in unique_labels:
            if cluster_label == labels[row_index]:
                continue
            other_mask = labels == cluster_label
            inter_candidates.append(float(np.mean(distance_matrix[row_index, other_mask])))
        inter = min(inter_candidates) if inter_candidates else intra
        denominator = max(intra, inter)
        scores.append((inter - intra) / denominator if denominator > 0 else 0.0)
    return float(np.mean(scores))


def availability_stats(source: CaseFeature, target: CaseFeature) -> tuple[int, int]:
    overlap_count = 0
    union_count = 0
    for channel_name in CHANNEL_ORDER:
        source_present = bool(np.isfinite(source.signal_bank[channel_name]).sum() >= 25)
        target_present = bool(np.isfinite(target.signal_bank[channel_name]).sum() >= 25)
        if source_present or target_present:
            union_count += 1
        if source_present and target_present:
            overlap_count += 1
    return overlap_count, union_count


def distance_scale(distance_matrix: np.ndarray) -> float:
    upper = distance_matrix[np.triu_indices_from(distance_matrix, k=1)]
    finite = upper[np.isfinite(upper) & (upper > 1e-12)]
    if not finite.size:
        return 1.0
    return float(np.median(finite))


def pca_reduce(
    standardized_matrix: np.ndarray,
    max_components: int = 12,
    variance_threshold: float = 0.93,
) -> tuple[np.ndarray, dict[str, Any]]:
    if standardized_matrix.size == 0:
        return standardized_matrix, {"selected_components": 0, "explained_variance_ratio": []}
    centered = standardized_matrix - np.mean(standardized_matrix, axis=0, keepdims=True)
    u, singular_values, vt = np.linalg.svd(centered, full_matrices=False)
    explained = np.square(singular_values)
    total = float(np.sum(explained))
    if total <= 1e-12:
        component_count = min(max_components, standardized_matrix.shape[1], max(1, standardized_matrix.shape[0]))
        return centered[:, :component_count], {"selected_components": component_count, "explained_variance_ratio": []}
    explained_ratio = explained / total
    max_allowed = min(max_components, vt.shape[0], standardized_matrix.shape[0])
    component_count = int(np.searchsorted(np.cumsum(explained_ratio[:max_allowed]), variance_threshold) + 1)
    component_count = max(1, min(component_count, max_allowed))
    reduced = centered @ vt[:component_count].T
    return reduced, {
        "selected_components": component_count,
        "explained_variance_ratio": json_clean(explained_ratio[:component_count]),
        "explained_variance_cumulative": float(np.sum(explained_ratio[:component_count])),
    }


def build_cluster_distance_matrix(
    standardized_matrix: np.ndarray,
    view_matrices: dict[str, dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    reduced_matrix, pca_info = pca_reduce(standardized_matrix)
    reduced_distance = euclidean_distance_matrix(reduced_matrix)
    reduced_scale = distance_scale(reduced_distance)
    reduced_distance_norm = reduced_distance / reduced_scale
    cosine_matrix = cosine_similarity_matrix(standardized_matrix)
    angular_distance = (1.0 - np.clip(cosine_matrix, -1.0, 1.0)) / 2.0
    cluster_distance = (0.34 * reduced_distance_norm) + (0.12 * angular_distance)
    total_view_weight = sum(float(view_matrix["weight"]) for view_matrix in view_matrices.values()) or 1.0
    for view_name, view_matrix in view_matrices.items():
        cluster_distance += (0.54 * float(view_matrix["weight"]) / total_view_weight) * np.asarray(view_matrix["distance"], dtype=float)
    np.fill_diagonal(cluster_distance, 0.0)
    pca_info["reduced_distance_scale"] = reduced_scale
    pca_info["view_columns"] = {view_name: int(view_matrix["column_count"]) for view_name, view_matrix in view_matrices.items()}
    return reduced_matrix, cluster_distance, pca_info


def initialize_medoids(distance_matrix: np.ndarray, cluster_count: int, rng: np.random.Generator) -> np.ndarray:
    medoids = [int(rng.integers(distance_matrix.shape[0]))]
    min_distances = distance_matrix[medoids[0]].copy()
    min_distances[medoids[0]] = 0.0
    while len(medoids) < cluster_count:
        candidate_scores = np.square(min_distances)
        for medoid in medoids:
            candidate_scores[medoid] = 0.0
        total = float(np.sum(candidate_scores))
        if total <= 1e-12:
            remaining = [index for index in range(distance_matrix.shape[0]) if index not in medoids]
            medoids.append(int(remaining[0]))
            continue
        probabilities = candidate_scores / total
        choice = int(rng.choice(distance_matrix.shape[0], p=probabilities))
        while choice in medoids:
            choice = int(rng.choice(distance_matrix.shape[0], p=probabilities))
        medoids.append(choice)
        min_distances = np.minimum(min_distances, distance_matrix[choice])
    return np.array(medoids, dtype=int)


def assign_medoids(distance_matrix: np.ndarray, medoids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    medoid_distances = distance_matrix[:, medoids]
    labels = np.argmin(medoid_distances, axis=1)
    distances = medoid_distances[np.arange(distance_matrix.shape[0]), labels]
    return labels.astype(int), distances.astype(float)


def fit_kmedoids(
    distance_matrix: np.ndarray,
    cluster_count: int,
    seed: int,
    max_iter: int = 100,
) -> tuple[np.ndarray, np.ndarray, float]:
    rng = np.random.default_rng(seed)
    medoids = initialize_medoids(distance_matrix, cluster_count, rng)
    labels = np.full(distance_matrix.shape[0], -1, dtype=int)
    distances = np.full(distance_matrix.shape[0], np.inf, dtype=float)
    for _ in range(max_iter):
        new_labels, new_distances = assign_medoids(distance_matrix, medoids)
        if np.array_equal(new_labels, labels):
            labels = new_labels
            distances = new_distances
            break
        labels = new_labels
        distances = new_distances
        updated_medoids = medoids.copy()
        for cluster_label in range(cluster_count):
            members = np.flatnonzero(labels == cluster_label)
            if members.size == 0:
                farthest_index = int(np.argmax(distances))
                if farthest_index not in updated_medoids:
                    updated_medoids[cluster_label] = farthest_index
                continue
            intra = distance_matrix[np.ix_(members, members)]
            costs = np.sum(intra, axis=1)
            updated_medoids[cluster_label] = int(members[int(np.argmin(costs))])
        if np.array_equal(updated_medoids, medoids):
            break
        medoids = updated_medoids
    final_labels, final_distances = assign_medoids(distance_matrix, medoids)
    total_cost = float(np.sum(final_distances))
    return final_labels, medoids, total_cost


def local_density_scores(distance_matrix: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lof_scores = np.ones(distance_matrix.shape[0], dtype=float)
    stability_scores = np.zeros(distance_matrix.shape[0], dtype=float)
    for cluster_label in np.unique(labels):
        members = np.flatnonzero(labels == cluster_label)
        if members.size <= 2:
            lof_scores[members] = 1.0
            stability_scores[members] = 1.0
            continue
        sub = distance_matrix[np.ix_(members, members)]
        k = min(max(5, int(math.ceil(members.size * 0.12))), members.size - 1)
        order = np.argsort(sub, axis=1)
        knn_indices = order[:, 1 : k + 1]
        knn_distances = np.take_along_axis(sub, knn_indices, axis=1)
        mean_knn_distance = np.mean(knn_distances, axis=1)
        local_density = 1.0 / np.maximum(mean_knn_distance, 1e-6)
        stability = 1.0 / (1.0 + mean_knn_distance)
        cluster_lof = np.ones(members.size, dtype=float)
        for local_index in range(members.size):
            neighbor_density = local_density[knn_indices[local_index]]
            cluster_lof[local_index] = float(np.mean(neighbor_density) / max(local_density[local_index], 1e-6))
        lof_scores[members] = cluster_lof
        stability_scores[members] = stability
    return lof_scores, stability_scores


def choose_clusters(
    standardized_matrix: np.ndarray,
    view_matrices: dict[str, dict[str, Any]],
    min_clusters: int,
    max_clusters: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    case_count = standardized_matrix.shape[0]
    if case_count < 3:
        labels = np.zeros(case_count, dtype=int)
        medoids = np.array([0], dtype=int) if case_count else np.empty((0,), dtype=int)
        cluster_distance = np.zeros((case_count, case_count), dtype=float)
        return labels, medoids, cluster_distance, {"selected_k": 1, "silhouette_score": None, "candidates": []}

    reduced_matrix, cluster_distance_matrix, pca_info = build_cluster_distance_matrix(standardized_matrix, view_matrices)
    upper = min(max_clusters, max(2, case_count - 1))
    lower = min(min_clusters, upper)
    min_cluster_size = max(5, int(math.ceil(case_count * 0.02)))
    best_valid_payload: tuple[np.ndarray, np.ndarray, float, int, float] | None = None
    best_fallback_payload: tuple[np.ndarray, np.ndarray, float, int, float] | None = None
    candidate_scores: list[dict[str, Any]] = []
    for cluster_count in range(lower, upper + 1):
        candidate_labels, candidate_medoids, total_cost = fit_kmedoids(
            cluster_distance_matrix, cluster_count, seed + cluster_count
        )
        score = silhouette_score(cluster_distance_matrix, candidate_labels)
        cluster_sizes = np.bincount(candidate_labels, minlength=cluster_count)
        valid = bool(cluster_sizes.min() >= min_cluster_size)
        candidate_scores.append(
            {
                "k": cluster_count,
                "silhouette_score": score,
                "total_cost": total_cost,
                "min_cluster_size": int(cluster_sizes.min()),
                "max_cluster_size": int(cluster_sizes.max()),
                "valid": valid,
            }
        )
        payload = (candidate_labels, candidate_medoids, score, cluster_count, total_cost)
        if best_fallback_payload is None or score > best_fallback_payload[2]:
            best_fallback_payload = payload
        if valid and (best_valid_payload is None or score > best_valid_payload[2]):
            best_valid_payload = payload
    selected_payload = best_valid_payload or best_fallback_payload
    assert selected_payload is not None
    labels, medoids, best_score, best_k, total_cost = selected_payload
    return labels, medoids, cluster_distance_matrix, {
        "selected_k": best_k,
        "silhouette_score": best_score,
        "total_cost": total_cost,
        "min_cluster_size_threshold": min_cluster_size,
        "selected_valid": best_valid_payload is not None,
        "pca": pca_info,
        "candidates": candidate_scores,
        "distance_scale": distance_scale(cluster_distance_matrix),
        "case_count": case_count,
        "reduced_shape": [int(reduced_matrix.shape[0]), int(reduced_matrix.shape[1])],
    }


def build_cluster_rows(
    case_features: list[CaseFeature],
    cluster_distance_matrix: np.ndarray,
    labels: np.ndarray,
    medoid_indices: np.ndarray,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not case_features:
        return [], [], []
    distances = cluster_distance_matrix[np.arange(cluster_distance_matrix.shape[0]), medoid_indices[labels]]
    lof_scores, stability_scores = local_density_scores(cluster_distance_matrix, labels)
    cluster_rows: list[dict[str, Any]] = []
    representatives: list[dict[str, Any]] = []
    outliers: list[dict[str, Any]] = []

    for cluster_label in np.unique(labels):
        member_indices = np.flatnonzero(labels == cluster_label)
        member_distances = distances[member_indices]
        median_distance = float(np.median(member_distances))
        mad = float(np.median(np.abs(member_distances - median_distance)))
        scale = max(mad * 1.4826, 1e-6)
        ordered_members = member_indices[np.argsort(member_distances)]
        medoid_index = int(medoid_indices[int(cluster_label)])
        cluster_coverages = np.array(
            [float(np.mean([value for value in case_features[int(idx)].coverage_map.values() if math.isfinite(value)])) for idx in member_indices],
            dtype=float,
        )
        stable_order = member_indices[np.argsort(-stability_scores[member_indices])]
        coverage_order = member_indices[np.argsort(-cluster_coverages)]
        boundary_order = member_indices[np.argsort(member_distances)[::-1]]

        for rank, member_index in enumerate(ordered_members[:3], start=1):
            representatives.append(
                {
                    "preprocessing_case_id": case_features[int(member_index)].case.preprocessing_case_id,
                    "cluster_label": int(cluster_label),
                    "representative_kind": "cluster_centroid",
                    "rank": rank,
                    "score": float(distances[int(member_index)]),
                }
            )
        for rank, member_index in enumerate(boundary_order[:3], start=1):
            representatives.append(
                {
                    "preprocessing_case_id": case_features[int(member_index)].case.preprocessing_case_id,
                    "cluster_label": int(cluster_label),
                    "representative_kind": "cluster_boundary",
                    "rank": rank,
                    "score": float(distances[int(member_index)]),
                }
            )
        for rank, member_index in enumerate(stable_order[:3], start=1):
            representatives.append(
                {
                    "preprocessing_case_id": case_features[int(member_index)].case.preprocessing_case_id,
                    "cluster_label": int(cluster_label),
                    "representative_kind": "cluster_stable",
                    "rank": rank,
                    "score": float(stability_scores[int(member_index)]),
                }
            )
        for rank, member_index in enumerate(coverage_order[:3], start=1):
            representatives.append(
                {
                    "preprocessing_case_id": case_features[int(member_index)].case.preprocessing_case_id,
                    "cluster_label": int(cluster_label),
                    "representative_kind": "cluster_high_coverage",
                    "rank": rank,
                    "score": float(cluster_coverages[np.where(member_indices == member_index)[0][0]]),
                }
            )

        for member_index in member_indices:
            robust_distance_score = float((distances[int(member_index)] - median_distance) / scale)
            local_density_score = max(0.0, (float(lof_scores[int(member_index)]) - 1.0) * 5.0)
            outlier_score = max(robust_distance_score, local_density_score)
            is_outlier = int(robust_distance_score >= 3.5 or float(lof_scores[int(member_index)]) >= 1.65)
            cluster_rows.append(
                {
                    "preprocessing_case_id": case_features[int(member_index)].case.preprocessing_case_id,
                    "cluster_label": int(cluster_label),
                    "centroid_distance": float(distances[int(member_index)]),
                    "outlier_score": outlier_score,
                    "is_outlier": is_outlier,
                    "cluster_medoid_case_id": case_features[medoid_index].case.preprocessing_case_id,
                    "robust_distance_score": robust_distance_score,
                    "local_density_outlier_score": float(lof_scores[int(member_index)]),
                    "stability_score": float(stability_scores[int(member_index)]),
                    "coverage_score": float(np.mean([value for value in case_features[int(member_index)].coverage_map.values() if math.isfinite(value)])),
                }
            )
            if is_outlier:
                outliers.append(
                    {
                        "filegroup_id": case_features[int(member_index)].case.filegroup_id,
                        "vehicle_make_model": case_features[int(member_index)].case.vehicle_make_model,
                        "cluster_label": int(cluster_label),
                        "outlier_score": outlier_score,
                        "local_density_outlier_score": float(lof_scores[int(member_index)]),
                    }
                )

    global_scores = np.sum(cluster_distance_matrix, axis=1)
    for rank, member_index in enumerate(np.argsort(global_scores)[:10], start=1):
        representatives.append(
            {
                "preprocessing_case_id": case_features[int(member_index)].case.preprocessing_case_id,
                "cluster_label": None,
                "representative_kind": "global_centroid",
                "rank": rank,
                "score": float(global_scores[int(member_index)] / max(1, cluster_distance_matrix.shape[0] - 1)),
            }
        )

    return cluster_rows, representatives, outliers


def combine_similarity(
    cosine_score: float,
    feature_distance: float,
    weighted_correlation: float,
    signal_rmse: float,
    dtw_distance: float,
    overlap_ratio: float,
    feature_distance_scale: float,
    multiview_score: float,
    pulse_phase_score: float,
) -> float:
    normalized_feature_distance = feature_distance / max(feature_distance_scale, 1e-6)
    components: list[tuple[float, float]] = [
        (((cosine_score + 1.0) / 2.0), 0.18),
        ((1.0 / (1.0 + normalized_feature_distance)), 0.10),
    ]
    if math.isfinite(weighted_correlation):
        components.append((((weighted_correlation + 1.0) / 2.0), 0.16))
    if math.isfinite(signal_rmse):
        components.append(((1.0 / (1.0 + signal_rmse)), 0.13))
    if math.isfinite(dtw_distance):
        components.append(((1.0 / (1.0 + dtw_distance)), 0.08))
    if math.isfinite(multiview_score):
        components.append((multiview_score, 0.24))
    if math.isfinite(pulse_phase_score):
        components.append((pulse_phase_score, 0.11))
    weight_sum = sum(weight for _, weight in components)
    similarity = sum(score * weight for score, weight in components) / weight_sum
    return similarity * (0.90 + (0.10 * overlap_ratio))


def build_neighbor_rows(
    case_features: list[CaseFeature],
    cosine_matrix: np.ndarray,
    feature_distance_matrix: np.ndarray,
    view_matrices: dict[str, dict[str, Any]],
    top_k: int,
    candidate_k: int,
    dtw_step: int,
    dtw_window: int,
) -> list[dict[str, Any]]:
    neighbor_rows: list[dict[str, Any]] = []
    case_count = len(case_features)
    feature_distance_scale = distance_scale(feature_distance_matrix)
    for row_index, source_feature in enumerate(case_features):
        if case_count <= 1:
            continue
        cosine_scores = cosine_matrix[row_index].copy()
        cosine_scores[row_index] = -np.inf
        feature_distances = feature_distance_matrix[row_index].copy()
        feature_distances[row_index] = np.inf
        candidate_count = min(candidate_k, case_count - 1)
        cosine_candidates = np.argpartition(-cosine_scores, candidate_count)[:candidate_count]
        distance_candidates = np.argpartition(feature_distances, candidate_count)[:candidate_count]
        candidate_indices = sorted(set(int(index) for index in np.concatenate([cosine_candidates, distance_candidates])))
        candidate_payloads: list[dict[str, Any]] = []
        for candidate_index in candidate_indices:
            if candidate_index == row_index:
                continue
            weighted_correlation, overlap_channel_count = weighted_signal_correlation(
                source_feature,
                case_features[int(candidate_index)],
            )
            signal_rmse, _ = weighted_signal_rmse(
                source_feature,
                case_features[int(candidate_index)],
            )
            dtw_distance = approximate_dtw_distance(
                source_feature,
                case_features[int(candidate_index)],
                step=dtw_step,
                window=dtw_window,
            )
            phase_payload = phase_similarity_all_views(source_feature, case_features[int(candidate_index)])
            multiview_score, multiview_detail = multiview_similarity(
                row_index,
                int(candidate_index),
                view_matrices=view_matrices,
                phase_payload=phase_payload,
            )
            overlap_count, union_count = availability_stats(source_feature, case_features[int(candidate_index)])
            overlap_ratio = safe_ratio(float(overlap_count), float(union_count)) if union_count else 0.0
            hybrid_distance = (
                0.32 * (float(feature_distance_matrix[row_index, int(candidate_index)]) / max(feature_distance_scale, 1e-6))
                + 0.20 * (signal_rmse if math.isfinite(signal_rmse) else 1.0)
                + 0.14 * (dtw_distance if math.isfinite(dtw_distance) else 1.0)
                + 0.24 * (1.0 - multiview_score if math.isfinite(multiview_score) else 1.0)
                + 0.10 * (1.0 - phase_payload.get("pulse", {}).get("score", 0.0) if math.isfinite(phase_payload.get("pulse", {}).get("score", float("nan"))) else 1.0)
            )
            similarity_score = combine_similarity(
                cosine_score=float(cosine_matrix[row_index, int(candidate_index)]),
                feature_distance=float(feature_distance_matrix[row_index, int(candidate_index)]),
                weighted_correlation=weighted_correlation,
                signal_rmse=signal_rmse,
                dtw_distance=dtw_distance,
                overlap_ratio=float(overlap_ratio),
                feature_distance_scale=feature_distance_scale,
                multiview_score=multiview_score,
                pulse_phase_score=phase_payload.get("pulse", {}).get("score", float("nan")),
            )
            candidate_payloads.append(
                {
                    "source_preprocessing_case_id": source_feature.case.preprocessing_case_id,
                    "target_preprocessing_case_id": case_features[int(candidate_index)].case.preprocessing_case_id,
                    "similarity_score": similarity_score,
                    "distance_score": hybrid_distance,
                    "weighted_correlation": weighted_correlation,
                    "dtw_distance": dtw_distance,
                    "overlap_channel_count": overlap_channel_count,
                    "multiview_score": multiview_score,
                    "pulse_view_score": multiview_detail.get("pulse", float("nan")),
                    "occupant_view_score": multiview_detail.get("occupant", float("nan")),
                    "lower_extremity_view_score": multiview_detail.get("lower_extremity", float("nan")),
                    "pulse_phase_score": phase_payload.get("pulse", {}).get("score", float("nan")),
                    "occupant_phase_score": phase_payload.get("occupant", {}).get("score", float("nan")),
                    "lower_extremity_phase_score": phase_payload.get("lower_extremity", {}).get("score", float("nan")),
                }
            )
        candidate_payloads.sort(key=lambda item: item["similarity_score"], reverse=True)
        for rank, payload in enumerate(candidate_payloads[:top_k], start=1):
            payload["rank"] = rank
            neighbor_rows.append(payload)
    return neighbor_rows


def create_feature_run(
    connection: sqlite3.Connection,
    source_mode: str,
    feature_space: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO preprocessing_feature_runs (
          started_at, parser_version, source_mode, feature_space, notes
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (utc_now_iso(), PARSER_VERSION, source_mode, feature_space, None),
    )
    connection.commit()
    return int(cursor.lastrowid)


def finish_feature_run(connection: sqlite3.Connection, preprocessing_feature_run_id: int, notes: dict[str, Any]) -> None:
    connection.execute(
        """
        UPDATE preprocessing_feature_runs
           SET finished_at = ?,
               notes = ?
         WHERE preprocessing_feature_run_id = ?
        """,
        (utc_now_iso(), json.dumps(json_clean(notes), ensure_ascii=False), preprocessing_feature_run_id),
    )
    connection.commit()


def replace_feature_sets(
    connection: sqlite3.Connection,
    preprocessing_feature_run_id: int,
    source_mode: str,
    feature_space: str,
    case_features: list[CaseFeature],
) -> dict[int, int]:
    ensure_preprocessing_schema(connection)
    connection.execute("PRAGMA foreign_keys = ON")
    target_case_ids = [case_feature.case.preprocessing_case_id for case_feature in case_features]
    if target_case_ids:
        placeholders = ",".join("?" for _ in target_case_ids)
        params = [source_mode, feature_space, *target_case_ids]
        connection.execute(
            f"""
            DELETE FROM preprocessing_neighbors
             WHERE source_feature_set_id IN (
                    SELECT preprocessing_feature_set_id
                      FROM preprocessing_feature_sets
                     WHERE source_mode = ?
                       AND feature_space = ?
                       AND preprocessing_case_id IN ({placeholders})
                  )
                OR target_feature_set_id IN (
                    SELECT preprocessing_feature_set_id
                      FROM preprocessing_feature_sets
                     WHERE source_mode = ?
                       AND feature_space = ?
                       AND preprocessing_case_id IN ({placeholders})
                  )
            """,
            [*params, *params],
        )
        connection.execute(
            f"""
            DELETE FROM preprocessing_clusters
             WHERE preprocessing_feature_set_id IN (
                    SELECT preprocessing_feature_set_id
                      FROM preprocessing_feature_sets
                     WHERE source_mode = ?
                       AND feature_space = ?
                       AND preprocessing_case_id IN ({placeholders})
                  )
            """,
            params,
        )
        connection.execute(
            f"""
            DELETE FROM preprocessing_representatives
             WHERE preprocessing_feature_set_id IN (
                    SELECT preprocessing_feature_set_id
                      FROM preprocessing_feature_sets
                     WHERE source_mode = ?
                       AND feature_space = ?
                       AND preprocessing_case_id IN ({placeholders})
                  )
            """,
            params,
        )
        connection.execute(
            f"""
            DELETE FROM preprocessing_feature_values
             WHERE preprocessing_feature_set_id IN (
                    SELECT preprocessing_feature_set_id
                      FROM preprocessing_feature_sets
                     WHERE source_mode = ?
                       AND feature_space = ?
                       AND preprocessing_case_id IN ({placeholders})
                  )
            """,
            params,
        )
    connection.execute(
        """
        DELETE FROM preprocessing_feature_sets
         WHERE source_mode = ?
           AND feature_space = ?
        """,
        (source_mode, feature_space),
    )
    connection.commit()

    now = utc_now_iso()
    feature_set_ids: dict[int, int] = {}
    for case_feature in case_features:
        vector_json = json.dumps(json_clean(case_feature.vector_map), ensure_ascii=False)
        coverage_json = json.dumps(json_clean(case_feature.coverage_map), ensure_ascii=False)
        cursor = connection.execute(
            """
            INSERT INTO preprocessing_feature_sets (
              preprocessing_feature_run_id, preprocessing_case_id, filegroup_id, source_mode, feature_space,
              status, feature_count, vector_json, coverage_json, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preprocessing_feature_run_id,
                case_feature.case.preprocessing_case_id,
                case_feature.case.filegroup_id,
                source_mode,
                feature_space,
                "done",
                len(case_feature.feature_values),
                vector_json,
                coverage_json,
                None,
                now,
                now,
            ),
        )
        feature_set_id = int(cursor.lastrowid)
        feature_set_ids[case_feature.case.preprocessing_case_id] = feature_set_id
        for feature_row in case_feature.feature_values:
            connection.execute(
                """
                INSERT INTO preprocessing_feature_values (
                  preprocessing_feature_set_id, standard_name, feature_name, feature_value_number, feature_unit
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    feature_set_id,
                    feature_row["standard_name"],
                    feature_row["feature_name"],
                    feature_row["feature_value_number"],
                    feature_row["feature_unit"],
                ),
            )
    connection.commit()
    return feature_set_ids


def persist_neighbor_rows(
    connection: sqlite3.Connection,
    preprocessing_feature_run_id: int,
    feature_space: str,
    feature_set_ids: dict[int, int],
    neighbor_rows: list[dict[str, Any]],
) -> None:
    for row in neighbor_rows:
        connection.execute(
            """
            INSERT INTO preprocessing_neighbors (
              preprocessing_feature_run_id, source_feature_set_id, target_feature_set_id, feature_space, rank,
              similarity_score, distance_score, weighted_correlation, dtw_distance, overlap_channel_count,
              multiview_score, pulse_view_score, occupant_view_score, lower_extremity_view_score,
              pulse_phase_score, occupant_phase_score, lower_extremity_phase_score, algorithm
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preprocessing_feature_run_id,
                feature_set_ids[row["source_preprocessing_case_id"]],
                feature_set_ids[row["target_preprocessing_case_id"]],
                feature_space,
                row["rank"],
                row["similarity_score"],
                row["distance_score"],
                row["weighted_correlation"],
                row["dtw_distance"],
                row["overlap_channel_count"],
                row.get("multiview_score"),
                row.get("pulse_view_score"),
                row.get("occupant_view_score"),
                row.get("lower_extremity_view_score"),
                row.get("pulse_phase_score"),
                row.get("occupant_phase_score"),
                row.get("lower_extremity_phase_score"),
                NEIGHBOR_ALGORITHM,
            ),
        )
    connection.commit()


def persist_cluster_rows(
    connection: sqlite3.Connection,
    preprocessing_feature_run_id: int,
    feature_space: str,
    feature_set_ids: dict[int, int],
    cluster_rows: list[dict[str, Any]],
    representative_rows: list[dict[str, Any]],
) -> None:
    for row in cluster_rows:
        connection.execute(
            """
            INSERT INTO preprocessing_clusters (
              preprocessing_feature_run_id, preprocessing_feature_set_id, feature_space, algorithm,
              cluster_label, centroid_distance, outlier_score, robust_distance_score,
              local_density_outlier_score, stability_score, coverage_score, is_outlier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preprocessing_feature_run_id,
                feature_set_ids[row["preprocessing_case_id"]],
                feature_space,
                CLUSTER_ALGORITHM,
                row["cluster_label"],
                row["centroid_distance"],
                row["outlier_score"],
                row.get("robust_distance_score"),
                row.get("local_density_outlier_score"),
                row.get("stability_score"),
                row.get("coverage_score"),
                row["is_outlier"],
            ),
        )
    for row in representative_rows:
        connection.execute(
            """
            INSERT INTO preprocessing_representatives (
              preprocessing_feature_run_id, preprocessing_feature_set_id, feature_space, algorithm,
              representative_kind, cluster_label, rank, score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preprocessing_feature_run_id,
                feature_set_ids[row["preprocessing_case_id"]],
                feature_space,
                REPRESENTATIVE_ALGORITHM,
                row["representative_kind"],
                row["cluster_label"],
                row["rank"],
                row["score"],
            ),
        )
    connection.commit()


def write_reports(
    output_dir: Path,
    source_mode: str,
    feature_space: str,
    case_features: list[CaseFeature],
    neighbor_rows: list[dict[str, Any]],
    cluster_rows: list[dict[str, Any]],
    representative_rows: list[dict[str, Any]],
    cluster_summary: dict[str, Any],
    outliers: list[dict[str, Any]],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = f"{sanitize_slug(source_mode)}__{sanitize_slug(feature_space)}"

    case_lookup = {case_feature.case.preprocessing_case_id: case_feature.case for case_feature in case_features}

    neighbor_records: list[dict[str, Any]] = []
    for row in neighbor_rows:
        source_case = case_lookup[row["source_preprocessing_case_id"]]
        target_case = case_lookup[row["target_preprocessing_case_id"]]
        neighbor_records.append(
            {
                "source_filegroup_id": source_case.filegroup_id,
                "source_vehicle": source_case.vehicle_make_model,
                "source_test_code": source_case.test_code,
                "target_filegroup_id": target_case.filegroup_id,
                "target_vehicle": target_case.vehicle_make_model,
                "target_test_code": target_case.test_code,
                "rank": row["rank"],
                "similarity_score": row["similarity_score"],
                "distance_score": row["distance_score"],
                "weighted_correlation": row["weighted_correlation"],
                "dtw_distance": row["dtw_distance"],
                "overlap_channel_count": row["overlap_channel_count"],
                "multiview_score": row.get("multiview_score"),
                "pulse_view_score": row.get("pulse_view_score"),
                "occupant_view_score": row.get("occupant_view_score"),
                "lower_extremity_view_score": row.get("lower_extremity_view_score"),
                "pulse_phase_score": row.get("pulse_phase_score"),
                "occupant_phase_score": row.get("occupant_phase_score"),
                "lower_extremity_phase_score": row.get("lower_extremity_phase_score"),
                "algorithm": NEIGHBOR_ALGORITHM,
            }
        )

    cluster_records: list[dict[str, Any]] = []
    cluster_lookup = {row["preprocessing_case_id"]: row for row in cluster_rows}
    best_neighbor_lookup: dict[int, dict[str, Any]] = {}
    for row in neighbor_rows:
        best_neighbor_lookup.setdefault(row["source_preprocessing_case_id"], row)
    for case_feature in case_features:
        cluster_row = cluster_lookup[case_feature.case.preprocessing_case_id]
        best_neighbor = best_neighbor_lookup.get(case_feature.case.preprocessing_case_id)
        neighbor_case = case_lookup[best_neighbor["target_preprocessing_case_id"]] if best_neighbor else None
        cluster_records.append(
            {
                "filegroup_id": case_feature.case.filegroup_id,
                "vehicle": case_feature.case.vehicle_make_model,
                "test_code": case_feature.case.test_code,
                "cluster_label": cluster_row["cluster_label"],
                "centroid_distance": cluster_row["centroid_distance"],
                "outlier_score": cluster_row["outlier_score"],
                "robust_distance_score": cluster_row.get("robust_distance_score"),
                "local_density_outlier_score": cluster_row.get("local_density_outlier_score"),
                "stability_score": cluster_row.get("stability_score"),
                "coverage_score": cluster_row.get("coverage_score"),
                "is_outlier": cluster_row["is_outlier"],
                "best_match_filegroup_id": neighbor_case.filegroup_id if neighbor_case else None,
                "best_match_vehicle": neighbor_case.vehicle_make_model if neighbor_case else None,
            }
        )

    representative_records: list[dict[str, Any]] = []
    for row in representative_rows:
        case = case_lookup[row["preprocessing_case_id"]]
        representative_records.append(
            {
                "filegroup_id": case.filegroup_id,
                "vehicle": case.vehicle_make_model,
                "test_code": case.test_code,
                "cluster_label": row["cluster_label"],
                "representative_kind": row["representative_kind"],
                "rank": row["rank"],
                "score": row["score"],
                "algorithm": REPRESENTATIVE_ALGORITHM,
            }
        )

    neighbor_path = output_dir / f"signal_feature_neighbors__{slug}.csv"
    cluster_path = output_dir / f"signal_feature_clusters__{slug}.csv"
    representative_path = output_dir / f"signal_feature_representatives__{slug}.csv"
    summary_path = output_dir / f"signal_feature_summary__{slug}.json"

    pd.DataFrame(neighbor_records).to_csv(neighbor_path, index=False)
    pd.DataFrame(cluster_records).to_csv(cluster_path, index=False)
    pd.DataFrame(representative_records).to_csv(representative_path, index=False)
    summary_path.write_text(
        json.dumps(
            json_clean(
                {
                    "parser_version": PARSER_VERSION,
                    "source_mode": source_mode,
                    "feature_space": feature_space,
                    "analysis_window_s": [ANALYSIS_WINDOW_START_S, ANALYSIS_WINDOW_END_S],
                    "case_count": len(case_features),
                    "neighbor_count": len(neighbor_rows),
                    "cluster_count": cluster_summary.get("selected_k"),
                    "silhouette_score": cluster_summary.get("silhouette_score"),
                    "cluster_candidates": cluster_summary.get("candidates"),
                    "outlier_count": len(outliers),
                    "outliers": outliers[:25],
                    "reports": {
                        "neighbors_csv": str(neighbor_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                        "clusters_csv": str(cluster_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                        "representatives_csv": str(representative_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    },
                }
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "neighbors_csv": str(neighbor_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "clusters_csv": str(cluster_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "representatives_csv": str(representative_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "summary_json": str(summary_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_dir = resolve_repo_path(args.output_dir) if args.output_dir else OUTPUT_ROOT

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        ensure_preprocessing_schema(connection)
        cases = load_cases(connection, source_mode=args.source_mode, limit=args.limit)
        if not cases:
            raise ValueError(f"No harmonized preprocessing cases found for mode={args.source_mode}")

        case_features = [load_case_feature(case) for case in cases]
        raw_matrix, standardized_matrix, feature_columns = build_feature_matrix(case_features)
        cosine_matrix = cosine_similarity_matrix(standardized_matrix)
        feature_distance_matrix = euclidean_distance_matrix(standardized_matrix)
        view_matrices = build_view_matrices(standardized_matrix, feature_columns)
        labels, medoid_indices, cluster_distance_matrix, cluster_summary = choose_clusters(
            standardized_matrix,
            view_matrices=view_matrices,
            min_clusters=args.min_clusters,
            max_clusters=args.max_clusters,
            seed=args.seed,
        )
        cluster_rows, representative_rows, outliers = build_cluster_rows(
            case_features=case_features,
            cluster_distance_matrix=cluster_distance_matrix,
            labels=labels,
            medoid_indices=medoid_indices,
        )
        neighbor_rows = build_neighbor_rows(
            case_features=case_features,
            cosine_matrix=cosine_matrix,
            feature_distance_matrix=feature_distance_matrix,
            view_matrices=view_matrices,
            top_k=args.top_k,
            candidate_k=args.candidate_k,
            dtw_step=args.dtw_step,
            dtw_window=args.dtw_window,
        )

        preprocessing_feature_run_id = create_feature_run(
            connection,
            source_mode=args.source_mode,
            feature_space=args.feature_space,
        )
        feature_set_ids = replace_feature_sets(
            connection=connection,
            preprocessing_feature_run_id=preprocessing_feature_run_id,
            source_mode=args.source_mode,
            feature_space=args.feature_space,
            case_features=case_features,
        )
        persist_neighbor_rows(
            connection=connection,
            preprocessing_feature_run_id=preprocessing_feature_run_id,
            feature_space=args.feature_space,
            feature_set_ids=feature_set_ids,
            neighbor_rows=neighbor_rows,
        )
        persist_cluster_rows(
            connection=connection,
            preprocessing_feature_run_id=preprocessing_feature_run_id,
            feature_space=args.feature_space,
            feature_set_ids=feature_set_ids,
            cluster_rows=cluster_rows,
            representative_rows=representative_rows,
        )

        reports = write_reports(
            output_dir=output_dir,
            source_mode=args.source_mode,
            feature_space=args.feature_space,
            case_features=case_features,
            neighbor_rows=neighbor_rows,
            cluster_rows=cluster_rows,
            representative_rows=representative_rows,
            cluster_summary=cluster_summary,
            outliers=outliers,
        )

        notes = {
            "analysis_window_s": [ANALYSIS_WINDOW_START_S, ANALYSIS_WINDOW_END_S],
            "case_count": len(case_features),
            "feature_columns": feature_columns,
            "feature_value_count": int(sum(len(case_feature.feature_values) for case_feature in case_features)),
            "neighbor_count": len(neighbor_rows),
            "cluster_count": cluster_summary.get("selected_k"),
            "silhouette_score": cluster_summary.get("silhouette_score"),
            "outlier_count": len(outliers),
            "view_matrices": {view_name: {"column_count": payload["column_count"], "weight": payload["weight"]} for view_name, payload in view_matrices.items()},
            "reports": reports,
        }
        finish_feature_run(connection, preprocessing_feature_run_id, notes)
        print(json.dumps(json_clean({"preprocessing_feature_run_id": preprocessing_feature_run_id, **notes}), ensure_ascii=False, indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
