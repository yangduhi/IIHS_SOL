from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from scripts.core.catalog import excel_catalog_schema
from scripts.tools.dashboards import build_excel_dashboard
from scripts.tools.exports import export_excel_catalog


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "small_overlap" / "dashboard" / "excel_catalog"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh Excel catalog views, rebuild the Excel dashboard, and export CSV extracts.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def main() -> None:
    args = parse_args()
    db_path = resolve_path(args.db)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    excel_catalog_schema.ensure_excel_catalog_schema(connection)
    connection.commit()

    dashboard_data = build_excel_dashboard.build_dashboard_data(connection)
    dashboard_path = output_dir / "index.html"
    dashboard_path.write_text(build_excel_dashboard.dashboard_html(dashboard_data), encoding="utf-8")

    export_summary = export_excel_catalog.export_catalog(connection, output_dir)
    workbook_count = connection.execute("SELECT COUNT(*) FROM excel_workbooks").fetchone()[0]
    metric_count = connection.execute("SELECT COUNT(*) FROM extracted_metrics WHERE source_type = 'excel_workbook'").fetchone()[0]
    connection.close()

    print(
        json.dumps(
            {
                "db": str(db_path),
                "dashboard_html": str(dashboard_path),
                "workbooks": workbook_count,
                "metric_rows": metric_count,
                **export_summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
