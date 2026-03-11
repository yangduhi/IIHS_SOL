from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_LOGS,
    ARTIFACT_TABLES,
    CASE_MASTER_DEFAULT,
    FEATURES_DEFAULT,
    FEATURES_STRICT_DEFAULT,
    FEATURE_VERSION,
    WINDOW_GRID_MS,
    compute_slide_away_metrics,
    ensure_dirs,
    open_connection,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the slide_away barrier-relative feature mart.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--case-master", default=str(CASE_MASTER_DEFAULT))
    parser.add_argument("--mode", default="standard_baseline", choices=["standard_baseline", "strict_origin"])
    parser.add_argument("--out", default=None)
    parser.add_argument("--out-summary", default=None)
    parser.add_argument("--log", default=None)
    return parser.parse_args()


def default_paths(mode: str) -> tuple[Path, Path, Path]:
    if mode == "strict_origin":
        return (
            FEATURES_STRICT_DEFAULT,
            ARTIFACT_TABLES / "features_v1_strict_origin_summary.csv",
            ARTIFACT_LOGS / "feature_mart_build__strict_origin.log",
        )
    return (
        FEATURES_DEFAULT,
        ARTIFACT_TABLES / "features_v1_summary.csv",
        ARTIFACT_LOGS / "feature_mart_build.log",
    )


def build_feature_mart(db_path: Path, case_master_path: Path, mode: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    case_master = pd.read_parquet(case_master_path).copy()
    connection = open_connection(db_path)
    preprocessing = pd.read_sql_query(
        """
        SELECT preprocessing_case_id, filegroup_id, mode, harmonized_wide_path
          FROM preprocessing_cases
         WHERE mode = ?
           AND status = 'done'
           AND harmonized_wide_path IS NOT NULL
        """,
        connection,
        params=(mode,),
    )
    connection.close()

    work = case_master.merge(preprocessing, on="filegroup_id", how="inner")
    rows: list[dict[str, object]] = []
    for record in work.itertuples(index=False):
        parquet_path = resolve_path(record.harmonized_wide_path)
        frame = pd.read_parquet(parquet_path)
        speed_kmh = record.report_speed_actual_kmh
        if pd.isna(speed_kmh):
            speed_kmh = record.report_speed_target_kmh
        v0_mps = float(speed_kmh) / 3.6 if speed_kmh is not None and not pd.isna(speed_kmh) else float("nan")
        metrics = compute_slide_away_metrics(frame, record.test_side, v0_mps, WINDOW_GRID_MS, default_window_ms=150)
        row = {
            "filegroup_id": int(record.filegroup_id),
            "preprocessing_case_id": int(record.preprocessing_case_id),
            "source_mode": mode,
            "window_s": metrics.default_metrics["window_s"],
            "v0_mps": v0_mps,
            "test_code": record.test_code,
            "vehicle_year": record.vehicle_year,
            "vehicle_make_model": record.vehicle_make_model,
            "test_side": record.test_side,
            "era": record.era,
            "make_model_family": record.make_model_family,
            "analysis_cohort": record.analysis_cohort,
            "harmonized_wide_path": str(parquet_path),
            "cluster_input_flag": metrics.cluster_input_flag,
            "feature_quality_score": metrics.quality_score,
            "feature_version": FEATURE_VERSION,
        }
        row.update(metrics.default_metrics)
        for window_ms, values in metrics.window_metrics.items():
            prefix = f"window_{window_ms:03d}_"
            for key, value in values.items():
                row[f"{prefix}{key}"] = value
        rows.append(row)

    feature_df = pd.DataFrame(rows).sort_values(["filegroup_id"]).reset_index(drop=True)
    feature_df["signal_ready_flag"] = 1
    summary = pd.DataFrame(
        [
            {"metric": "row_count", "value": int(len(feature_df))},
            {"metric": "mode", "value": mode},
            {"metric": "cluster_input_count", "value": int(feature_df["cluster_input_flag"].sum())},
            {"metric": "mean_feature_quality_score", "value": round(float(feature_df["feature_quality_score"].mean(skipna=True)), 6)},
            {"metric": "mean_ri_60", "value": round(float(feature_df["ri"].mean(skipna=True)), 6)},
            {"metric": "mean_delta_vy_away_150", "value": round(float(feature_df["delta_vy_away_mps"].mean(skipna=True)), 6)},
        ]
    )
    return feature_df, summary


def main() -> None:
    args = parse_args()
    ensure_dirs()
    default_out, default_summary, default_log = default_paths(args.mode)
    out_path = resolve_path(args.out or default_out)
    summary_path = resolve_path(args.out_summary or default_summary)
    log_path = resolve_path(args.log or default_log)
    feature_df, summary = build_feature_mart(resolve_path(args.db), resolve_path(args.case_master), args.mode)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_parquet(out_path, index=False)
    summary.to_csv(summary_path, index=False)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"mode={args.mode}",
            f"features={repo_relative(out_path)}",
            f"summary_csv={repo_relative(summary_path)}",
            f"row_count={len(feature_df)}",
            f"cluster_input_count={int(feature_df['cluster_input_flag'].sum())}",
            f"mean_feature_quality_score={feature_df['feature_quality_score'].mean(skipna=True):.6f}",
            f"mean_ri_60={feature_df['ri'].mean(skipna=True):.6f}",
        ],
    )


if __name__ == "__main__":
    main()
