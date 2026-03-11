from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.core.signals.preprocess_known_signal_families import ensure_preprocessing_schema, resolve_repo_path


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = REPO_ROOT / "output" / "small_overlap" / "tables"
TARGET_MODES = (
    "standard_baseline",
    "strict_origin",
    "exploratory_t0",
    "standard_baseline_full_tdms",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build preprocessing compliance audit and ETL monitoring tables from research.sqlite."
    )
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def load_tdms_inventory(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT fg.filegroup_id,
               fg.test_code,
               v.vehicle_year,
               v.vehicle_make_model,
               COUNT(DISTINCT sc.signal_container_id) AS tdms_container_count,
               COUNT(DISTINCT ss.signal_series_id) AS raw_series_count
          FROM filegroups fg
          JOIN vehicles v
            ON v.vehicle_id = fg.vehicle_id
          JOIN signal_containers sc
            ON sc.filegroup_id = fg.filegroup_id
           AND sc.container_type = 'tdms'
           AND sc.extraction_status = 'done'
          LEFT JOIN signal_series ss
            ON ss.signal_container_id = sc.signal_container_id
         GROUP BY fg.filegroup_id, fg.test_code, v.vehicle_year, v.vehicle_make_model
         ORDER BY fg.filegroup_id
        """
    ).fetchall()


def load_cases(connection: sqlite3.Connection) -> dict[int, dict[str, sqlite3.Row]]:
    rows = connection.execute(
        """
        SELECT preprocessing_case_id,
               filegroup_id,
               mode,
               status,
               parser_version,
               manifest_path,
               wide_path,
               harmonized_wide_path,
               metrics_json
          FROM preprocessing_cases
         WHERE mode IN (?, ?, ?, ?)
        """,
        TARGET_MODES,
    ).fetchall()
    case_map: dict[int, dict[str, sqlite3.Row]] = defaultdict(dict)
    for row in rows:
        case_map[int(row["filegroup_id"])][row["mode"]] = row
    return case_map


def load_feature_sets(connection: sqlite3.Connection) -> set[int]:
    rows = connection.execute(
        """
        SELECT DISTINCT filegroup_id
          FROM preprocessing_feature_sets
         WHERE source_mode = 'standard_baseline'
           AND status = 'done'
        """
    ).fetchall()
    return {int(row["filegroup_id"]) for row in rows}


def manifest_for_filegroup(case_rows: dict[str, sqlite3.Row]) -> tuple[dict[str, Any] | None, Path | None]:
    for mode in TARGET_MODES:
        row = case_rows.get(mode)
        if row is None or not row["manifest_path"]:
            continue
        manifest_path = Path(row["manifest_path"])
        manifest_path = manifest_path if manifest_path.is_absolute() else REPO_ROOT / manifest_path
        if manifest_path.exists():
            return json.loads(manifest_path.read_text(encoding="utf-8")), manifest_path
    return None, None


def case_root_from_manifest_path(manifest_path: Path | None) -> Path | None:
    return manifest_path.parent if manifest_path else None


def dashboard_exists(case_root: Path | None) -> bool:
    if case_root is None:
        return False
    dashboard_path = REPO_ROOT / "output" / "small_overlap" / "dashboard" / case_root.name / "index.html"
    return dashboard_path.exists()


def plots_exist(case_root: Path | None) -> bool:
    if case_root is None:
        return False
    plots_root = REPO_ROOT / "output" / "small_overlap" / "plots" / case_root.name
    return (plots_root / "01_official_overview.png").exists() and (plots_root / "02_longitudinal_detail.png").exists()


def parse_metrics(row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None or not row["metrics_json"]:
        return {}
    try:
        return json.loads(row["metrics_json"])
    except json.JSONDecodeError:
        return {}


def unavailable_reason(mode: str, manifest: dict[str, Any] | None, case_row: sqlite3.Row | None) -> str:
    if case_row is None or case_row["status"] != "unavailable":
        return ""
    if mode == "exploratory_t0" and manifest is not None:
        assessment = manifest.get("t0_proxy_assessment", {})
        for key in ("description", "summary"):
            if assessment.get(key):
                return str(assessment[key])
    metrics = parse_metrics(case_row)
    if metrics.get("reason"):
        return str(metrics["reason"])
    return "Unavailable reason not recorded in metrics_json."


def missing_channel_summary(manifest: dict[str, Any] | None) -> tuple[int, str]:
    if manifest is None:
        return 0, ""
    missing = manifest.get("missing_channels") or []
    names = [item.get("standard_name", "") for item in missing if item.get("standard_name")]
    return len(missing), "; ".join(names)


def harmonized_ready(case_row: sqlite3.Row | None) -> bool:
    if case_row is None or case_row["status"] != "done" or not case_row["harmonized_wide_path"]:
        return False
    path = Path(case_row["harmonized_wide_path"])
    path = path if path.is_absolute() else REPO_ROOT / path
    return path.exists()


def wide_ready(case_row: sqlite3.Row | None) -> bool:
    if case_row is None or case_row["status"] != "done" or not case_row["wide_path"]:
        return False
    path = Path(case_row["wide_path"])
    path = path if path.is_absolute() else REPO_ROOT / path
    return path.exists()


def preprocess_stage_gaps(row: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if not row["raw_series_ready"]:
        gaps.append("raw_export")
    if row["standard_status"] != "done":
        gaps.append("standard_preprocess")
    if not row["standard_harmonized_ready"]:
        gaps.append("standard_harmonized")
    if not row["feature_ready"]:
        gaps.append("feature_batch")
    if not row["dashboard_ready"]:
        gaps.append("dashboard")
    if not row["plots_ready"]:
        gaps.append("plots")
    return gaps


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    mode_status_counts: dict[str, dict[str, int]] = {}
    unavailable_reasons = Counter()
    missing_stage_counts = Counter()
    for mode in TARGET_MODES:
        counts = Counter(row[f"{mode}_status"] for row in rows)
        mode_status_counts[mode] = dict(sorted(counts.items()))
    for row in rows:
        reason = row["exploratory_t0_unavailable_reason"]
        if reason:
            unavailable_reasons[reason] += 1
        for gap in row["etl_missing_stages"].split("; "):
            if gap:
                missing_stage_counts[gap] += 1
    return {
        "tdms_done_count": len(rows),
        "mode_status_counts": mode_status_counts,
        "feature_ready_count": int(sum(1 for row in rows if row["feature_ready"])),
        "dashboard_ready_count": int(sum(1 for row in rows if row["dashboard_ready"])),
        "plots_ready_count": int(sum(1 for row in rows if row["plots_ready"])),
        "missing_stage_counts": dict(sorted(missing_stage_counts.items())),
        "exploratory_t0_unavailable_reasons": dict(unavailable_reasons.most_common()),
    }


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_dir = resolve_repo_path(args.output_dir) if args.output_dir else OUTPUT_ROOT
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        ensure_preprocessing_schema(connection)
        inventory_rows = load_tdms_inventory(connection)
        case_map = load_cases(connection)
        feature_ready_filegroups = load_feature_sets(connection)

        audit_rows: list[dict[str, Any]] = []
        for inventory in inventory_rows:
            filegroup_id = int(inventory["filegroup_id"])
            cases = case_map.get(filegroup_id, {})
            manifest, manifest_path = manifest_for_filegroup(cases)
            case_root = case_root_from_manifest_path(manifest_path)
            missing_count, missing_names = missing_channel_summary(manifest)

            row: dict[str, Any] = {
                "filegroup_id": filegroup_id,
                "test_code": inventory["test_code"],
                "vehicle_year": int(inventory["vehicle_year"]) if inventory["vehicle_year"] is not None else None,
                "vehicle_make_model": inventory["vehicle_make_model"],
                "tdms_container_count": int(inventory["tdms_container_count"]),
                "raw_series_count": int(inventory["raw_series_count"]),
                "raw_series_ready": int(inventory["raw_series_count"]) > 0,
                "manifest_path": str(manifest_path) if manifest_path else "",
                "missing_channel_count": missing_count,
                "missing_channels": missing_names,
                "feature_ready": filegroup_id in feature_ready_filegroups,
                "dashboard_ready": dashboard_exists(case_root),
                "plots_ready": plots_exist(case_root),
            }

            for mode in TARGET_MODES:
                case_row = cases.get(mode)
                row[f"{mode}_status"] = case_row["status"] if case_row is not None else "missing"
                row[f"{mode}_wide_ready"] = wide_ready(case_row)
                row[f"{mode}_harmonized_ready"] = harmonized_ready(case_row)
            row["standard_status"] = row["standard_baseline_status"]
            row["strict_status"] = row["strict_origin_status"]
            row["t0_status"] = row["exploratory_t0_status"]
            row["full_tdms_status"] = row["standard_baseline_full_tdms_status"]
            row["standard_harmonized_ready"] = row["standard_baseline_harmonized_ready"]
            row["full_tdms_harmonized_ready"] = row["standard_baseline_full_tdms_harmonized_ready"]
            row["exploratory_t0_unavailable_reason"] = unavailable_reason("exploratory_t0", manifest, cases.get("exploratory_t0"))
            row["etl_missing_stages"] = "; ".join(preprocess_stage_gaps(row))
            audit_rows.append(row)

        audit_df = pd.DataFrame(audit_rows).sort_values(["filegroup_id"])
        summary = summarize(audit_rows)

        audit_csv = output_dir / "signal_preprocessing_audit.csv"
        etl_csv = output_dir / "signal_etl_monitor.csv"
        audit_json = output_dir / "signal_preprocessing_audit.json"
        etl_json = output_dir / "signal_etl_monitor.json"

        audit_df.to_csv(audit_csv, index=False)
        audit_df.to_csv(etl_csv, index=False)
        audit_json.write_text(
            json.dumps({"summary": summary, "rows": audit_rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        etl_json.write_text(
            json.dumps({"summary": summary, "rows": audit_rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(
            json.dumps(
                {
                    "summary": summary,
                    "outputs": {
                        "audit_csv": str(audit_csv.relative_to(REPO_ROOT)).replace("\\", "/"),
                        "etl_csv": str(etl_csv.relative_to(REPO_ROOT)).replace("\\", "/"),
                        "audit_json": str(audit_json.relative_to(REPO_ROOT)).replace("\\", "/"),
                        "etl_json": str(etl_json.relative_to(REPO_ROOT)).replace("\\", "/"),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
