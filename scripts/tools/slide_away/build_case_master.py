from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_LOGS,
    ARTIFACT_TABLES,
    CASE_MASTER_DEFAULT,
    CASE_MASTER_VERSION,
    CANONICAL_CSV,
    classify_analysis_cohort,
    ensure_dirs,
    load_canonical,
    normalize_make_model_family,
    open_connection,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the slide_away case master mart.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--canonical", default=str(CANONICAL_CSV))
    parser.add_argument("--out", default=str(CASE_MASTER_DEFAULT))
    parser.add_argument("--out-summary", default=str(ARTIFACT_TABLES / "case_master_summary.csv"))
    parser.add_argument("--log", default=str(ARTIFACT_LOGS / "case_master_build.log"))
    return parser.parse_args()


def build_case_master(db_path: Path, canonical_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    canonical = load_canonical(canonical_path).copy()
    connection = open_connection(db_path)
    preprocessing = pd.read_sql_query(
        """
        SELECT filegroup_id,
               MAX(CASE WHEN mode = 'standard_baseline' AND status = 'done' AND harmonized_wide_path IS NOT NULL THEN 1 ELSE 0 END) AS signal_ready_flag,
               MAX(CASE WHEN mode = 'strict_origin' AND status = 'done' AND harmonized_wide_path IS NOT NULL THEN 1 ELSE 0 END) AS strict_origin_ready_flag,
               MAX(CASE WHEN mode = 'standard_baseline' AND status = 'done' AND harmonized_wide_path IS NOT NULL THEN preprocessing_case_id END) AS standard_preprocessing_case_id,
               MAX(CASE WHEN mode = 'strict_origin' AND status = 'done' AND harmonized_wide_path IS NOT NULL THEN preprocessing_case_id END) AS strict_preprocessing_case_id
          FROM preprocessing_cases
         GROUP BY filegroup_id
        """,
        connection,
    )
    pdf_meta = pd.read_sql_query(
        """
        SELECT filegroup_id,
               MAX(CASE WHEN extraction_status = 'done' THEN 1 ELSE 0 END) AS pdf_available_flag,
               MAX(report_speed_actual_kmh) AS report_speed_actual_kmh,
               MAX(report_speed_target_kmh) AS report_speed_target_kmh,
               MAX(report_overlap_actual_pct) AS report_overlap_actual_pct,
               MAX(report_overlap_target_pct) AS report_overlap_target_pct,
               MAX(report_curb_weight_kg_measured) AS report_curb_weight_kg_measured,
               MAX(report_test_weight_kg_measured) AS report_test_weight_kg_measured
          FROM pdf_document_inventory
         GROUP BY filegroup_id
        """,
        connection,
    )
    connection.close()

    case_master = canonical.merge(preprocessing, on="filegroup_id", how="left")
    case_master = case_master.merge(pdf_meta, on="filegroup_id", how="left")
    case_master["signal_ready_flag"] = case_master["signal_ready_flag"].fillna(0).astype(int)
    case_master["strict_origin_ready_flag"] = case_master["strict_origin_ready_flag"].fillna(0).astype(int)
    case_master["pdf_available_flag"] = case_master["pdf_available_flag"].fillna((case_master["pdf_document_count"].fillna(0) > 0).astype(int)).astype(int)
    case_master["excel_available_flag"] = (pd.to_numeric(case_master["excel_workbook_count"], errors="coerce").fillna(0) > 0).astype(int)
    case_master["make_model_family"] = case_master["vehicle_make_model"].map(normalize_make_model_family)
    case_master["analysis_cohort"] = case_master.apply(classify_analysis_cohort, axis=1)
    case_master["case_master_version"] = CASE_MASTER_VERSION
    case_master["generated_at"] = utc_now_iso()
    case_master["signal_ready_rule"] = "preprocessing_cases.mode=standard_baseline,status=done,harmonized_wide_path!=NULL"

    summary = pd.DataFrame(
        [
            {"metric": "row_count", "value": int(len(case_master))},
            {"metric": "signal_ready_count", "value": int(case_master["signal_ready_flag"].sum())},
            {"metric": "strict_origin_ready_count", "value": int(case_master["strict_origin_ready_flag"].sum())},
            {"metric": "pdf_available_count", "value": int(case_master["pdf_available_flag"].sum())},
            {"metric": "excel_available_count", "value": int(case_master["excel_available_flag"].sum())},
            {"metric": "driver_count", "value": int((case_master["test_side"] == "driver").sum())},
            {"metric": "passenger_count", "value": int((case_master["test_side"] == "passenger").sum())},
        ]
    )
    return case_master, summary


def main() -> None:
    args = parse_args()
    ensure_dirs()
    out_path = resolve_path(args.out)
    summary_path = resolve_path(args.out_summary)
    log_path = resolve_path(args.log)
    case_master, summary = build_case_master(resolve_path(args.db), resolve_path(args.canonical))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    case_master.to_parquet(out_path, index=False)
    summary.to_csv(summary_path, index=False)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"case_master={repo_relative(out_path)}",
            f"summary_csv={repo_relative(summary_path)}",
            f"row_count={len(case_master)}",
            f"signal_ready_count={int(case_master['signal_ready_flag'].sum())}",
            "signal_ready_rule=mode='standard_baseline' AND status='done' AND harmonized_wide_path IS NOT NULL",
        ],
    )


if __name__ == "__main__":
    main()
