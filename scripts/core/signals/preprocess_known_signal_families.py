from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from nptdms import TdmsFile


REPO_ROOT = Path(__file__).resolve().parents[3]
DERIVED_ROOT = REPO_ROOT / "data" / "derived" / "small_overlap" / "preprocessed_signals"
PARSER_VERSION = "signal-preprocessing:v2"
DEFAULT_HARMONIZED_START_S = 0.0
DEFAULT_HARMONIZED_END_S = 0.25
DEFAULT_HARMONIZED_SAMPLE_RATE_HZ = 10000.0
MODE_STANDARD = "standard_baseline"
MODE_STRICT = "strict_origin"
MODE_T0 = "exploratory_t0"
DEFAULT_MODES = (MODE_STANDARD, MODE_STRICT, MODE_T0)


@dataclass(frozen=True)
class TestContext:
    filegroup_id: int
    test_code: str
    vehicle_make_model: str
    tdms_asset_id: int
    tdms_path: Path


@dataclass(frozen=True)
class ChannelCatalog:
    standard_name: str
    channel_family: str
    cfc_class: int
    unit: str
    filtered_aliases: tuple[str, ...]
    raw_aliases: tuple[str, ...]
    group_preferences: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class ResolvedChannel:
    standard_name: str
    channel_family: str
    cfc_class: int
    unit: str
    source_group: str
    source_channel: str
    raw_reference_group: str | None
    raw_reference_channel: str | None
    notes: str = ""


CHANNEL_CATALOG: tuple[ChannelCatalog, ...] = (
    ChannelCatalog(
        standard_name="vehicle_longitudinal_accel_g",
        channel_family="vehicle_acceleration_array",
        cfc_class=60,
        unit="g",
        filtered_aliases=("10VEHC0000__ACXD", "10VEHC0000_ACXD"),
        raw_aliases=("10VEHC0000__ACX_", "10VEHC0000_ACX_"),
        group_preferences=("1vehicle", "vehicle", "filtereddata", "analysiscopyy", "analysis"),
        notes="IIHS explicit family: vehicle acceleration array CFC 60.",
    ),
    ChannelCatalog(
        standard_name="vehicle_lateral_accel_g",
        channel_family="vehicle_acceleration_array",
        cfc_class=60,
        unit="g",
        filtered_aliases=("10VEHC0000__ACYD", "10VEHC0000_ACYD"),
        raw_aliases=("10VEHC0000__ACY_", "10VEHC0000_ACY_"),
        group_preferences=("1vehicle", "vehicle", "filtereddata", "analysiscopyy", "analysis"),
        notes="IIHS explicit family: vehicle acceleration array CFC 60.",
    ),
    ChannelCatalog(
        standard_name="vehicle_vertical_accel_g",
        channel_family="vehicle_acceleration_array",
        cfc_class=60,
        unit="g",
        filtered_aliases=("10VEHC0000__ACZD", "10VEHC0000_ACZD"),
        raw_aliases=("10VEHC0000__ACZ_", "10VEHC0000_ACZ_"),
        group_preferences=("1vehicle", "vehicle", "filtereddata", "analysiscopyy", "analysis"),
        notes="IIHS explicit family: vehicle acceleration array CFC 60.",
    ),
    ChannelCatalog(
        standard_name="vehicle_resultant_accel_g",
        channel_family="vehicle_acceleration_array",
        cfc_class=60,
        unit="g",
        filtered_aliases=("10VEHC0000__ACRD", "10VEHC0000_ACRD"),
        raw_aliases=(),
        group_preferences=("1vehicle", "vehicle", "filtereddata", "analysiscopyy", "analysis"),
        notes="Resultant channel delivered by DIAdem in TDMS.",
    ),
    ChannelCatalog(
        standard_name="seat_mid_deflection_mm",
        channel_family="seat_back_deflection",
        cfc_class=60,
        unit="mm",
        filtered_aliases=("11SEATMI0000DSXD",),
        raw_aliases=("11SEATMI0000DSX0",),
        group_preferences=("1vehicle", "vehicle", "filtereddata"),
        notes="IIHS explicit family: seat back deflection CFC 60.",
    ),
    ChannelCatalog(
        standard_name="seat_inner_deflection_mm",
        channel_family="seat_back_deflection",
        cfc_class=60,
        unit="mm",
        filtered_aliases=("11SEATIN0000DSXD",),
        raw_aliases=("11SEATIN0000DSX0",),
        group_preferences=("1vehicle", "vehicle", "filtereddata"),
        notes="IIHS explicit family: seat back deflection CFC 60.",
    ),
    ChannelCatalog(
        standard_name="foot_left_x_accel_g",
        channel_family="foot_acceleration",
        cfc_class=180,
        unit="g",
        filtered_aliases=("11FOOTLE00__ACXC", "11FOOTLE00_ACXC"),
        raw_aliases=("11FOOTLE00__ACX_", "11FOOTLE00_ACX_"),
        group_preferences=("11leftleg", "leftleg"),
        notes="IIHS explicit family: foot acceleration CFC 180.",
    ),
    ChannelCatalog(
        standard_name="foot_left_z_accel_g",
        channel_family="foot_acceleration",
        cfc_class=180,
        unit="g",
        filtered_aliases=("11FOOTLE00__ACZC", "11FOOTLE00_ACZC"),
        raw_aliases=("11FOOTLE00__ACZ_", "11FOOTLE00_ACZ_"),
        group_preferences=("11leftleg", "leftleg"),
        notes="IIHS explicit family: foot acceleration CFC 180.",
    ),
    ChannelCatalog(
        standard_name="foot_right_x_accel_g",
        channel_family="foot_acceleration",
        cfc_class=180,
        unit="g",
        filtered_aliases=("11FOOTRI00__ACXC", "11FOOTRI00_ACXC"),
        raw_aliases=("11FOOTRI00__ACX_", "11FOOTRI00_ACX_"),
        group_preferences=("11rightleg", "rightleg"),
        notes="IIHS explicit family: foot acceleration CFC 180.",
    ),
    ChannelCatalog(
        standard_name="foot_right_z_accel_g",
        channel_family="foot_acceleration",
        cfc_class=180,
        unit="g",
        filtered_aliases=("11FOOTRI00__ACZC", "11FOOTRI00_ACZC"),
        raw_aliases=("11FOOTRI00__ACZ_", "11FOOTRI00_ACZ_"),
        group_preferences=("11rightleg", "rightleg"),
        notes="IIHS explicit family: foot acceleration CFC 180.",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create three-mode IIHS preprocessing outputs plus a fixed-window harmonized layer."
    )
    parser.add_argument("--filegroup-id", type=int, required=True)
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--register-db", action="store_true")
    parser.add_argument("--modes", default=",".join(DEFAULT_MODES))
    parser.add_argument("--harmonized-start-s", type=float, default=DEFAULT_HARMONIZED_START_S)
    parser.add_argument("--harmonized-end-s", type=float, default=DEFAULT_HARMONIZED_END_S)
    parser.add_argument("--harmonized-sample-rate-hz", type=float, default=DEFAULT_HARMONIZED_SAMPLE_RATE_HZ)
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def parse_modes(text: str) -> tuple[str, ...]:
    modes = tuple(chunk.strip() for chunk in text.split(",") if chunk.strip())
    invalid = sorted(set(modes) - set(DEFAULT_MODES))
    if invalid:
        raise ValueError(f"Unsupported mode(s): {', '.join(invalid)}")
    return modes or DEFAULT_MODES


def ensure_column_exists(connection: sqlite3.Connection, table_name: str, column_name: str, ddl: str) -> None:
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}
    if column_name not in existing:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")


def ensure_preprocessing_schema(connection: sqlite3.Connection) -> None:
    schema_path = REPO_ROOT / "sql" / "research_database.sql"
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    ensure_column_exists(connection, "preprocessing_neighbors", "multiview_score", "REAL")
    ensure_column_exists(connection, "preprocessing_neighbors", "pulse_view_score", "REAL")
    ensure_column_exists(connection, "preprocessing_neighbors", "occupant_view_score", "REAL")
    ensure_column_exists(connection, "preprocessing_neighbors", "lower_extremity_view_score", "REAL")
    ensure_column_exists(connection, "preprocessing_neighbors", "pulse_phase_score", "REAL")
    ensure_column_exists(connection, "preprocessing_neighbors", "occupant_phase_score", "REAL")
    ensure_column_exists(connection, "preprocessing_neighbors", "lower_extremity_phase_score", "REAL")
    ensure_column_exists(connection, "preprocessing_clusters", "robust_distance_score", "REAL")
    ensure_column_exists(connection, "preprocessing_clusters", "local_density_outlier_score", "REAL")
    ensure_column_exists(connection, "preprocessing_clusters", "stability_score", "REAL")
    ensure_column_exists(connection, "preprocessing_clusters", "coverage_score", "REAL")


def load_context(connection: sqlite3.Connection, filegroup_id: int) -> TestContext:
    row = connection.execute(
        """
        SELECT fg.filegroup_id,
               fg.test_code,
               v.vehicle_make_model,
               a.asset_id AS tdms_asset_id,
               a.local_path AS tdms_path
          FROM filegroups fg
          JOIN vehicles v
            ON v.vehicle_id = fg.vehicle_id
          JOIN signal_containers sc
            ON sc.filegroup_id = fg.filegroup_id
           AND sc.container_type = 'tdms'
           AND sc.extraction_status = 'done'
          JOIN assets a
            ON a.asset_id = sc.asset_id
         WHERE fg.filegroup_id = ?
         ORDER BY a.asset_id
         LIMIT 1
        """,
        (filegroup_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"TDMS done container not found for filegroup_id={filegroup_id}")
    return TestContext(
        filegroup_id=int(row["filegroup_id"]),
        test_code=row["test_code"],
        vehicle_make_model=row["vehicle_make_model"],
        tdms_asset_id=int(row["tdms_asset_id"]),
        tdms_path=Path(row["tdms_path"]),
    )


def find_raw_group(tdms: TdmsFile) -> str:
    candidates = [group.name for group in tdms.groups() if group.name.endswith("_Raw_Data")]
    if candidates:
        return sorted(candidates)[0]
    for group in tdms.groups():
        if "raw" in group.name.lower():
            return group.name
    raise ValueError("Raw TDMS group not found.")


def build_channel_index(tdms: TdmsFile) -> dict[str, list[tuple[str, str]]]:
    index: dict[str, list[tuple[str, str]]] = {}
    for group in tdms.groups():
        for channel in group.channels():
            index.setdefault(normalize_key(channel.name), []).append((group.name, channel.name))
    return index


def choose_filtered_candidate(
    candidates: list[tuple[str, str]],
    raw_group: str,
    group_preferences: tuple[str, ...],
) -> tuple[str, str] | None:
    if not candidates:
        return None
    raw_group_norm = normalize_key(raw_group)

    def rank(item: tuple[str, str]) -> tuple[int, int, int, str, str]:
        group_name, channel_name = item
        group_norm = normalize_key(group_name)
        raw_penalty = 1 if group_norm == raw_group_norm or "raw" in group_norm else 0
        pref_rank = len(group_preferences)
        for idx, preference in enumerate(group_preferences):
            if preference in group_norm:
                pref_rank = idx
                break
        return (raw_penalty, pref_rank, len(group_name), group_name, channel_name)

    return min(candidates, key=rank)


def resolve_raw_reference(
    channel_index: dict[str, list[tuple[str, str]]],
    raw_group: str,
    raw_aliases: tuple[str, ...],
) -> tuple[str | None, str | None]:
    if not raw_aliases:
        return None, None
    raw_group_norm = normalize_key(raw_group)
    raw_candidates: list[tuple[str, str]] = []
    for alias in raw_aliases:
        for candidate in channel_index.get(normalize_key(alias), []):
            if normalize_key(candidate[0]) == raw_group_norm:
                return candidate
            if "raw" in normalize_key(candidate[0]):
                raw_candidates.append(candidate)
    if raw_candidates:
        return sorted(raw_candidates)[0]
    return None, None


def resolve_channels(tdms: TdmsFile, raw_group: str) -> tuple[list[ResolvedChannel], list[dict[str, Any]]]:
    channel_index = build_channel_index(tdms)
    resolved: list[ResolvedChannel] = []
    missing: list[dict[str, Any]] = []
    for catalog in CHANNEL_CATALOG:
        candidates: list[tuple[str, str]] = []
        for alias in catalog.filtered_aliases:
            candidates.extend(channel_index.get(normalize_key(alias), []))
        selected = choose_filtered_candidate(candidates, raw_group, catalog.group_preferences)
        if selected is None:
            missing.append(
                {
                    "standard_name": catalog.standard_name,
                    "channel_family": catalog.channel_family,
                    "reason": "filtered_channel_not_found",
                    "aliases": list(catalog.filtered_aliases),
                }
            )
            continue
        raw_reference_group, raw_reference_channel = resolve_raw_reference(channel_index, raw_group, catalog.raw_aliases)
        resolved.append(
            ResolvedChannel(
                standard_name=catalog.standard_name,
                channel_family=catalog.channel_family,
                cfc_class=catalog.cfc_class,
                unit=catalog.unit,
                source_group=selected[0],
                source_channel=selected[1],
                raw_reference_group=raw_reference_group,
                raw_reference_channel=raw_reference_channel,
                notes=catalog.notes,
            )
        )
    return resolved, missing


def select_preferred_channel(resolved_channels: list[ResolvedChannel]) -> ResolvedChannel:
    for channel in resolved_channels:
        if channel.standard_name == "vehicle_longitudinal_accel_g":
            return channel
    return resolved_channels[0]


def resolve_time_basis(
    tdms: TdmsFile,
    raw_group: str,
    preferred_channel: ResolvedChannel,
) -> tuple[np.ndarray, dict[str, Any]]:
    explicit_time_axis = np.array([], dtype=float)
    explicit_source = f"{raw_group}/Time axis"
    raw_channels = {channel.name for channel in tdms[raw_group].channels()}
    if "Time axis" in raw_channels:
        explicit_time_axis = np.asarray(tdms[raw_group]["Time axis"][:], dtype=float)

    fallback = tdms[preferred_channel.source_group][preferred_channel.source_channel]
    try:
        time_track = np.asarray(fallback.time_track(), dtype=float)
    except Exception:
        time_track = np.array([], dtype=float)

    if time_track.size:
        note = ""
        if explicit_time_axis.size == time_track.size + 1 and np.allclose(explicit_time_axis[1:], time_track):
            note = "Explicit raw Time axis includes one leading boundary sample; channel time_track was selected."
        elif explicit_time_axis.size and explicit_time_axis.size != time_track.size:
            note = "Explicit raw Time axis sample count differs from waveform sample count; channel time_track was selected."
        return time_track, {
            "selected_source": f"{preferred_channel.source_group}/{preferred_channel.source_channel}.time_track()",
            "selected_sample_count": int(time_track.size),
            "explicit_time_axis_source": explicit_source,
            "explicit_time_axis_sample_count": int(explicit_time_axis.size),
            "note": note,
        }
    if explicit_time_axis.size:
        return explicit_time_axis, {
            "selected_source": explicit_source,
            "selected_sample_count": int(explicit_time_axis.size),
            "explicit_time_axis_source": explicit_source,
            "explicit_time_axis_sample_count": int(explicit_time_axis.size),
            "note": "Channel time_track was unavailable; explicit Time axis channel was used.",
        }
    raise ValueError("Unable to restore TDMS time axis.")


def read_channel(tdms: TdmsFile, group_name: str, channel_name: str) -> np.ndarray:
    return np.asarray(tdms[group_name][channel_name][:], dtype=float)


def preimpact_mask(time_s: np.ndarray) -> np.ndarray:
    return (time_s >= -0.05) & (time_s < -0.04)


def reference_index_for_zero(time_s: np.ndarray) -> int:
    non_negative = np.flatnonzero(time_s >= 0.0)
    if non_negative.size:
        return int(non_negative[0])
    return int(np.nanargmin(np.abs(time_s)))


def safe_extrema(values: np.ndarray) -> tuple[int | None, int | None]:
    finite_mask = np.isfinite(values)
    if not np.any(finite_mask):
        return None, None
    finite_idx = np.flatnonzero(finite_mask)
    finite_values = values[finite_mask]
    min_pos = int(finite_idx[int(np.argmin(finite_values))])
    max_pos = int(finite_idx[int(np.argmax(finite_values))])
    return min_pos, max_pos


def series_summary(time_s: np.ndarray, values: np.ndarray) -> dict[str, float | int | None]:
    min_idx, max_idx = safe_extrema(values)
    return {
        "sample_count": int(values.size),
        "non_null_count": int(np.isfinite(values).sum()),
        "time_start_s": None if time_s.size == 0 else float(time_s[0]),
        "time_end_s": None if time_s.size == 0 else float(time_s[-1]),
        "initial_value": None if values.size == 0 or not np.isfinite(values[0]) else float(values[0]),
        "min_value": None if min_idx is None else float(values[min_idx]),
        "min_time_s": None if min_idx is None else float(time_s[min_idx]),
        "max_value": None if max_idx is None else float(values[max_idx]),
        "max_time_s": None if max_idx is None else float(time_s[max_idx]),
    }


def compute_standard_baseline(
    time_s: np.ndarray,
    values: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    mask = preimpact_mask(time_s) & np.isfinite(values)
    if np.any(mask):
        baseline = float(np.nanmean(values[mask]))
        baseline_sample_count = int(mask.sum())
        baseline_method = "preimpact_mean_50_40ms"
    else:
        baseline = 0.0
        baseline_sample_count = 0
        baseline_method = "fallback_zero"
    corrected = values - baseline
    return corrected, {
        "baseline_method": baseline_method,
        "baseline_window_start_s": -0.05,
        "baseline_window_end_s": -0.04,
        "baseline_sample_count": baseline_sample_count,
        "baseline_value": baseline,
    }


def sliding_bias(values: np.ndarray, window_samples: int, first_fraction: float = 0.2) -> dict[str, Any]:
    search_end = max(window_samples, int(np.floor(values.size * first_fraction)))
    best_start = 0
    best_std = None
    best_mean = 0.0
    for start in range(0, max(search_end - window_samples + 1, 1)):
        window = values[start : start + window_samples]
        if not np.isfinite(window).any():
            continue
        std = float(np.nanstd(window))
        if best_std is None or std < best_std:
            best_std = std
            best_start = start
            best_mean = float(np.nanmean(window))
    if best_std is None:
        return {
            "window_start_index": 0,
            "window_end_index": max(window_samples - 1, 0),
            "window_std": None,
            "detected_bias": 0.0,
        }
    return {
        "window_start_index": best_start,
        "window_end_index": best_start + window_samples - 1,
        "window_std": best_std,
        "detected_bias": best_mean,
    }


def build_t0_proxy(time_s: np.ndarray, values: np.ndarray) -> tuple[pd.DataFrame, dict[str, Any]]:
    dt = float(np.nanmedian(np.diff(time_s)))
    window_samples = max(1, int(round(0.010 / dt)))
    bias_info = sliding_bias(values, window_samples=window_samples)
    detected_bias = float(bias_info["detected_bias"])
    applied_bias = 0.0 if abs(detected_bias) > 3.0 else detected_bias
    corrected = values - applied_bias

    anchor_idx = next((idx for idx, value in enumerate(corrected) if value < -5.0), None)
    release_idx = None
    algorithm_mode = "anchor_backtrack"
    if anchor_idx is not None:
        for idx in range(anchor_idx, -1, -1):
            if corrected[idx] > -0.5:
                release_idx = idx
                break
        t0_idx = 0 if release_idx is None else min(release_idx + 1, corrected.size - 1)
        if release_idx is None:
            algorithm_mode = "anchor_without_release"
    else:
        t0_idx = next((idx for idx, value in enumerate(corrected) if value < -0.5), 0)
        algorithm_mode = "fallback_release_only" if t0_idx != 0 else "fallback_zero"

    normalized = corrected.copy()
    normalized[:t0_idx] = 0.0
    normalized[t0_idx:] = normalized[t0_idx:] - normalized[t0_idx]
    shifted_time = time_s - time_s[t0_idx]

    proxy_frame = pd.DataFrame(
        {
            "shifted_time_s": shifted_time,
            "vehicle_longitudinal_accel_g_t0_proxy": normalized,
            "source_time_s": time_s,
            "source_vehicle_longitudinal_accel_g": values,
        }
    )
    metrics = {
        "source_channel_basis": "standard_baseline_vehicle_longitudinal_accel_g",
        "window_samples": window_samples,
        "detected_bias_g": detected_bias,
        "applied_bias_g": applied_bias,
        "anchor_idx": anchor_idx,
        "anchor_time_s": None if anchor_idx is None else float(time_s[anchor_idx]),
        "anchor_value_g": None if anchor_idx is None else float(corrected[anchor_idx]),
        "release_idx": release_idx,
        "release_time_s": None if release_idx is None else float(time_s[release_idx]),
        "release_value_g": None if release_idx is None else float(corrected[release_idx]),
        "t0_idx": int(t0_idx),
        "t0_time_s": float(time_s[t0_idx]),
        "t0_value_g_before_zeroing": float(corrected[t0_idx]),
        "algorithm_mode": algorithm_mode,
        "acceptance_checks": {
            "shifted_time_at_t0_is_zero": bool(abs(float(shifted_time[t0_idx])) < 1e-12),
            "accel_at_t0_is_zero": bool(abs(float(normalized[t0_idx])) < 1e-12),
            "pre_t0_all_zero": bool(np.allclose(normalized[:t0_idx], 0.0)),
        },
    }
    metrics.update(bias_info)
    return proxy_frame, metrics


def channel_meta_frame(context: TestContext, resolved_channels: list[ResolvedChannel], mode: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for channel in resolved_channels:
        rows.append(
            {
                "filegroup_id": context.filegroup_id,
                "test_code": context.test_code,
                "vehicle_make_model": context.vehicle_make_model,
                "mode": mode,
                "standard_name": channel.standard_name,
                "channel_family": channel.channel_family,
                "cfc_class": channel.cfc_class,
                "unit": channel.unit,
                "source_group": channel.source_group,
                "source_channel": channel.source_channel,
                "raw_reference_group": channel.raw_reference_group,
                "raw_reference_channel": channel.raw_reference_channel,
                "notes": channel.notes,
                "source_kind": "official_tdms_processed_channel",
            }
        )
    return pd.DataFrame(rows)


def build_long_frame(
    context: TestContext,
    mode: str,
    wide_frame: pd.DataFrame,
    resolved_channels: list[ResolvedChannel],
) -> pd.DataFrame:
    meta = channel_meta_frame(context, resolved_channels, mode)
    long_frame = wide_frame.melt(id_vars=["time_s"], var_name="standard_name", value_name="value")
    return long_frame.merge(meta, on="standard_name", how="left")


def interpolate_linear(time_s: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    valid = np.isfinite(time_s) & np.isfinite(values)
    if np.count_nonzero(valid) == 0:
        return np.full(grid.shape, np.nan, dtype=float)
    valid_time = time_s[valid]
    valid_values = values[valid]
    order = np.argsort(valid_time)
    valid_time = valid_time[order]
    valid_values = valid_values[order]
    unique_time, unique_indices = np.unique(valid_time, return_index=True)
    valid_values = valid_values[unique_indices]
    if unique_time.size == 1:
        out = np.full(grid.shape, np.nan, dtype=float)
        match = np.isclose(grid, unique_time[0], atol=1e-12)
        out[match] = valid_values[0]
        return out
    out = np.full(grid.shape, np.nan, dtype=float)
    coverage = (grid >= unique_time[0]) & (grid <= unique_time[-1])
    out[coverage] = np.interp(grid[coverage], unique_time, valid_values)
    return out


def build_harmonized_outputs(
    context: TestContext,
    mode: str,
    time_s: np.ndarray,
    values_by_name: dict[str, np.ndarray],
    resolved_channels: list[ResolvedChannel],
    start_s: float,
    end_s: float,
    sample_rate_hz: float,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    dt = 1.0 / sample_rate_hz
    grid = np.round(np.arange(start_s, end_s + (dt * 0.5), dt), 10)
    wide_rows: dict[str, np.ndarray] = {"time_s": grid}
    coverage: dict[str, Any] = {}

    for channel in resolved_channels:
        interpolated = interpolate_linear(time_s, values_by_name[channel.standard_name], grid)
        wide_rows[channel.standard_name] = interpolated
        coverage[channel.standard_name] = {
            "non_null_count": int(np.isfinite(interpolated).sum()),
            "coverage_ratio": float(np.isfinite(interpolated).sum() / interpolated.size) if interpolated.size else 0.0,
            "interpolation_method": "linear",
        }

    wide_frame = pd.DataFrame(wide_rows)
    long_frame = build_long_frame(context, mode, wide_frame, resolved_channels)
    long_frame["is_observed"] = long_frame["value"].notna()
    return wide_frame, long_frame, coverage


def build_mode_result(
    context: TestContext,
    mode: str,
    source_time_s: np.ndarray,
    source_values_by_name: dict[str, np.ndarray],
    resolved_channels: list[ResolvedChannel],
    reference_idx: int,
    reference_method: str,
    description: str,
    crop_before_reference: bool,
    harmonized_start_s: float,
    harmonized_end_s: float,
    harmonized_sample_rate_hz: float,
    extra_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reference_time_s = float(source_time_s[reference_idx])
    if crop_before_reference:
        mode_time_s = source_time_s[reference_idx:] - reference_time_s
        mode_values_by_name = {
            name: values[reference_idx:] - values[reference_idx]
            for name, values in source_values_by_name.items()
        }
    else:
        mode_time_s = source_time_s.copy()
        mode_values_by_name = {name: values.copy() for name, values in source_values_by_name.items()}

    wide_rows: dict[str, np.ndarray] = {"time_s": mode_time_s}
    for channel in resolved_channels:
        wide_rows[channel.standard_name] = mode_values_by_name[channel.standard_name]
    wide_frame = pd.DataFrame(wide_rows)
    long_frame = build_long_frame(context, mode, wide_frame, resolved_channels)

    harmonized_wide, harmonized_long, harmonized_coverage = build_harmonized_outputs(
        context=context,
        mode=mode,
        time_s=mode_time_s,
        values_by_name=mode_values_by_name,
        resolved_channels=resolved_channels,
        start_s=harmonized_start_s,
        end_s=harmonized_end_s,
        sample_rate_hz=harmonized_sample_rate_hz,
    )

    series_rows: list[dict[str, Any]] = []
    for channel in resolved_channels:
        native_values = mode_values_by_name[channel.standard_name]
        harmonized_values = harmonized_wide[channel.standard_name].to_numpy()
        series_rows.append(
            {
                "standard_name": channel.standard_name,
                "channel_family": channel.channel_family,
                "unit": channel.unit,
                "cfc_class": channel.cfc_class,
                "source_group": channel.source_group,
                "source_channel": channel.source_channel,
                "raw_reference_group": channel.raw_reference_group,
                "raw_reference_channel": channel.raw_reference_channel,
                "native_sample_count": int(native_values.size),
                "harmonized_non_null_count": int(np.isfinite(harmonized_values).sum()),
                "stats": {
                    "native": series_summary(mode_time_s, native_values),
                    "harmonized": series_summary(harmonized_wide["time_s"].to_numpy(), harmonized_values),
                    "harmonized_coverage": harmonized_coverage[channel.standard_name],
                },
            }
        )

    return {
        "status": "done",
        "description": description,
        "reference_method": reference_method,
        "reference_index": int(reference_idx),
        "reference_time_s": reference_time_s,
        "crop_before_reference": crop_before_reference,
        "native_sample_count": int(mode_time_s.size),
        "native_time_start_s": None if mode_time_s.size == 0 else float(mode_time_s[0]),
        "native_time_end_s": None if mode_time_s.size == 0 else float(mode_time_s[-1]),
        "harmonized_sample_count": int(harmonized_wide.shape[0]),
        "harmonized_time_start_s": None if harmonized_wide.empty else float(harmonized_wide["time_s"].iat[0]),
        "harmonized_time_end_s": None if harmonized_wide.empty else float(harmonized_wide["time_s"].iat[-1]),
        "wide_frame": wide_frame,
        "long_frame": long_frame,
        "harmonized_wide_frame": harmonized_wide,
        "harmonized_long_frame": harmonized_long,
        "series": series_rows,
        "metrics": extra_metrics or {},
    }


def output_paths(output_root: Path, context: TestContext, modes: tuple[str, ...]) -> dict[str, Any]:
    target_root = output_root / f"{context.filegroup_id}-{context.test_code}"
    mode_paths: dict[str, dict[str, Path]] = {}
    for mode in modes:
        mode_root = target_root / "modes" / mode
        mode_paths[mode] = {
            "root": mode_root,
            "wide": mode_root / "wide.parquet",
            "long": mode_root / "long.parquet",
            "harmonized_wide": mode_root / "harmonized_wide.parquet",
            "harmonized_long": mode_root / "harmonized_long.parquet",
        }
    return {
        "root": target_root,
        "manifest": target_root / "preprocessing_manifest.json",
        "legacy_standard_wide": target_root / "official_known_families_wide.parquet",
        "legacy_standard_long": target_root / "official_known_families_long.parquet",
        "legacy_t0_proxy": target_root / "exploratory_vehicle_longitudinal_t0_proxy.parquet",
        "modes": mode_paths,
    }


def sanitize_manifest_mode(mode_result: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    sanitized = {
        key: value
        for key, value in mode_result.items()
        if key
        not in {
            "wide_frame",
            "long_frame",
            "harmonized_wide_frame",
            "harmonized_long_frame",
        }
    }
    sanitized["outputs"] = {
        "wide": repo_relative(paths["wide"]),
        "long": repo_relative(paths["long"]),
        "harmonized_wide": repo_relative(paths["harmonized_wide"]),
        "harmonized_long": repo_relative(paths["harmonized_long"]),
    }
    return sanitized


def write_outputs(
    paths: dict[str, Any],
    mode_results: dict[str, dict[str, Any]],
    t0_proxy_frame: pd.DataFrame | None,
) -> None:
    paths["root"].mkdir(parents=True, exist_ok=True)
    for mode, result in mode_results.items():
        if result["status"] != "done":
            continue
        mode_path = paths["modes"][mode]
        mode_path["root"].mkdir(parents=True, exist_ok=True)
        result["wide_frame"].to_parquet(mode_path["wide"], engine="pyarrow", index=False)
        result["long_frame"].to_parquet(mode_path["long"], engine="pyarrow", index=False)
        result["harmonized_wide_frame"].to_parquet(mode_path["harmonized_wide"], engine="pyarrow", index=False)
        result["harmonized_long_frame"].to_parquet(mode_path["harmonized_long"], engine="pyarrow", index=False)

    if MODE_STANDARD in mode_results and mode_results[MODE_STANDARD]["status"] == "done":
        mode_results[MODE_STANDARD]["wide_frame"].to_parquet(paths["legacy_standard_wide"], engine="pyarrow", index=False)
        mode_results[MODE_STANDARD]["long_frame"].to_parquet(paths["legacy_standard_long"], engine="pyarrow", index=False)
    if t0_proxy_frame is not None:
        t0_proxy_frame.to_parquet(paths["legacy_t0_proxy"], engine="pyarrow", index=False)


def build_manifest(
    context: TestContext,
    raw_group: str,
    time_s: np.ndarray,
    time_basis: dict[str, Any],
    resolved_channels: list[ResolvedChannel],
    missing_channels: list[dict[str, Any]],
    diagnostics: list[dict[str, Any]],
    mode_results: dict[str, dict[str, Any]],
    paths: dict[str, Any],
    harmonized_start_s: float,
    harmonized_end_s: float,
    harmonized_sample_rate_hz: float,
    t0_proxy_metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    modes_manifest: dict[str, Any] = {}
    for mode, result in mode_results.items():
        if result["status"] == "done":
            modes_manifest[mode] = sanitize_manifest_mode(result, paths["modes"][mode])
        else:
            modes_manifest[mode] = result

    mode_outputs: dict[str, dict[str, str]] = {}
    for mode, mode_paths in paths["modes"].items():
        if mode_results[mode]["status"] != "done":
            continue
        mode_outputs[mode] = {
            key: repo_relative(path)
            for key, path in mode_paths.items()
            if key != "root"
        }

    outputs = {
        "manifest": repo_relative(paths["manifest"]),
        "legacy_standard_wide": repo_relative(paths["legacy_standard_wide"]),
        "legacy_standard_long": repo_relative(paths["legacy_standard_long"]),
        "modes": mode_outputs,
    }
    if t0_proxy_metrics is not None:
        outputs["legacy_t0_proxy"] = repo_relative(paths["legacy_t0_proxy"])

    return {
        "generated_at": utc_now_iso(),
        "parser_version": PARSER_VERSION,
        "filegroup_id": context.filegroup_id,
        "test_code": context.test_code,
        "vehicle_make_model": context.vehicle_make_model,
        "tdms_asset_id": context.tdms_asset_id,
        "tdms_path": str(context.tdms_path),
        "raw_group": raw_group,
        "time_basis": {
            **time_basis,
            "sample_count": int(time_s.size),
            "sample_rate_hz": float(round(1.0 / np.nanmedian(np.diff(time_s)), 6)),
            "start_time_s": float(time_s[0]),
            "end_time_s": float(time_s[-1]),
            "policy": "Preserve native TDMS time axis in the canonical standard_baseline mode.",
        },
        "official_policy": {
            "source_precedence": [
                "DTS metadata",
                "TDMS signal payload",
                "TDM/TDX via DIAdem export",
                "CSV sidecar",
                "legacy BIN/PI/CHN/TLF family",
            ],
            "applied_rule_scope": [
                "vehicle acceleration array -> CFC 60",
                "seat back deflection -> CFC 60",
                "foot acceleration -> CFC 180",
            ],
            "mode_policy": {
                MODE_STANDARD: "Subtract IIHS pre-impact baseline over -50 to -40 ms and preserve native TDMS time axis.",
                MODE_STRICT: "Crop at official time zero and force each channel to start at (0, 0).",
                MODE_T0: "Detect T0 from vehicle longitudinal acceleration, crop at T0, and force each channel to start at (0, 0).",
            },
            "non_goals": [
                "No in-place modification of raw TDMS signals.",
                "No spline upsampling in the harmonized layer.",
                "No inferred CFC assignment for channels outside the documented IIHS families.",
            ],
        },
        "harmonized_policy": {
            "window_start_s": harmonized_start_s,
            "window_end_s": harmonized_end_s,
            "sample_rate_hz": harmonized_sample_rate_hz,
            "sample_count": int(round((harmonized_end_s - harmonized_start_s) * harmonized_sample_rate_hz)) + 1,
            "interpolation_method": "linear",
            "out_of_range_policy": "NaN padding",
        },
        "resolved_channels": [asdict(channel) for channel in resolved_channels],
        "missing_channels": missing_channels,
        "diagnostics": diagnostics,
        "modes": modes_manifest,
        "t0_proxy_assessment": {
            "status": "done" if t0_proxy_metrics else "unavailable",
            "summary": (
                "The prior-project T0 logic is implemented as the exploratory_t0 mode and as a longitudinal proxy artifact."
                if t0_proxy_metrics
                else "Vehicle longitudinal acceleration was unavailable, so T0 mode was not generated."
            ),
            "metrics": t0_proxy_metrics,
        },
        "outputs": outputs,
    }


def native_channel_diagnostics(
    time_s: np.ndarray,
    source_values_by_name: dict[str, np.ndarray],
    baseline_values_by_name: dict[str, np.ndarray],
    baseline_metrics_by_name: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for standard_name, source_values in source_values_by_name.items():
        diagnostics.append(
            {
                "standard_name": standard_name,
                "source_summary": series_summary(time_s, source_values),
                "standard_baseline_summary": series_summary(time_s, baseline_values_by_name[standard_name]),
                "baseline_metrics": baseline_metrics_by_name[standard_name],
            }
        )
    return diagnostics


def process_filegroup(
    connection: sqlite3.Connection,
    filegroup_id: int,
    output_root: Path,
    modes: tuple[str, ...] = DEFAULT_MODES,
    harmonized_start_s: float = DEFAULT_HARMONIZED_START_S,
    harmonized_end_s: float = DEFAULT_HARMONIZED_END_S,
    harmonized_sample_rate_hz: float = DEFAULT_HARMONIZED_SAMPLE_RATE_HZ,
    register_db: bool = False,
    preprocessing_run_id: int | None = None,
) -> dict[str, Any]:
    context = load_context(connection, filegroup_id)
    if not context.tdms_path.exists():
        raise FileNotFoundError(context.tdms_path)

    with TdmsFile.open(context.tdms_path) as tdms:
        raw_group = find_raw_group(tdms)
        resolved_channels, missing_channels = resolve_channels(tdms, raw_group)
        if not resolved_channels:
            raise ValueError(f"No supported channels resolved for filegroup_id={filegroup_id}")
        preferred_channel = select_preferred_channel(resolved_channels)
        time_s, time_basis = resolve_time_basis(tdms, raw_group, preferred_channel)

        source_values_by_name: dict[str, np.ndarray] = {}
        aligned_channels: list[ResolvedChannel] = []
        compatibility_issues: list[dict[str, Any]] = []
        for channel in resolved_channels:
            values = read_channel(tdms, channel.source_group, channel.source_channel)
            if values.size != time_s.size:
                compatibility_issues.append(
                    {
                        "standard_name": channel.standard_name,
                        "reason": "sample_count_mismatch",
                        "channel_sample_count": int(values.size),
                        "time_sample_count": int(time_s.size),
                    }
                )
                continue
            aligned_channels.append(channel)
            source_values_by_name[channel.standard_name] = values
        resolved_channels = aligned_channels
        missing_channels.extend(compatibility_issues)
        if not resolved_channels:
            raise ValueError(f"No aligned supported channels available for filegroup_id={filegroup_id}")

    baseline_values_by_name: dict[str, np.ndarray] = {}
    baseline_metrics_by_name: dict[str, dict[str, Any]] = {}
    for channel in resolved_channels:
        corrected, baseline_metrics = compute_standard_baseline(time_s, source_values_by_name[channel.standard_name])
        baseline_values_by_name[channel.standard_name] = corrected
        baseline_metrics_by_name[channel.standard_name] = baseline_metrics

    diagnostics = native_channel_diagnostics(time_s, source_values_by_name, baseline_values_by_name, baseline_metrics_by_name)
    official_zero_idx = reference_index_for_zero(time_s)

    t0_proxy_frame: pd.DataFrame | None = None
    t0_proxy_metrics: dict[str, Any] | None = None
    if "vehicle_longitudinal_accel_g" in baseline_values_by_name and np.isfinite(
        baseline_values_by_name["vehicle_longitudinal_accel_g"]
    ).sum() >= 2:
        t0_proxy_frame, t0_proxy_metrics = build_t0_proxy(time_s, baseline_values_by_name["vehicle_longitudinal_accel_g"])

    mode_results: dict[str, dict[str, Any]] = {}
    if MODE_STANDARD in modes:
        mode_results[MODE_STANDARD] = build_mode_result(
            context=context,
            mode=MODE_STANDARD,
            source_time_s=time_s,
            source_values_by_name=baseline_values_by_name,
            resolved_channels=resolved_channels,
            reference_idx=official_zero_idx,
            reference_method="official_native_zero_preserved",
            description="Canonical mode. Applies IIHS -50 to -40 ms baseline subtraction and preserves native TDMS time.",
            crop_before_reference=False,
            harmonized_start_s=harmonized_start_s,
            harmonized_end_s=harmonized_end_s,
            harmonized_sample_rate_hz=harmonized_sample_rate_hz,
            extra_metrics={
                "reference_kind": "official_native_zero",
                "baseline_metrics_by_channel": baseline_metrics_by_name,
            },
        )

    if MODE_STRICT in modes:
        mode_results[MODE_STRICT] = build_mode_result(
            context=context,
            mode=MODE_STRICT,
            source_time_s=time_s,
            source_values_by_name=baseline_values_by_name,
            resolved_channels=resolved_channels,
            reference_idx=official_zero_idx,
            reference_method="official_zero_crop_anchor",
            description="Crops at official zero and anchors each channel value at the reference sample.",
            crop_before_reference=True,
            harmonized_start_s=harmonized_start_s,
            harmonized_end_s=harmonized_end_s,
            harmonized_sample_rate_hz=harmonized_sample_rate_hz,
            extra_metrics={
                "reference_kind": "official_native_zero",
                "baseline_metrics_by_channel": baseline_metrics_by_name,
            },
        )

    if MODE_T0 in modes:
        if t0_proxy_metrics is None:
            mode_results[MODE_T0] = {
                "status": "unavailable",
                "description": "Vehicle longitudinal acceleration was unavailable.",
                "reference_method": "t0_not_available",
                "metrics": {},
                "series": [],
            }
        else:
            mode_results[MODE_T0] = build_mode_result(
                context=context,
                mode=MODE_T0,
                source_time_s=time_s,
                source_values_by_name=baseline_values_by_name,
                resolved_channels=resolved_channels,
                reference_idx=int(t0_proxy_metrics["t0_idx"]),
                reference_method="vehicle_longitudinal_anchor_backtrack_t0",
                description="Detects T0 from vehicle longitudinal acceleration and crops at T0.",
                crop_before_reference=True,
                harmonized_start_s=harmonized_start_s,
                harmonized_end_s=harmonized_end_s,
                harmonized_sample_rate_hz=harmonized_sample_rate_hz,
                extra_metrics=t0_proxy_metrics,
            )

    paths = output_paths(output_root, context, modes)
    write_outputs(paths, mode_results, t0_proxy_frame)
    manifest = build_manifest(
        context=context,
        raw_group=raw_group,
        time_s=time_s,
        time_basis=time_basis,
        resolved_channels=resolved_channels,
        missing_channels=missing_channels,
        diagnostics=diagnostics,
        mode_results=mode_results,
        paths=paths,
        harmonized_start_s=harmonized_start_s,
        harmonized_end_s=harmonized_end_s,
        harmonized_sample_rate_hz=harmonized_sample_rate_hz,
        t0_proxy_metrics=t0_proxy_metrics,
    )
    paths["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if register_db:
        register_preprocessing_manifest(connection, manifest, preprocessing_run_id=preprocessing_run_id)

    return manifest


def register_preprocessing_manifest(
    connection: sqlite3.Connection,
    manifest: dict[str, Any],
    preprocessing_run_id: int | None = None,
) -> None:
    ensure_preprocessing_schema(connection)
    now = utc_now_iso()
    filegroup_id = int(manifest["filegroup_id"])
    tdms_asset_id = manifest.get("tdms_asset_id")
    case_root = str(Path(manifest["outputs"]["manifest"]).parent).replace("\\", "/")

    for mode, mode_info in manifest["modes"].items():
        existing = connection.execute(
            """
            SELECT preprocessing_case_id, created_at
              FROM preprocessing_cases
             WHERE filegroup_id = ? AND mode = ?
            """,
            (filegroup_id, mode),
        ).fetchone()
        created_at = existing["created_at"] if existing is not None else now
        metrics_json = json.dumps(mode_info.get("metrics"), ensure_ascii=False)
        outputs = mode_info.get("outputs", {})

        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO preprocessing_cases (
                  preprocessing_run_id, filegroup_id, tdms_asset_id, mode, status, parser_version, case_root,
                  manifest_path, wide_path, long_path, harmonized_wide_path, harmonized_long_path,
                  reference_method, reference_time_s, reference_index,
                  native_time_start_s, native_time_end_s, native_sample_rate_hz, native_sample_count,
                  harmonized_time_start_s, harmonized_time_end_s, harmonized_sample_rate_hz, harmonized_sample_count,
                  metrics_json, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    preprocessing_run_id,
                    filegroup_id,
                    tdms_asset_id,
                    mode,
                    mode_info["status"],
                    manifest["parser_version"],
                    case_root,
                    manifest["outputs"]["manifest"],
                    outputs.get("wide"),
                    outputs.get("long"),
                    outputs.get("harmonized_wide"),
                    outputs.get("harmonized_long"),
                    mode_info.get("reference_method"),
                    mode_info.get("reference_time_s"),
                    mode_info.get("reference_index"),
                    mode_info.get("native_time_start_s"),
                    mode_info.get("native_time_end_s"),
                    manifest["time_basis"].get("sample_rate_hz"),
                    mode_info.get("native_sample_count"),
                    mode_info.get("harmonized_time_start_s"),
                    mode_info.get("harmonized_time_end_s"),
                    manifest["harmonized_policy"].get("sample_rate_hz"),
                    mode_info.get("harmonized_sample_count"),
                    metrics_json,
                    None,
                    created_at,
                    now,
                ),
            )
            preprocessing_case_id = int(cursor.lastrowid)
        else:
            preprocessing_case_id = int(existing["preprocessing_case_id"])
            connection.execute(
                """
                UPDATE preprocessing_cases
                   SET preprocessing_run_id = ?,
                       tdms_asset_id = ?,
                       status = ?,
                       parser_version = ?,
                       case_root = ?,
                       manifest_path = ?,
                       wide_path = ?,
                       long_path = ?,
                       harmonized_wide_path = ?,
                       harmonized_long_path = ?,
                       reference_method = ?,
                       reference_time_s = ?,
                       reference_index = ?,
                       native_time_start_s = ?,
                       native_time_end_s = ?,
                       native_sample_rate_hz = ?,
                       native_sample_count = ?,
                       harmonized_time_start_s = ?,
                       harmonized_time_end_s = ?,
                       harmonized_sample_rate_hz = ?,
                       harmonized_sample_count = ?,
                       metrics_json = ?,
                       notes = ?,
                       updated_at = ?
                 WHERE preprocessing_case_id = ?
                """,
                (
                    preprocessing_run_id,
                    tdms_asset_id,
                    mode_info["status"],
                    manifest["parser_version"],
                    case_root,
                    manifest["outputs"]["manifest"],
                    outputs.get("wide"),
                    outputs.get("long"),
                    outputs.get("harmonized_wide"),
                    outputs.get("harmonized_long"),
                    mode_info.get("reference_method"),
                    mode_info.get("reference_time_s"),
                    mode_info.get("reference_index"),
                    mode_info.get("native_time_start_s"),
                    mode_info.get("native_time_end_s"),
                    manifest["time_basis"].get("sample_rate_hz"),
                    mode_info.get("native_sample_count"),
                    mode_info.get("harmonized_time_start_s"),
                    mode_info.get("harmonized_time_end_s"),
                    manifest["harmonized_policy"].get("sample_rate_hz"),
                    mode_info.get("harmonized_sample_count"),
                    metrics_json,
                    None,
                    now,
                    preprocessing_case_id,
                ),
            )
            connection.execute("DELETE FROM preprocessing_series WHERE preprocessing_case_id = ?", (preprocessing_case_id,))

        for series in mode_info.get("series", []):
            connection.execute(
                """
                INSERT INTO preprocessing_series (
                  preprocessing_case_id, standard_name, channel_family, unit, cfc_class,
                  source_group, source_channel, raw_reference_group, raw_reference_channel,
                  native_sample_count, harmonized_non_null_count, stats_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    preprocessing_case_id,
                    series["standard_name"],
                    series.get("channel_family"),
                    series.get("unit"),
                    series.get("cfc_class"),
                    series.get("source_group"),
                    series.get("source_channel"),
                    series.get("raw_reference_group"),
                    series.get("raw_reference_channel"),
                    series.get("native_sample_count"),
                    series.get("harmonized_non_null_count"),
                    json.dumps(series.get("stats"), ensure_ascii=False),
                ),
            )

    connection.commit()


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_root = resolve_repo_path(args.output_root) if args.output_root else DERIVED_ROOT
    modes = parse_modes(args.modes)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        manifest = process_filegroup(
            connection=connection,
            filegroup_id=args.filegroup_id,
            output_root=output_root,
            modes=modes,
            harmonized_start_s=args.harmonized_start_s,
            harmonized_end_s=args.harmonized_end_s,
            harmonized_sample_rate_hz=args.harmonized_sample_rate_hz,
            register_db=args.register_db,
        )
        print(json.dumps(manifest["outputs"], ensure_ascii=False, indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
