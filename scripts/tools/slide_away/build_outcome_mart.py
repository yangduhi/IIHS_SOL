from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_LOGS,
    ARTIFACT_TABLES,
    CASE_MASTER_DEFAULT,
    OUTCOME_VERSION,
    OUTCOMES_DEFAULT,
    ensure_dirs,
    json_dumps,
    max_abs,
    min_positive,
    open_connection,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the slide_away case-level outcome mart.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--case-master", default=str(CASE_MASTER_DEFAULT))
    parser.add_argument("--out", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--out-summary", default=str(ARTIFACT_TABLES / "outcomes_v1_summary.csv"))
    parser.add_argument("--out-coverage", default=str(ARTIFACT_TABLES / "outcomes_v1_coverage.csv"))
    parser.add_argument("--log", default=str(ARTIFACT_LOGS / "outcome_mart_build.log"))
    return parser.parse_args()


def _group_metric(dataframe: pd.DataFrame, column: str, fn, mask: pd.Series | None, out_name: str) -> pd.DataFrame:
    target = dataframe.loc[mask] if mask is not None else dataframe
    if target.empty:
        return pd.DataFrame(columns=["filegroup_id", out_name])
    return target.groupby("filegroup_id")[column].apply(fn).reset_index(name=out_name)


def build_outcome_mart(db_path: Path, case_master_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    case_master = pd.read_parquet(case_master_path)
    connection = open_connection(db_path)
    row_catalog = pd.read_sql_query(
        """
        SELECT filegroup_id,
               table_type,
               normalized_label,
               section_key,
               unit,
               result_number,
               time_number,
               left_number,
               right_number,
               resultant_number,
               measure_number
          FROM pdf_result_row_catalog
         WHERE filegroup_id IS NOT NULL
           AND quality_status IS NOT 'review'
           AND table_type IN (
               'intrusion',
               'leg_foot_injury',
               'restraint_kinematics',
               'head_injury',
               'chest_injury',
               'neck_injury',
               'thigh_hip_injury',
               'dummy_clearance'
           )
        """,
        connection,
    )
    connection.close()

    base = case_master[["filegroup_id"]].drop_duplicates().copy()
    intrusion = row_catalog.loc[row_catalog["table_type"] == "intrusion"].copy()
    leg = row_catalog.loc[row_catalog["table_type"] == "leg_foot_injury"].copy()
    restraint = row_catalog.loc[row_catalog["table_type"] == "restraint_kinematics"].copy()
    head = row_catalog.loc[row_catalog["table_type"] == "head_injury"].copy()
    chest = row_catalog.loc[row_catalog["table_type"] == "chest_injury"].copy()
    neck = row_catalog.loc[row_catalog["table_type"] == "neck_injury"].copy()
    thigh = row_catalog.loc[row_catalog["table_type"] == "thigh_hip_injury"].copy()
    clearance = row_catalog.loc[row_catalog["table_type"] == "dummy_clearance"].copy()

    pieces = [
        _group_metric(intrusion, "resultant_number", max_abs, None, "intrusion_max_resultant_cm"),
        _group_metric(intrusion, "resultant_number", max_abs, intrusion["normalized_label"].str.contains("footrest", na=False), "intrusion_footrest_resultant_cm"),
        _group_metric(intrusion, "resultant_number", max_abs, intrusion["normalized_label"].str.contains("left toepan|lefttoepan", na=False), "intrusion_left_toepan_resultant_cm"),
        _group_metric(intrusion, "resultant_number", max_abs, intrusion["normalized_label"].str.contains(r"\bbrake pedal\b", na=False), "intrusion_brake_pedal_resultant_cm"),
        _group_metric(leg, "left_number", max_abs, leg["normalized_label"].eq("index"), "leg_foot_index_left"),
        _group_metric(leg, "right_number", max_abs, leg["normalized_label"].eq("index"), "leg_foot_index_right"),
        _group_metric(leg, "left_number", max_abs, leg["normalized_label"].eq("vector resultant acceleration g"), "foot_resultant_accel_left_g"),
        _group_metric(leg, "right_number", max_abs, leg["normalized_label"].eq("vector resultant acceleration g"), "foot_resultant_accel_right_g"),
        _group_metric(head, "result_number", max_abs, head["normalized_label"].str.contains("hic 15", na=False), "head_hic15"),
        _group_metric(chest, "result_number", max_abs, chest["normalized_label"].eq("rib compression mm"), "chest_rib_compression_mm"),
        _group_metric(chest, "result_number", max_abs, chest["normalized_label"].str.contains("viscous", na=False), "chest_viscous_criteria_ms"),
        _group_metric(neck, "result_number", max_abs, neck["normalized_label"].eq("nij tension extension"), "neck_tension_extension_nij"),
        _group_metric(thigh, "left_number", max_abs, thigh["normalized_label"].str.contains("femur axial force", na=False), "thigh_hip_risk_proxy_left_kn"),
        _group_metric(thigh, "right_number", max_abs, thigh["normalized_label"].str.contains("femur axial force", na=False), "thigh_hip_risk_proxy_right_kn"),
        _group_metric(restraint, "time_number", min_positive, restraint["normalized_label"].str.contains("pretensioner", na=False), "pretensioner_time_ms"),
        _group_metric(restraint, "time_number", min_positive, restraint["normalized_label"].str.contains("face begins loading frontal airbag|contacts frontal airbag", na=False), "airbag_first_contact_time_ms"),
        _group_metric(restraint, "time_number", min_positive, restraint["normalized_label"].str.contains("frontal airbag fully inflated", na=False), "airbag_full_inflation_time_ms"),
        _group_metric(clearance, "measure_number", max_abs, clearance["normalized_label"].eq("head to roof"), "dummy_clearance_head_to_roof_mm"),
        _group_metric(clearance, "measure_number", max_abs, clearance["normalized_label"].eq("knee to dash left"), "dummy_clearance_knee_to_dash_left_mm"),
        _group_metric(clearance, "measure_number", max_abs, clearance["normalized_label"].eq("knee to dash right"), "dummy_clearance_knee_to_dash_right_mm"),
    ]
    restraint_count = (
        restraint.loc[restraint["time_number"].notna()]
        .groupby("filegroup_id")["normalized_label"]
        .nunique()
        .reset_index(name="restraint_event_count")
    )
    pieces.append(restraint_count)

    outcome = base
    for piece in pieces:
        outcome = outcome.merge(piece, on="filegroup_id", how="left")
    outcome["thigh_hip_risk_proxy"] = outcome[["thigh_hip_risk_proxy_left_kn", "thigh_hip_risk_proxy_right_kn"]].max(axis=1)
    outcome["dummy_clearance_min_mm"] = outcome[
        ["dummy_clearance_head_to_roof_mm", "dummy_clearance_knee_to_dash_left_mm", "dummy_clearance_knee_to_dash_right_mm"]
    ].min(axis=1)
    for column in ("leg_foot_index_left", "leg_foot_index_right"):
        outcome.loc[pd.to_numeric(outcome[column], errors="coerce") > 5.0, column] = pd.NA

    required_columns = [
        "intrusion_max_resultant_cm",
        "intrusion_footrest_resultant_cm",
        "intrusion_left_toepan_resultant_cm",
        "intrusion_brake_pedal_resultant_cm",
        "leg_foot_index_left",
        "leg_foot_index_right",
        "foot_resultant_accel_left_g",
        "foot_resultant_accel_right_g",
        "restraint_event_count",
        "pretensioner_time_ms",
        "airbag_first_contact_time_ms",
        "airbag_full_inflation_time_ms",
        "head_hic15",
        "chest_rib_compression_mm",
        "chest_viscous_criteria_ms",
        "neck_tension_extension_nij",
        "thigh_hip_risk_proxy",
    ]
    present_count = outcome[required_columns].notna().sum(axis=1)
    outcome["outcome_quality_score"] = present_count / len(required_columns)
    outcome["outcome_source_version"] = OUTCOME_VERSION

    field_rules = defaultdict(str)
    field_rules.update(
        {
            "intrusion_max_resultant_cm": "intrusion/resultant_number/max_abs",
            "intrusion_footrest_resultant_cm": "intrusion/footrest/resultant_number/max_abs",
            "intrusion_left_toepan_resultant_cm": "intrusion/left_toepan/resultant_number/max_abs",
            "intrusion_brake_pedal_resultant_cm": "intrusion/brake_pedal/resultant_number/max_abs",
            "leg_foot_index_left": "leg_foot_injury/index/left_number/max_abs",
            "leg_foot_index_right": "leg_foot_injury/index/right_number/max_abs",
            "foot_resultant_accel_left_g": "leg_foot_injury/vector_resultant_acceleration_g/left_number/max_abs",
            "foot_resultant_accel_right_g": "leg_foot_injury/vector_resultant_acceleration_g/right_number/max_abs",
            "restraint_event_count": "restraint_kinematics/distinct_normalized_label/time_number_not_null",
            "pretensioner_time_ms": "restraint_kinematics/pretensioner/time_number/min_positive",
            "airbag_first_contact_time_ms": "restraint_kinematics/face_begins_loading_frontal_airbag/time_number/min_positive",
            "airbag_full_inflation_time_ms": "restraint_kinematics/frontal_airbag_fully_inflated/time_number/min_positive",
            "head_hic15": "head_injury/hic15/result_number/max_abs",
            "chest_rib_compression_mm": "chest_injury/rib_compression_mm/result_number/max_abs",
            "chest_viscous_criteria_ms": "chest_injury/viscous_criteria/result_number/max_abs",
            "neck_tension_extension_nij": "neck_injury/nij_tension_extension/result_number/max_abs",
            "thigh_hip_risk_proxy": "thigh_hip_injury/femur_axial_force/max_abs",
        }
    )
    outcome["outcome_provenance_json"] = json_dumps(field_rules)

    summary = pd.DataFrame(
        [
            {"metric": "row_count", "value": int(len(outcome))},
            {"metric": "mean_quality_score", "value": round(float(outcome["outcome_quality_score"].mean(skipna=True)), 6)},
            {"metric": "available_intrusion", "value": int(outcome["intrusion_max_resultant_cm"].notna().sum())},
            {"metric": "available_head_hic15", "value": int(outcome["head_hic15"].notna().sum())},
            {"metric": "available_ri_linkable_core", "value": int(outcome[["intrusion_max_resultant_cm", "head_hic15", "neck_tension_extension_nij"]].notna().any(axis=1).sum())},
        ]
    )
    coverage = pd.DataFrame(
        [
            {"field_name": column, "non_null_count": int(outcome[column].notna().sum()), "coverage_ratio": float(outcome[column].notna().mean())}
            for column in required_columns + [
                "dummy_clearance_head_to_roof_mm",
                "dummy_clearance_knee_to_dash_left_mm",
                "dummy_clearance_knee_to_dash_right_mm",
                "dummy_clearance_min_mm",
            ]
        ]
    )
    return outcome, summary, coverage


def main() -> None:
    args = parse_args()
    ensure_dirs()
    out_path = resolve_path(args.out)
    summary_path = resolve_path(args.out_summary)
    coverage_path = resolve_path(args.out_coverage)
    log_path = resolve_path(args.log)
    outcome, summary, coverage = build_outcome_mart(resolve_path(args.db), resolve_path(args.case_master))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    outcome.to_parquet(out_path, index=False)
    summary.to_csv(summary_path, index=False)
    coverage.to_csv(coverage_path, index=False)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"outcomes={repo_relative(out_path)}",
            f"summary_csv={repo_relative(summary_path)}",
            f"coverage_csv={repo_relative(coverage_path)}",
            f"row_count={len(outcome)}",
            f"mean_quality_score={outcome['outcome_quality_score'].mean(skipna=True):.6f}",
        ],
    )


if __name__ == "__main__":
    main()
