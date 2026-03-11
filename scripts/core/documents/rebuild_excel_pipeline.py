from __future__ import annotations

import argparse
import json
import sqlite3
import time
import warnings
from pathlib import Path

from scripts.core.catalog import excel_catalog_schema
from scripts.core.documents import process_excels
from scripts.tools.dashboards import build_excel_dashboard
from scripts.tools.exports import export_excel_catalog


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "small_overlap" / "dashboard" / "excel_catalog"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-run Excel ETL from scratch, refresh catalog views, rebuild the Excel dashboard, and export CSV extracts."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--excel-workbook-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--commit-interval", type=int, default=25)
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def main() -> None:
    args = parse_args()
    warnings.filterwarnings("ignore", message="Cannot parse header or footer so it will be ignored")
    db_path = resolve_path(args.db)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    commit_interval = max(1, int(args.commit_interval or 1))
    started = time.perf_counter()

    excel_catalog_schema.ensure_excel_catalog_schema(connection)
    connection.commit()

    etl_args = argparse.Namespace(
        db=str(db_path),
        excel_workbook_id=args.excel_workbook_id,
        limit=args.limit,
        all=True,
        include_done=True,
        commit_interval=commit_interval,
    )
    jobs = process_excels.load_jobs(connection, etl_args)
    results: list[dict[str, object]] = []
    for index, job in enumerate(jobs, start=1):
        results.append(process_excels.process_job(connection, job))
        if index % commit_interval == 0:
            connection.commit()
    connection.commit()

    excel_catalog_schema.ensure_excel_catalog_schema(connection)
    connection.commit()
    process_excels.write_summary(results)

    dashboard_data = build_excel_dashboard.build_dashboard_data(connection)
    dashboard_path = output_dir / "index.html"
    dashboard_path.write_text(build_excel_dashboard.dashboard_html(dashboard_data), encoding="utf-8")

    export_summary = export_excel_catalog.export_catalog(connection, output_dir)
    workbook_status = [dict(row) for row in connection.execute(
        """
        SELECT workbook_type, extraction_status, COUNT(*) AS workbook_count
          FROM excel_workbooks
         GROUP BY workbook_type, extraction_status
         ORDER BY workbook_type, extraction_status
        """
    )]
    namespace_counts = [dict(row) for row in connection.execute(
        """
        SELECT namespace, COUNT(*) AS metric_count
          FROM excel_metric_catalog
         GROUP BY namespace
         ORDER BY metric_count DESC, namespace
        """
    )]
    connection.close()

    print(
        json.dumps(
            {
                "db": str(db_path),
                "dashboard_html": str(dashboard_path),
                "processed_jobs": len(results),
                "done_jobs": sum(1 for row in results if row["status"] == "done"),
                "skipped_jobs": sum(1 for row in results if row["status"] == "skipped"),
                "error_jobs": sum(1 for row in results if row["status"] == "error"),
                "sheet_rows": sum(int(row["sheet_count"]) for row in results),
                "metric_rows": sum(int(row["metric_count"]) for row in results),
                "commit_interval": commit_interval,
                "elapsed_seconds": round(time.perf_counter() - started, 2),
                "workbook_status": workbook_status,
                "namespace_counts": namespace_counts,
                **export_summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
