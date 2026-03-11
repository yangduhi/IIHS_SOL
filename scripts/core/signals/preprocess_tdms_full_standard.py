from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.core.signals.preprocess_known_signal_families import (
    DEFAULT_HARMONIZED_END_S,
    DEFAULT_HARMONIZED_SAMPLE_RATE_HZ,
    DEFAULT_HARMONIZED_START_S,
    compute_standard_baseline,
    ensure_preprocessing_schema,
    interpolate_linear,
    preimpact_mask,
    register_preprocessing_manifest,
    repo_relative,
    resolve_repo_path,
    series_summary,
    utc_now_iso,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
DERIVED_ROOT = REPO_ROOT / "data" / "derived" / "small_overlap" / "preprocessed_signals_full_tdms"
PARSER_VERSION = "signal-preprocessing-full-tdms:v1"
MODE = "standard_baseline_full_tdms"


@dataclass(frozen=True)
class FullTdmsJob:
    signal_container_id: int
    filegroup_id: int
    test_code: str
    vehicle_make_model: str
    tdms_asset_id: int
    parquet_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a full-channel TDMS standard preprocessing layer for one filegroup."
    )
    parser.add_argument("--filegroup-id", type=int, required=True)
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--register-db", action="store_true")
    parser.add_argument("--harmonized-start-s", type=float, default=DEFAULT_HARMONIZED_START_S)
    parser.add_argument("--harmonized-end-s", type=float, default=DEFAULT_HARMONIZED_END_S)
    parser.add_argument("--harmonized-sample-rate-hz", type=float, default=DEFAULT_HARMONIZED_SAMPLE_RATE_HZ)
    return parser.parse_args()


def parse_tdms_raw_name(raw_name: str | None) -> tuple[str | None, str | None]:
    if not raw_name:
        return None, None
    match = re.match(r"/'(?P<group>.+)'/'(?P<channel>.+)'", raw_name)
    if not match:
        return None, raw_name
    return match.group("group"), match.group("channel")


def load_job(connection: sqlite3.Connection, filegroup_id: int) -> FullTdmsJob:
    row = connection.execute(
        """
        SELECT sc.signal_container_id,
               fg.filegroup_id,
               fg.test_code,
               v.vehicle_make_model,
               a.asset_id AS tdms_asset_id,
               ss.parquet_path
          FROM signal_containers sc
          JOIN filegroups fg
            ON fg.filegroup_id = sc.filegroup_id
          JOIN vehicles v
            ON v.vehicle_id = fg.vehicle_id
          JOIN assets a
            ON a.asset_id = sc.asset_id
          JOIN signal_series ss
            ON ss.signal_container_id = sc.signal_container_id
         WHERE sc.container_type = 'tdms'
           AND sc.extraction_status = 'done'
           AND fg.filegroup_id = ?
           AND ss.parquet_path IS NOT NULL
         ORDER BY ss.signal_series_id
         LIMIT 1
        """,
        (filegroup_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"TDMS parquet not found for filegroup_id={filegroup_id}")
    parquet_path = Path(row["parquet_path"])
    parquet_path = parquet_path if parquet_path.is_absolute() else REPO_ROOT / parquet_path
    return FullTdmsJob(
        signal_container_id=int(row["signal_container_id"]),
        filegroup_id=int(row["filegroup_id"]),
        test_code=row["test_code"],
        vehicle_make_model=row["vehicle_make_model"],
        tdms_asset_id=int(row["tdms_asset_id"]),
        parquet_path=parquet_path,
    )


def load_series_meta(connection: sqlite3.Connection, signal_container_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT series_key, series_name, unit, stats_json
          FROM signal_series
         WHERE signal_container_id = ?
         ORDER BY signal_series_id
        """,
        (signal_container_id,),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        stats = json.loads(row["stats_json"]) if row["stats_json"] else {}
        source_group, source_channel = parse_tdms_raw_name(stats.get("raw_name"))
        result.append(
            {
                "series_key": row["series_key"],
                "series_name": row["series_name"] or row["series_key"],
                "unit": row["unit"],
                "stats": stats,
                "source_group": source_group or stats.get("group_name"),
                "source_channel": source_channel or row["series_name"] or row["series_key"],
            }
        )
    return result


def choose_time_column(meta_rows: list[dict[str, Any]]) -> str:
    ranked: list[tuple[int, str]] = []
    for row in meta_rows:
        key = row["series_key"]
        key_lower = key.lower()
        series_name = (row["series_name"] or "").lower()
        source_group = (row.get("source_group") or "").lower()
        unit = (row.get("unit") or "").lower()
        if key_lower.endswith("_raw_data_time_axis"):
            ranked.append((0, key))
        elif "_raw_data_time_axis_" in key_lower:
            ranked.append((1, key))
        elif series_name == "time axis" and "raw" in source_group:
            ranked.append((2, key))
        elif series_name.startswith("time axis") and "raw" in source_group:
            ranked.append((3, key))
        elif series_name == "time axis":
            ranked.append((4, key))
        elif series_name.startswith("time axis"):
            ranked.append((5, key))
        elif unit == "s" and "time" in key_lower and "raw" in source_group:
            ranked.append((6, key))
        elif unit == "s" and "time" in key_lower:
            ranked.append((7, key))
    if not ranked:
        raise ValueError("Primary TDMS time axis column not found.")
    ranked.sort()
    return ranked[0][1]


def is_time_like(row: dict[str, Any]) -> bool:
    key = row["series_key"].lower()
    series_name = (row["series_name"] or "").lower()
    unit = (row.get("unit") or "").lower()
    return series_name == "time axis" or (unit == "s" and "time" in key)


def is_reference_like(row: dict[str, Any]) -> bool:
    source_group = (row.get("source_group") or "").lower()
    key = row["series_key"].lower()
    if "corridor" in source_group or "corridor" in key:
        return True
    if source_group == "analysis" or key.startswith("analysis_"):
        return True
    markers = ("acceptable", "good", "marginal", "poor", "upper_bound", "lower_bound", "bound")
    return any(marker in key for marker in markers)


def reference_index_for_zero(time_s: np.ndarray) -> int:
    non_negative = np.flatnonzero(time_s >= 0.0)
    if non_negative.size:
        return int(non_negative[0])
    return int(np.nanargmin(np.abs(time_s)))


def build_harmonized_wide(
    time_s: np.ndarray,
    values_by_name: dict[str, np.ndarray],
    start_s: float,
    end_s: float,
    sample_rate_hz: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    dt = 1.0 / sample_rate_hz
    grid = np.round(np.arange(start_s, end_s + (dt * 0.5), dt), 10)
    data: dict[str, np.ndarray] = {"time_s": grid}
    coverage: dict[str, Any] = {}
    for key, values in values_by_name.items():
        interpolated = interpolate_linear(time_s, values, grid)
        data[key] = interpolated
        coverage[key] = {
            "non_null_count": int(np.isfinite(interpolated).sum()),
            "coverage_ratio": float(np.isfinite(interpolated).sum() / interpolated.size) if interpolated.size else 0.0,
            "interpolation_method": "linear",
        }
    return pd.DataFrame(data), coverage


def output_paths(output_root: Path, job: FullTdmsJob) -> dict[str, Path]:
    case_root = output_root / f"{job.filegroup_id}-{job.test_code}"
    mode_root = case_root / "modes" / MODE
    return {
        "root": case_root,
        "mode_root": mode_root,
        "manifest": case_root / "preprocessing_manifest.json",
        "wide": mode_root / "wide.parquet",
        "harmonized_wide": mode_root / "harmonized_wide.parquet",
    }


def process_filegroup(
    connection: sqlite3.Connection,
    filegroup_id: int,
    output_root: Path,
    harmonized_start_s: float = DEFAULT_HARMONIZED_START_S,
    harmonized_end_s: float = DEFAULT_HARMONIZED_END_S,
    harmonized_sample_rate_hz: float = DEFAULT_HARMONIZED_SAMPLE_RATE_HZ,
    register_db: bool = False,
    preprocessing_run_id: int | None = None,
) -> dict[str, Any]:
    job = load_job(connection, filegroup_id)
    meta_rows = load_series_meta(connection, job.signal_container_id)
    time_column = choose_time_column(meta_rows)
    dataframe = pd.read_parquet(job.parquet_path)
    if time_column not in dataframe.columns:
        raise ValueError(f"Time axis column missing from parquet: {time_column}")

    time_s = pd.to_numeric(dataframe[time_column], errors="coerce").to_numpy(dtype=float)
    reference_idx = reference_index_for_zero(time_s)
    values_by_name: dict[str, np.ndarray] = {}
    series_rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []

    for row in meta_rows:
        key = row["series_key"]
        if key == time_column:
            exclusions.append({"series_key": key, "reason": "primary_time_axis"})
            continue
        if key not in dataframe.columns:
            exclusions.append({"series_key": key, "reason": "column_missing_in_parquet"})
            continue
        series = dataframe[key]
        if not pd.api.types.is_numeric_dtype(series):
            exclusions.append({"series_key": key, "reason": "non_numeric"})
            continue
        if is_time_like(row):
            exclusions.append({"series_key": key, "reason": "auxiliary_time_axis"})
            continue

        numeric_values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
        if is_reference_like(row):
            standardized = numeric_values.copy()
            policy = {
                "preprocess_policy": "pass_through_reference",
                "baseline_method": None,
                "baseline_value": None,
                "baseline_sample_count": 0,
            }
        else:
            standardized, baseline_metrics = compute_standard_baseline(time_s, numeric_values)
            policy = {
                "preprocess_policy": "baseline_subtract",
                **baseline_metrics,
            }

        values_by_name[key] = standardized
        series_rows.append(
            {
                "standard_name": key,
                "channel_family": row.get("source_group"),
                "unit": row.get("unit"),
                "cfc_class": None,
                "source_group": row.get("source_group"),
                "source_channel": row.get("source_channel"),
                "raw_reference_group": None,
                "raw_reference_channel": None,
                "native_sample_count": int(standardized.size),
                "harmonized_non_null_count": None,
                "stats": {
                    "native": series_summary(time_s, standardized),
                    "policy": policy,
                },
            }
        )

    if not values_by_name:
        raise ValueError(f"No standardizable TDMS series found for filegroup_id={filegroup_id}")

    wide_frame = pd.DataFrame({"time_s": time_s, **values_by_name})
    harmonized_wide, coverage = build_harmonized_wide(
        time_s=time_s,
        values_by_name=values_by_name,
        start_s=harmonized_start_s,
        end_s=harmonized_end_s,
        sample_rate_hz=harmonized_sample_rate_hz,
    )
    for row in series_rows:
        key = row["standard_name"]
        row["harmonized_non_null_count"] = coverage[key]["non_null_count"]
        row["stats"]["harmonized"] = series_summary(harmonized_wide["time_s"].to_numpy(), harmonized_wide[key].to_numpy())
        row["stats"]["harmonized_coverage"] = coverage[key]

    paths = output_paths(output_root, job)
    paths["mode_root"].mkdir(parents=True, exist_ok=True)
    wide_frame.to_parquet(paths["wide"], engine="pyarrow", index=False)
    harmonized_wide.to_parquet(paths["harmonized_wide"], engine="pyarrow", index=False)

    mode_info = {
        "status": "done",
        "description": "Full-channel TDMS standard layer. Applies standard baseline subtraction to measured channels and preserves reference groups as pass-through.",
        "reference_method": "official_native_zero_preserved",
        "reference_index": int(reference_idx),
        "reference_time_s": float(time_s[reference_idx]),
        "crop_before_reference": False,
        "native_sample_count": int(time_s.size),
        "native_time_start_s": float(time_s[0]),
        "native_time_end_s": float(time_s[-1]),
        "harmonized_sample_count": int(harmonized_wide.shape[0]),
        "harmonized_time_start_s": float(harmonized_wide["time_s"].iat[0]),
        "harmonized_time_end_s": float(harmonized_wide["time_s"].iat[-1]),
        "series": series_rows,
        "metrics": {
            "series_count": len(series_rows),
            "excluded_count": len(exclusions),
            "excluded_examples": exclusions[:50],
            "time_column": time_column,
            "preimpact_window": {"start_s": -0.05, "end_s": -0.04, "sample_count": int(preimpact_mask(time_s).sum())},
        },
        "outputs": {
            "wide": repo_relative(paths["wide"]),
            "harmonized_wide": repo_relative(paths["harmonized_wide"]),
        },
    }

    manifest = {
        "generated_at": utc_now_iso(),
        "parser_version": PARSER_VERSION,
        "filegroup_id": job.filegroup_id,
        "test_code": job.test_code,
        "vehicle_make_model": job.vehicle_make_model,
        "tdms_asset_id": job.tdms_asset_id,
        "signal_container_id": job.signal_container_id,
        "source_parquet_path": repo_relative(job.parquet_path),
        "time_basis": {
            "selected_source": time_column,
            "sample_count": int(time_s.size),
            "sample_rate_hz": float(round(1.0 / np.nanmedian(np.diff(time_s)), 6)),
            "start_time_s": float(time_s[0]),
            "end_time_s": float(time_s[-1]),
            "policy": "Use the raw TDMS export time axis column from signal_parquet as the canonical native time basis.",
        },
        "harmonized_policy": {
            "window_start_s": harmonized_start_s,
            "window_end_s": harmonized_end_s,
            "sample_rate_hz": harmonized_sample_rate_hz,
            "sample_count": int(harmonized_wide.shape[0]),
            "interpolation_method": "linear",
            "out_of_range_policy": "NaN padding",
        },
        "series_catalog": {
            "included_count": len(series_rows),
            "excluded_count": len(exclusions),
        },
        "modes": {MODE: mode_info},
        "outputs": {
            "manifest": repo_relative(paths["manifest"]),
            "modes": {MODE: mode_info["outputs"]},
        },
    }
    paths["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if register_db:
        register_preprocessing_manifest(connection, manifest, preprocessing_run_id=preprocessing_run_id)

    return manifest


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_root = resolve_repo_path(args.output_root) if args.output_root else DERIVED_ROOT

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        ensure_preprocessing_schema(connection)
        manifest = process_filegroup(
            connection=connection,
            filegroup_id=args.filegroup_id,
            output_root=output_root,
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
