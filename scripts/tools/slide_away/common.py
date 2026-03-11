from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
SLIDE_AWAY_ROOT = REPO_ROOT / "slide_away"
ARTIFACTS_ROOT = SLIDE_AWAY_ROOT / "artifacts"
ARTIFACT_MARTS = ARTIFACTS_ROOT / "marts"
ARTIFACT_TABLES = ARTIFACTS_ROOT / "tables"
ARTIFACT_FIGURES = ARTIFACTS_ROOT / "figures"
ARTIFACT_LOGS = ARTIFACTS_ROOT / "logs"
REVIEWS_ROOT = SLIDE_AWAY_ROOT / "reviews"
REVIEW_GOVERNANCE_ROOT = REVIEWS_ROOT / "01_governance"
REVIEW_EXECUTION_ROOT = REVIEWS_ROOT / "02_execution"
REVIEW_ANALYSIS_ROOT = REVIEWS_ROOT / "03_analysis"
REVIEW_CASEBOOKS_ROOT = REVIEWS_ROOT / "04_casebooks"
CANONICAL_CSV = REPO_ROOT / "output" / "small_overlap" / "tables" / "canonical_small_overlap_tests.csv"
CASE_MASTER_DEFAULT = ARTIFACT_MARTS / "case_master.parquet"
OUTCOMES_DEFAULT = ARTIFACT_MARTS / "outcomes_v1.parquet"
FEATURES_DEFAULT = ARTIFACT_MARTS / "features_v1.parquet"
FEATURES_STRICT_DEFAULT = ARTIFACT_MARTS / "features_v1_strict_origin.parquet"
MODE_ASSIGNMENTS_DEFAULT = ARTIFACT_TABLES / "mode_case_assignments.csv"
WINDOW_GRID_MS = (20, 40, 60, 80, 100, 120, 150, 250)
FEATURE_VERSION = "slide-away-features:v1"
OUTCOME_VERSION = "slide-away-outcomes:v1"
CASE_MASTER_VERSION = "slide-away-case-master:v1"


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def ensure_dirs() -> None:
    for path in (
        ARTIFACT_MARTS,
        ARTIFACT_TABLES,
        ARTIFACT_FIGURES,
        ARTIFACT_LOGS,
        REVIEWS_ROOT,
        REVIEW_GOVERNANCE_ROOT,
        REVIEW_EXECUTION_ROOT,
        REVIEW_ANALYSIS_ROOT,
        REVIEW_CASEBOOKS_ROOT,
    ):
        path.mkdir(parents=True, exist_ok=True)


def write_log(log_path: Path, lines: Iterable[str]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [line.rstrip() for line in lines]
    log_path.write_text("\n".join(payload) + "\n", encoding="utf-8")


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def open_connection(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(resolve_path(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def load_canonical(path: str | Path = CANONICAL_CSV) -> pd.DataFrame:
    dataframe = pd.read_csv(resolve_path(path))
    if "filegroup_id" in dataframe.columns:
        dataframe["filegroup_id"] = pd.to_numeric(dataframe["filegroup_id"], errors="coerce").astype("Int64")
    return dataframe


def normalize_make_model_family(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^\d{4}\s+", "", text)
    text = text.split(" into ")[0]
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\bSmall Overlap\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bR&D\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*-\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,")


def classify_analysis_cohort(row: pd.Series) -> str:
    side = str(row.get("test_side") or "unknown")
    era = str(row.get("era") or "unknown-era")
    signal_state = "signal-ready" if bool(row.get("signal_ready_flag")) else "signal-missing"
    return f"{era}|{side}|{signal_state}"


def side_factor(test_side: str | None) -> float:
    normalized = str(test_side or "").strip().lower()
    if normalized == "passenger":
        return -1.0
    return 1.0


def max_abs(series: pd.Series) -> float:
    valid = pd.to_numeric(series, errors="coerce").dropna()
    if valid.empty:
        return float("nan")
    return float(valid.abs().max())


def min_positive(series: pd.Series) -> float:
    valid = pd.to_numeric(series, errors="coerce").dropna()
    valid = valid.loc[valid >= 0]
    if valid.empty:
        return float("nan")
    return float(valid.min())


def safe_float(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return numeric if math.isfinite(numeric) else float("nan")


def cumulative_delta_v_mps(time_s: np.ndarray, accel_g: np.ndarray) -> np.ndarray:
    time = np.asarray(time_s, dtype=float)
    accel = np.asarray(accel_g, dtype=float)
    if time.size == 0 or accel.size == 0:
        return np.array([], dtype=float)
    values = np.nan_to_num(accel, nan=0.0)
    dt = np.diff(time, prepend=time[0])
    if dt.size:
        dt[0] = 0.0
    return np.cumsum(values * 9.80665 * dt)


def value_at_or_before(time_s: np.ndarray, values: np.ndarray, target_s: float) -> float:
    if time_s.size == 0 or values.size == 0:
        return float("nan")
    mask = np.asarray(time_s, dtype=float) <= (target_s + 1e-12)
    if not np.any(mask):
        return float("nan")
    return safe_float(np.asarray(values, dtype=float)[mask][-1])


def time_of_half_final_abs(time_s: np.ndarray, cumulative_values: np.ndarray, target_s: float) -> float:
    if time_s.size == 0 or cumulative_values.size == 0:
        return float("nan")
    final_value = value_at_or_before(time_s, cumulative_values, target_s)
    if not math.isfinite(final_value) or abs(final_value) < 1e-9:
        return float("nan")
    threshold = abs(final_value) * 0.5
    subset_mask = np.asarray(time_s, dtype=float) <= (target_s + 1e-12)
    subset_time = np.asarray(time_s, dtype=float)[subset_mask]
    subset_values = np.abs(np.asarray(cumulative_values, dtype=float)[subset_mask])
    indices = np.flatnonzero(subset_values >= threshold)
    if indices.size == 0:
        return float("nan")
    return safe_float(subset_time[indices[0]] * 1000.0)


def peak_time_ms(time_s: np.ndarray, values: np.ndarray, target_s: float) -> float:
    subset_mask = np.asarray(time_s, dtype=float) <= (target_s + 1e-12)
    subset_time = np.asarray(time_s, dtype=float)[subset_mask]
    subset_values = np.asarray(values, dtype=float)[subset_mask]
    finite_mask = np.isfinite(subset_time) & np.isfinite(subset_values)
    if not np.any(finite_mask):
        return float("nan")
    subset_time = subset_time[finite_mask]
    subset_values = subset_values[finite_mask]
    if subset_time.size == 0:
        return float("nan")
    peak_index = int(np.argmax(np.abs(subset_values)))
    return safe_float(subset_time[peak_index] * 1000.0)


def max_abs_until(time_s: np.ndarray, values: np.ndarray, target_s: float) -> float:
    subset_mask = np.asarray(time_s, dtype=float) <= (target_s + 1e-12)
    subset_values = np.asarray(values, dtype=float)[subset_mask]
    finite = subset_values[np.isfinite(subset_values)]
    if finite.size == 0:
        return float("nan")
    return safe_float(np.max(np.abs(finite)))


def pulse_duration_ms(time_s: np.ndarray, values: np.ndarray, target_s: float, fraction: float = 0.10) -> float:
    subset_mask = np.asarray(time_s, dtype=float) <= (target_s + 1e-12)
    subset_time = np.asarray(time_s, dtype=float)[subset_mask]
    subset_values = np.asarray(values, dtype=float)[subset_mask]
    finite_mask = np.isfinite(subset_time) & np.isfinite(subset_values)
    if not np.any(finite_mask):
        return float("nan")
    subset_time = subset_time[finite_mask]
    subset_values = subset_values[finite_mask]
    if subset_time.size == 0:
        return float("nan")
    peak = float(np.max(np.abs(subset_values)))
    if peak <= 0:
        return 0.0
    active = np.abs(subset_values) >= (peak * fraction)
    if not np.any(active):
        return 0.0
    first = subset_time[np.flatnonzero(active)[0]]
    last = subset_time[np.flatnonzero(active)[-1]]
    return safe_float((last - first) * 1000.0)


def build_safety_score(dataframe: pd.DataFrame) -> pd.Series:
    components = pd.DataFrame(
        {
            "intrusion": pd.to_numeric(dataframe.get("intrusion_max_resultant_cm"), errors="coerce"),
            "leg_index": pd.concat(
                [
                    pd.to_numeric(dataframe.get("leg_foot_index_left"), errors="coerce"),
                    pd.to_numeric(dataframe.get("leg_foot_index_right"), errors="coerce"),
                ],
                axis=1,
            ).max(axis=1),
            "foot_accel": pd.concat(
                [
                    pd.to_numeric(dataframe.get("foot_resultant_accel_left_g"), errors="coerce"),
                    pd.to_numeric(dataframe.get("foot_resultant_accel_right_g"), errors="coerce"),
                ],
                axis=1,
            ).max(axis=1),
            "hic15": pd.to_numeric(dataframe.get("head_hic15"), errors="coerce"),
            "rib_comp": pd.to_numeric(dataframe.get("chest_rib_compression_mm"), errors="coerce").abs(),
            "nij": pd.to_numeric(dataframe.get("neck_tension_extension_nij"), errors="coerce"),
            "thigh_proxy": pd.to_numeric(dataframe.get("thigh_hip_risk_proxy"), errors="coerce"),
        }
    )
    score = pd.Series(0.0, index=dataframe.index, dtype=float)
    valid_component_count = pd.Series(0.0, index=dataframe.index, dtype=float)
    for column in components.columns:
        series = pd.to_numeric(components[column], errors="coerce")
        valid = series.dropna()
        if valid.empty:
            continue
        center = float(valid.median())
        spread = float(valid.std(ddof=0))
        if not math.isfinite(spread) or spread <= 1e-9:
            normalized = series - center
        else:
            normalized = (series - center) / spread
        score = score.add(normalized.fillna(0.0), fill_value=0.0)
        valid_component_count = valid_component_count.add(series.notna().astype(float), fill_value=0.0)
    valid_mask = valid_component_count > 0
    score.loc[~valid_mask] = np.nan
    score.loc[valid_mask] = score.loc[valid_mask] / valid_component_count.loc[valid_mask]
    return score


@dataclass(frozen=True)
class SlideAwayMetrics:
    default_metrics: dict[str, float]
    window_metrics: dict[int, dict[str, float]]
    quality_score: float
    cluster_input_flag: int


def compute_slide_away_metrics(
    frame: pd.DataFrame,
    test_side: str | None,
    v0_mps: float,
    windows_ms: Iterable[int] = WINDOW_GRID_MS,
    default_window_ms: int = 150,
) -> SlideAwayMetrics:
    def column_values(column_name: str) -> np.ndarray:
        if column_name in frame.columns:
            return pd.to_numeric(frame[column_name], errors="coerce").to_numpy(dtype=float)
        if "time_s" in frame.columns:
            size = len(frame["time_s"])
        else:
            size = len(frame.index)
        return np.full(size, np.nan, dtype=float)

    time_s = column_values("time_s")
    ax = column_values("vehicle_longitudinal_accel_g")
    ay = column_values("vehicle_lateral_accel_g")
    az = column_values("vehicle_vertical_accel_g")
    resultant = column_values("vehicle_resultant_accel_g")
    ay_away = ay * side_factor(test_side)
    seat_mid = column_values("seat_mid_deflection_mm")
    seat_inner = column_values("seat_inner_deflection_mm")
    foot_left_x = column_values("foot_left_x_accel_g")
    foot_left_z = column_values("foot_left_z_accel_g")
    foot_right_x = column_values("foot_right_x_accel_g")
    foot_right_z = column_values("foot_right_z_accel_g")

    cumulative_dvx = cumulative_delta_v_mps(time_s, ax)
    cumulative_dvy_away = cumulative_delta_v_mps(time_s, ay_away)
    foot_left_resultant = np.sqrt(np.square(np.nan_to_num(foot_left_x, nan=0.0)) + np.square(np.nan_to_num(foot_left_z, nan=0.0)))
    foot_right_resultant = np.sqrt(np.square(np.nan_to_num(foot_right_x, nan=0.0)) + np.square(np.nan_to_num(foot_right_z, nan=0.0)))
    seat_twist = np.abs(seat_inner - seat_mid)

    v0 = safe_float(v0_mps)
    if not math.isfinite(v0) or v0 <= 0:
        v0 = float("nan")

    window_metrics: dict[int, dict[str, float]] = {}
    for window_ms in windows_ms:
        window_s = float(window_ms) / 1000.0
        delta_vx = value_at_or_before(time_s, cumulative_dvx, window_s)
        delta_vy = value_at_or_before(time_s, cumulative_dvy_away, window_s)
        abs_delta_vx = abs(delta_vx) if math.isfinite(delta_vx) else float("nan")
        abs_delta_vy = abs(delta_vy) if math.isfinite(delta_vy) else float("nan")
        ri_value = (
            abs_delta_vy / abs_delta_vx
            if math.isfinite(abs_delta_vy) and math.isfinite(abs_delta_vx) and abs_delta_vx >= 0.25
            else float("nan")
        )
        window_metrics[int(window_ms)] = {
            "delta_vx_mps": delta_vx,
            "delta_vy_away_mps": delta_vy,
            "lr": abs_delta_vx / v0 if math.isfinite(abs_delta_vx) and math.isfinite(v0) and v0 > 0 else float("nan"),
            "ly": abs_delta_vy / v0 if math.isfinite(abs_delta_vy) and math.isfinite(v0) and v0 > 0 else float("nan"),
            "ri": ri_value,
            "max_abs_ax_g": max_abs_until(time_s, ax, window_s),
            "max_abs_ay_g": max_abs_until(time_s, ay_away, window_s),
            "max_abs_az_g": max_abs_until(time_s, az, window_s),
            "max_abs_resultant_g": max_abs_until(time_s, resultant, window_s),
            "pulse_duration_x_ms": pulse_duration_ms(time_s, ax, window_s),
            "pulse_duration_y_ms": pulse_duration_ms(time_s, ay_away, window_s),
            "pulse_duration_z_ms": pulse_duration_ms(time_s, az, window_s),
            "seat_twist_peak_mm": max_abs_until(time_s, seat_twist, window_s),
            "foot_resultant_left_g": max_abs_until(time_s, foot_left_resultant, window_s),
            "foot_resultant_right_g": max_abs_until(time_s, foot_right_resultant, window_s),
            "foot_x_left_right_diff_g": max_abs_until(time_s, foot_left_x - foot_right_x, window_s),
            "foot_z_left_right_diff_g": max_abs_until(time_s, foot_left_z - foot_right_z, window_s),
        }
        left_peak = window_metrics[int(window_ms)]["foot_resultant_left_g"]
        right_peak = window_metrics[int(window_ms)]["foot_resultant_right_g"]
        window_metrics[int(window_ms)]["foot_resultant_asymmetry_g"] = (
            abs(left_peak - right_peak) if math.isfinite(left_peak) and math.isfinite(right_peak) else float("nan")
        )

    default_window_s = float(default_window_ms) / 1000.0
    default_window = window_metrics[int(default_window_ms)]
    seat_peak_time = peak_time_ms(time_s, seat_twist, default_window_s)
    foot_left_peak_time = peak_time_ms(time_s, foot_left_resultant, default_window_s)
    foot_right_peak_time = peak_time_ms(time_s, foot_right_resultant, default_window_s)
    vehicle_x_peak_time = peak_time_ms(time_s, ax, default_window_s)

    default_metrics = {
        "window_s": default_window_s,
        "delta_vx_mps": default_window["delta_vx_mps"],
        "delta_vy_away_mps": default_window["delta_vy_away_mps"],
        "lr": window_metrics.get(60, {}).get("lr", float("nan")),
        "lr_100": window_metrics.get(100, {}).get("lr", float("nan")),
        "ly": window_metrics.get(60, {}).get("ly", float("nan")),
        "ly_40": window_metrics.get(40, {}).get("ly", float("nan")),
        "ly_60": window_metrics.get(60, {}).get("ly", float("nan")),
        "ri": window_metrics.get(60, {}).get("ri", float("nan")),
        "ri_60": window_metrics.get(60, {}).get("ri", float("nan")),
        "t_peak_x_ms": vehicle_x_peak_time,
        "t_peak_y_ms": peak_time_ms(time_s, ay_away, default_window_s),
        "t_peak_z_ms": peak_time_ms(time_s, az, default_window_s),
        "t_50_dvx_ms": time_of_half_final_abs(time_s, cumulative_dvx, default_window_s),
        "max_abs_ax_g": default_window["max_abs_ax_g"],
        "max_abs_ay_g": default_window["max_abs_ay_g"],
        "max_abs_az_g": default_window["max_abs_az_g"],
        "max_abs_resultant_g": default_window["max_abs_resultant_g"],
        "pulse_duration_x_ms": default_window["pulse_duration_x_ms"],
        "pulse_duration_y_ms": default_window["pulse_duration_y_ms"],
        "pulse_duration_z_ms": default_window["pulse_duration_z_ms"],
        "seat_twist_peak_mm": default_window["seat_twist_peak_mm"],
        "foot_resultant_left_g": default_window["foot_resultant_left_g"],
        "foot_resultant_right_g": default_window["foot_resultant_right_g"],
        "foot_resultant_asymmetry_g": default_window["foot_resultant_asymmetry_g"],
        "foot_x_left_right_diff_g": default_window["foot_x_left_right_diff_g"],
        "foot_z_left_right_diff_g": default_window["foot_z_left_right_diff_g"],
        "seat_peak_minus_vehicle_peak_ms": seat_peak_time - vehicle_x_peak_time
        if math.isfinite(seat_peak_time) and math.isfinite(vehicle_x_peak_time)
        else float("nan"),
        "foot_left_peak_minus_vehicle_peak_ms": foot_left_peak_time - vehicle_x_peak_time
        if math.isfinite(foot_left_peak_time) and math.isfinite(vehicle_x_peak_time)
        else float("nan"),
        "foot_right_peak_minus_vehicle_peak_ms": foot_right_peak_time - vehicle_x_peak_time
        if math.isfinite(foot_right_peak_time) and math.isfinite(vehicle_x_peak_time)
        else float("nan"),
    }

    required = [
        default_metrics["delta_vx_mps"],
        default_metrics["delta_vy_away_mps"],
        default_metrics["ri"],
        default_metrics["max_abs_ax_g"],
        default_metrics["max_abs_ay_g"],
        default_metrics["max_abs_az_g"],
        default_metrics["seat_twist_peak_mm"],
        default_metrics["foot_resultant_left_g"],
        default_metrics["foot_resultant_right_g"],
    ]
    finite_required = [value for value in required if math.isfinite(safe_float(value))]
    quality_score = len(finite_required) / len(required)
    cluster_input_flag = int(quality_score >= 0.875)
    return SlideAwayMetrics(
        default_metrics=default_metrics,
        window_metrics=window_metrics,
        quality_score=quality_score,
        cluster_input_flag=cluster_input_flag,
    )


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
