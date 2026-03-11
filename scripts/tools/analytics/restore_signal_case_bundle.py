from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from scripts.core.signals.preprocess_known_signal_families import ensure_preprocessing_schema, resolve_repo_path


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = REPO_ROOT / "output" / "small_overlap" / "restore_bundles"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore a reproducible preprocessing bundle for one filegroup and mode.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--filegroup-id", type=int, required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def absolute_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_case(connection: sqlite3.Connection, filegroup_id: int, mode: str) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT pc.preprocessing_case_id,
               pc.filegroup_id,
               pc.mode,
               pc.status,
               pc.parser_version,
               pc.manifest_path,
               pc.wide_path,
               pc.long_path,
               pc.harmonized_wide_path,
               pc.harmonized_long_path,
               pc.metrics_json,
               fg.test_code,
               v.vehicle_year,
               v.vehicle_make_model
          FROM preprocessing_cases pc
          JOIN filegroups fg
            ON fg.filegroup_id = pc.filegroup_id
          JOIN vehicles v
            ON v.vehicle_id = fg.vehicle_id
         WHERE pc.filegroup_id = ?
           AND pc.mode = ?
        """,
        (filegroup_id, mode),
    ).fetchone()
    if row is None:
        raise ValueError(f"preprocessing case not found for filegroup_id={filegroup_id}, mode={mode}")
    return row


def load_series(connection: sqlite3.Connection, preprocessing_case_id: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT standard_name,
               channel_family,
               unit,
               cfc_class,
               source_group,
               source_channel,
               raw_reference_group,
               raw_reference_channel,
               native_sample_count,
               harmonized_non_null_count,
               stats_json
          FROM preprocessing_series
         WHERE preprocessing_case_id = ?
         ORDER BY standard_name
        """,
        (preprocessing_case_id,),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["stats_json"] = json.loads(item["stats_json"]) if item.get("stats_json") else {}
        result.append(item)
    return result


def copy_if_exists(source: Path | None, target_dir: Path) -> str | None:
    if source is None or not source.exists():
        return None
    target = target_dir / source.name
    shutil.copy2(source, target)
    return str(target.relative_to(target_dir.parent)).replace("\\", "/")


def rebuild_command(filegroup_id: int, mode: str) -> str:
    if mode == "standard_baseline_full_tdms":
        return f"python scripts/preprocess_tdms_full_standard.py --filegroup-id {filegroup_id} --register-db"
    if mode in {"standard_baseline", "strict_origin", "exploratory_t0"}:
        return f"python scripts/preprocess_known_signal_families.py --filegroup-id {filegroup_id} --modes {mode} --register-db"
    return ""


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_dir = resolve_repo_path(args.output_dir) if args.output_dir else OUTPUT_ROOT
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        ensure_preprocessing_schema(connection)
        case = load_case(connection, args.filegroup_id, args.mode)
        series_rows = load_series(connection, int(case["preprocessing_case_id"]))
    finally:
        connection.close()

    bundle_root = output_dir / f"{case['filegroup_id']}-{case['test_code']}__{case['mode']}"
    bundle_root.mkdir(parents=True, exist_ok=True)
    copied_root = bundle_root / "artifacts"
    copied_root.mkdir(parents=True, exist_ok=True)

    manifest_path = absolute_path(case["manifest_path"])
    wide_path = absolute_path(case["wide_path"])
    long_path = absolute_path(case["long_path"])
    harmonized_wide_path = absolute_path(case["harmonized_wide_path"])
    harmonized_long_path = absolute_path(case["harmonized_long_path"])

    copied = {
        "manifest": copy_if_exists(manifest_path, copied_root),
        "wide": copy_if_exists(wide_path, copied_root),
        "long": copy_if_exists(long_path, copied_root),
        "harmonized_wide": copy_if_exists(harmonized_wide_path, copied_root),
        "harmonized_long": copy_if_exists(harmonized_long_path, copied_root),
    }
    bundle_manifest = {
        "filegroup_id": int(case["filegroup_id"]),
        "test_code": case["test_code"],
        "vehicle_year": int(case["vehicle_year"]) if case["vehicle_year"] is not None else None,
        "vehicle_make_model": case["vehicle_make_model"],
        "mode": case["mode"],
        "status": case["status"],
        "parser_version": case["parser_version"],
        "preprocessing_case_id": int(case["preprocessing_case_id"]),
        "source_paths": {
            "manifest": case["manifest_path"],
            "wide": case["wide_path"],
            "long": case["long_path"],
            "harmonized_wide": case["harmonized_wide_path"],
            "harmonized_long": case["harmonized_long_path"],
        },
        "copied_artifacts": copied,
        "metrics": json.loads(case["metrics_json"]) if case["metrics_json"] else {},
        "series": series_rows,
        "rebuild_command": rebuild_command(int(case["filegroup_id"]), case["mode"]),
    }
    bundle_manifest_path = bundle_root / "restore_bundle.json"
    bundle_manifest_path.write_text(json.dumps(bundle_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "bundle_root": str(bundle_root.relative_to(REPO_ROOT)).replace("\\", "/"),
                "restore_bundle": str(bundle_manifest_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "copied_artifacts": copied,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
