from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "small_overlap" / "dashboard" / "pdf_catalog"


ROW_QUERY = """
SELECT pdf_result_row_id,
       pdf_result_table_id,
       pdf_document_id,
       filegroup_id,
       test_code,
       document_title,
       vehicle_year,
       vehicle_make_model,
       pdf_role,
       family_key,
       family_label,
       report_test_side,
       local_path,
       page_number,
       table_order,
       table_ref,
       table_title,
       table_type,
       table_group,
       row_order,
       section_name,
       seat_position,
       section_key,
       label,
       normalized_label,
       quality_status,
       quality_score,
       quality_flags,
       code,
       unit,
       threshold_text,
       threshold_number,
       result_text,
       result_number,
       time_text,
       time_number,
       left_text,
       left_number,
       left_time_text,
       left_time_number,
       right_text,
       right_number,
       right_time_text,
       right_time_number,
       longitudinal_text,
       longitudinal_number,
       lateral_text,
       lateral_number,
       vertical_text,
       vertical_number,
       resultant_text,
       resultant_number,
       measure_text,
       measure_number,
       raw_row_json
  FROM pdf_result_row_catalog
 ORDER BY test_code, table_type, page_number, table_order, row_order
"""


SUMMARY_QUERY = """
SELECT table_type,
       table_group,
       section_key,
       section_label,
       normalized_label,
       display_label,
       unit,
       seat_positions,
       document_count,
       row_count,
       sample_test_codes
  FROM pdf_common_measure_summary
 ORDER BY document_count DESC, row_count DESC, table_type, section_label, display_label
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export PDF result catalog tables to CSV.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def export_query(connection: sqlite3.Connection, query: str, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
    row_csv = output_dir / "pdf_result_row_catalog.csv"
    summary_csv = output_dir / "pdf_common_measure_summary.csv"
    row_count = export_query(connection, ROW_QUERY, row_csv)
    summary_count = export_query(connection, SUMMARY_QUERY, summary_csv)
    return {
        "row_csv": str(row_csv),
        "summary_csv": str(summary_csv),
        "row_count": row_count,
        "summary_count": summary_count,
    }


def main() -> None:
    args = parse_args()
    db_path = resolve_path(args.db)
    output_dir = resolve_path(args.output_dir)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    summary = export_catalog(connection, output_dir)
    connection.close()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
