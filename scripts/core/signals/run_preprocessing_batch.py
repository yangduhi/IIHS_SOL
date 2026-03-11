from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts.core.signals.preprocess_known_signal_families import (
    DEFAULT_HARMONIZED_END_S,
    DEFAULT_HARMONIZED_SAMPLE_RATE_HZ,
    DEFAULT_HARMONIZED_START_S,
    DEFAULT_MODES,
    DERIVED_ROOT,
    ensure_preprocessing_schema,
    parse_modes,
    process_filegroup,
    resolve_repo_path,
    utc_now_iso,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch-build three-mode preprocessing outputs and register them in the research DB.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--filegroup-id", type=int, action="append", default=[])
    parser.add_argument("--all", action="store_true", help="Include filegroups that already have done rows for every requested mode.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--modes", default=",".join(DEFAULT_MODES))
    parser.add_argument("--harmonized-start-s", type=float, default=DEFAULT_HARMONIZED_START_S)
    parser.add_argument("--harmonized-end-s", type=float, default=DEFAULT_HARMONIZED_END_S)
    parser.add_argument("--harmonized-sample-rate-hz", type=float, default=DEFAULT_HARMONIZED_SAMPLE_RATE_HZ)
    return parser.parse_args()


def load_tdms_filegroups(connection: sqlite3.Connection) -> list[int]:
    rows = connection.execute(
        """
        SELECT DISTINCT filegroup_id
          FROM signal_containers
         WHERE container_type = 'tdms'
           AND extraction_status = 'done'
         ORDER BY filegroup_id
        """
    ).fetchall()
    return [int(row["filegroup_id"]) for row in rows]


def done_modes_by_filegroup(connection: sqlite3.Connection, modes: tuple[str, ...]) -> dict[int, set[str]]:
    placeholders = ",".join("?" for _ in modes)
    query = f"""
        SELECT filegroup_id, mode
          FROM preprocessing_cases
         WHERE status = 'done'
           AND mode IN ({placeholders})
    """
    mapping: dict[int, set[str]] = {}
    for row in connection.execute(query, modes):
        mapping.setdefault(int(row["filegroup_id"]), set()).add(row["mode"])
    return mapping


def select_jobs(connection: sqlite3.Connection, args: argparse.Namespace, modes: tuple[str, ...]) -> list[int]:
    if args.filegroup_id:
        jobs = sorted(set(args.filegroup_id))
    else:
        jobs = load_tdms_filegroups(connection)
        if not args.all:
            done_map = done_modes_by_filegroup(connection, modes)
            wanted = set(modes)
            jobs = [filegroup_id for filegroup_id in jobs if done_map.get(filegroup_id, set()) != wanted]
    if args.limit is not None:
        jobs = jobs[: args.limit]
    return jobs


def create_run(connection: sqlite3.Connection, modes: tuple[str, ...], scope: str) -> int:
    cursor = connection.execute(
        """
        INSERT INTO preprocessing_runs (started_at, parser_version, scope, modes_json, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            utc_now_iso(),
            "signal-preprocessing:v2",
            scope,
            json.dumps(list(modes), ensure_ascii=False),
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
    modes = parse_modes(args.modes)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        ensure_preprocessing_schema(connection)
        jobs = select_jobs(connection, args, modes)
        scope = "explicit_filegroups" if args.filegroup_id else "tdms_batch"
        preprocessing_run_id = create_run(connection, modes, scope)

        results: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for filegroup_id in jobs:
            try:
                manifest = process_filegroup(
                    connection=connection,
                    filegroup_id=filegroup_id,
                    output_root=output_root,
                    modes=modes,
                    harmonized_start_s=args.harmonized_start_s,
                    harmonized_end_s=args.harmonized_end_s,
                    harmonized_sample_rate_hz=args.harmonized_sample_rate_hz,
                    register_db=True,
                    preprocessing_run_id=preprocessing_run_id,
                )
                results.append(
                    {
                        "filegroup_id": filegroup_id,
                        "test_code": manifest["test_code"],
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
        finish_run(connection, preprocessing_run_id, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
