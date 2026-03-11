from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "pdf" / "pdf_result_rows.csv"

EXPORT_COLUMNS = [
    "test_code",
    "vehicle_year",
    "vehicle_make_model",
    "pdf_role",
    "report_test_side",
    "table_type",
    "table_group",
    "table_title",
    "page_number",
    "table_ref",
    "row_order",
    "section_name",
    "seat_position",
    "section_key",
    "label",
    "normalized_label",
    "quality_status",
    "quality_score",
    "quality_flags",
    "code",
    "unit",
    "threshold_text",
    "result_text",
    "time_text",
    "left_text",
    "left_time_text",
    "right_text",
    "right_time_text",
    "longitudinal_text",
    "lateral_text",
    "vertical_text",
    "resultant_text",
    "measure_text",
    "raw_row_json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export normalized PDF result rows to CSV.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--table-type", action="append", default=[], help="Repeatable filter for table_type values.")
    parser.add_argument("--test-code", action="append", default=[], help="Repeatable filter for test_code values.")
    parser.add_argument("--quality-status", action="append", default=[], help="Repeatable filter for quality_status values.")
    parser.add_argument("--search", default="", help="Case-insensitive keyword search across common text fields.")
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def build_query(args: argparse.Namespace) -> tuple[str, list[str | int]]:
    where_clauses: list[str] = []
    params: list[str | int] = []

    if args.table_type:
        placeholders = ", ".join("?" for _ in args.table_type)
        where_clauses.append(f"table_type IN ({placeholders})")
        params.extend(args.table_type)

    if args.test_code:
        placeholders = ", ".join("?" for _ in args.test_code)
        where_clauses.append(f"test_code IN ({placeholders})")
        params.extend(args.test_code)

    if args.quality_status:
        placeholders = ", ".join("?" for _ in args.quality_status)
        where_clauses.append(f"quality_status IN ({placeholders})")
        params.extend(args.quality_status)

    if args.search.strip():
        keyword = f"%{args.search.strip().lower()}%"
        where_clauses.append(
            """
            LOWER(
                COALESCE(test_code, '') || ' ' ||
                COALESCE(vehicle_make_model, '') || ' ' ||
                COALESCE(table_type, '') || ' ' ||
                COALESCE(table_title, '') || ' ' ||
                COALESCE(section_name, '') || ' ' ||
                COALESCE(section_key, '') || ' ' ||
                COALESCE(label, '') || ' ' ||
                COALESCE(normalized_label, '') || ' ' ||
                COALESCE(quality_status, '') || ' ' ||
                COALESCE(quality_flags, '') || ' ' ||
                COALESCE(code, '')
            ) LIKE ?
            """
        )
        params.append(keyword)

    query = f"""
        SELECT {", ".join(EXPORT_COLUMNS)}
          FROM pdf_result_row_catalog
    """
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY test_code, table_type, page_number, row_order"
    if args.limit is not None:
        query += " LIMIT ?"
        params.append(args.limit)
    return query, params


def main() -> None:
    args = parse_args()
    db_path = resolve_path(args.db)
    output_path = resolve_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    query, params = build_query(args)
    rows = connection.execute(query, params).fetchall()

    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            payload = dict(row)
            if isinstance(payload.get("quality_flags"), str) and payload["quality_flags"]:
                try:
                    payload["quality_flags"] = json.dumps(json.loads(payload["quality_flags"]), ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
            if payload.get("raw_row_json"):
                try:
                    payload["raw_row_json"] = json.dumps(json.loads(payload["raw_row_json"]), ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
            writer.writerow(payload)

    print(json.dumps({"output_csv": str(output_path), "row_count": len(rows)}, ensure_ascii=False, indent=2))
    connection.close()


if __name__ == "__main__":
    main()
