from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts.core.catalog import excel_catalog_schema


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "small_overlap" / "dashboard" / "excel_catalog"


QUERIES = {
    "excel_workbook_inventory.csv": """
        SELECT *
          FROM excel_workbook_inventory
         ORDER BY test_code, workbook_type, filename
    """,
    "excel_metric_summary.csv": """
        SELECT *
          FROM excel_metric_summary
         ORDER BY workbook_count DESC, metric_count DESC, workbook_type, namespace, metric_name
    """,
    "excel_metric_catalog.csv": """
        SELECT *
          FROM excel_metric_catalog
         ORDER BY test_code, workbook_type, namespace, metric_name, extracted_metric_id
    """,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Excel ETL catalog views to CSV.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def export_query(connection: sqlite3.Connection, query: str, output_path: Path) -> int:
    cursor = connection.execute(query)
    columns = [column[0] for column in cursor.description]
    row_count = 0
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in cursor:
            writer.writerow([row[column] for column in columns])
            row_count += 1
    return row_count


def export_catalog(connection: sqlite3.Connection, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {}
    for filename, query in QUERIES.items():
        output_path = output_dir / filename
        summary[filename] = {
            "path": str(output_path),
            "row_count": export_query(connection, query, output_path),
        }
    return summary


def main() -> None:
    args = parse_args()
    db_path = resolve_path(args.db)
    output_dir = resolve_path(args.output_dir)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    excel_catalog_schema.ensure_excel_catalog_schema(connection)
    connection.commit()
    summary = export_catalog(connection, output_dir)
    connection.close()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
