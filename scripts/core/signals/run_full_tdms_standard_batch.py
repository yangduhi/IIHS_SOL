from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts.core.signals.preprocess_known_signal_families import ensure_preprocessing_schema, resolve_repo_path, utc_now_iso
from scripts.core.signals.preprocess_tdms_full_standard import (
    DERIVED_ROOT,
    MODE,
    PARSER_VERSION,
    process_filegroup,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch-build full-channel TDMS standard preprocessing for the 400 longitudinal-capable filegroups.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--filegroup-id", type=int, action="append", default=[])
    parser.add_argument("--register-db", action="store_true")
    parser.add_argument("--all", action="store_true", help="Rebuild even when the target mode already exists.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--harmonized-start-s", type=float, default=0.0)
    parser.add_argument("--harmonized-end-s", type=float, default=0.25)
    parser.add_argument("--harmonized-sample-rate-hz", type=float, default=10000.0)
    return parser.parse_args()


def select_jobs(connection: sqlite3.Connection, args: argparse.Namespace) -> list[int]:
    if args.filegroup_id:
        jobs = sorted(set(args.filegroup_id))
    else:
        rows = connection.execute(
            """
            SELECT DISTINCT ss.filegroup_id
              FROM signal_series ss
              JOIN signal_containers sc
                ON sc.signal_container_id = ss.signal_container_id
             WHERE sc.container_type = 'tdms'
               AND sc.extraction_status = 'done'
               AND ss.series_key LIKE '%10VEHC0000_ACX%'
             ORDER BY ss.filegroup_id
            """
        ).fetchall()
        jobs = [int(row["filegroup_id"]) for row in rows]
        if args.register_db and not args.all:
            done_rows = connection.execute(
                """
                SELECT filegroup_id
                  FROM preprocessing_cases
                 WHERE mode = ?
                   AND status = 'done'
                """,
                (MODE,),
            ).fetchall()
            done_set = {int(row["filegroup_id"]) for row in done_rows}
            jobs = [filegroup_id for filegroup_id in jobs if filegroup_id not in done_set]
    if args.limit is not None:
        jobs = jobs[: args.limit]
    return jobs


def create_run(connection: sqlite3.Connection, scope: str) -> int:
    cursor = connection.execute(
        """
        INSERT INTO preprocessing_runs (started_at, parser_version, scope, modes_json, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            utc_now_iso(),
            PARSER_VERSION,
            scope,
            json.dumps([MODE], ensure_ascii=False),
            None,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def finish_run(connection: sqlite3.Connection, preprocessing_run_id: int, notes: dict[str, Any]) -> None:
    connection.execute(
        """
        UPDATE preprocessing_runs
           SET finished_at = ?,
               notes = ?
         WHERE preprocessing_run_id = ?
        """,
        (utc_now_iso(), json.dumps(notes, ensure_ascii=False), preprocessing_run_id),
    )
    connection.commit()


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_root = resolve_repo_path(args.output_root) if args.output_root else DERIVED_ROOT

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        if args.register_db:
            ensure_preprocessing_schema(connection)
        jobs = select_jobs(connection, args)
        scope = "explicit_filegroups" if args.filegroup_id else "tdms_longitudinal_400"
        preprocessing_run_id = create_run(connection, scope) if args.register_db else None
        results: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for filegroup_id in jobs:
            try:
                manifest = process_filegroup(
                    connection=connection,
                    filegroup_id=filegroup_id,
                    output_root=output_root,
                    harmonized_start_s=args.harmonized_start_s,
                    harmonized_end_s=args.harmonized_end_s,
                    harmonized_sample_rate_hz=args.harmonized_sample_rate_hz,
                    register_db=args.register_db,
                    preprocessing_run_id=preprocessing_run_id,
                )
                results.append(
                    {
                        "filegroup_id": filegroup_id,
                        "test_code": manifest["test_code"],
                        "included_series_count": manifest["series_catalog"]["included_count"],
                        "excluded_series_count": manifest["series_catalog"]["excluded_count"],
                        "status": "done",
                    }
                )
            except Exception as exc:
                failures.append(
                    {
                        "filegroup_id": filegroup_id,
                        "status": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        summary = {
            "preprocessing_run_id": preprocessing_run_id,
            "job_count": len(jobs),
            "done_count": len(results),
            "error_count": len(failures),
            "results": results,
            "failures": failures,
        }
        if preprocessing_run_id is not None:
            finish_run(connection, preprocessing_run_id, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
