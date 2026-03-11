from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader


PARSER_VERSION = "pdf-pipeline:v2"
PREVIEW_DIR = Path("output/pdf/layout_previews")
RAW_DATA_ROOT = Path("data/raw").resolve()

PDF_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pdf_extraction_runs (
  pdf_extraction_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  parser_version TEXT NOT NULL,
  scope TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS pdf_layout_families (
  family_key TEXT PRIMARY KEY,
  family_label TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS pdf_layout_assignments (
  pdf_layout_assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
  pdf_document_id INTEGER NOT NULL,
  pdf_extraction_run_id INTEGER,
  family_key TEXT NOT NULL,
  confidence REAL,
  classification_method TEXT,
  signature_hash TEXT,
  preview_png_path TEXT,
  fingerprint_json TEXT,
  classified_at TEXT NOT NULL,
  notes TEXT,
  UNIQUE(pdf_document_id, pdf_extraction_run_id),
  FOREIGN KEY(pdf_document_id) REFERENCES pdf_documents(pdf_document_id) ON DELETE CASCADE,
  FOREIGN KEY(pdf_extraction_run_id) REFERENCES pdf_extraction_runs(pdf_extraction_run_id) ON DELETE SET NULL,
  FOREIGN KEY(family_key) REFERENCES pdf_layout_families(family_key)
);

CREATE TABLE IF NOT EXISTS pdf_page_features (
  pdf_document_id INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  page_width REAL,
  page_height REAL,
  word_count INTEGER,
  char_count INTEGER,
  table_count INTEGER,
  first_line TEXT,
  last_line TEXT,
  heading_lines_json TEXT,
  layout_signature TEXT,
  PRIMARY KEY(pdf_document_id, page_number),
  FOREIGN KEY(pdf_document_id) REFERENCES pdf_documents(pdf_document_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pdf_layout_assignments_family ON pdf_layout_assignments(family_key);

CREATE TABLE IF NOT EXISTS pdf_document_inventory (
  pdf_document_id INTEGER PRIMARY KEY,
  asset_id INTEGER NOT NULL UNIQUE,
  filegroup_id INTEGER NOT NULL,
  test_code TEXT,
  title TEXT,
  filegroup_tested_on TEXT,
  test_type_label TEXT,
  vehicle_year INTEGER,
  vehicle_make_model TEXT,
  dataset_partition TEXT,
  pdf_role TEXT NOT NULL,
  family_key TEXT,
  family_label TEXT,
  family_source_kind TEXT,
  extraction_status TEXT NOT NULL,
  local_exists INTEGER NOT NULL DEFAULT 1,
  local_path TEXT,
  relative_path TEXT,
  folder_path TEXT,
  filename TEXT,
  page_count INTEGER,
  total_table_count INTEGER,
  pages_with_tables INTEGER,
  total_word_count INTEGER,
  avg_words_per_page REAL,
  first_page_heading TEXT,
  second_page_heading TEXT,
  report_vehicle_title TEXT,
  report_tested_on TEXT,
  report_test_side TEXT,
  report_body_type TEXT,
  report_engine_transmission TEXT,
  report_test_protocol TEXT,
  report_test_protocol_version TEXT,
  report_speed_target_kmh REAL,
  report_speed_actual_kmh REAL,
  report_overlap_target_pct REAL,
  report_overlap_actual_pct REAL,
  report_wheelbase_cm_manufacturer REAL,
  report_wheelbase_cm_measured REAL,
  report_overall_length_cm_manufacturer REAL,
  report_overall_length_cm_measured REAL,
  report_overall_width_cm_manufacturer REAL,
  report_overall_width_cm_measured REAL,
  report_curb_weight_kg_manufacturer REAL,
  report_curb_weight_kg_measured REAL,
  report_test_weight_kg_measured REAL,
  edr_vendor TEXT,
  edr_vendor_family TEXT,
  edr_case_number TEXT,
  edr_software_version TEXT,
  vehicle_identification_number TEXT,
  classification_confidence REAL,
  classification_method TEXT,
  preview_png_path TEXT,
  notes TEXT,
  FOREIGN KEY(pdf_document_id) REFERENCES pdf_documents(pdf_document_id) ON DELETE CASCADE,
  FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_family_summary (
  family_key TEXT PRIMARY KEY,
  family_label TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  document_count INTEGER NOT NULL,
  locally_available_count INTEGER NOT NULL,
  completed_count INTEGER NOT NULL,
  avg_page_count REAL,
  avg_table_count REAL,
  avg_word_count REAL,
  avg_confidence REAL
);

CREATE TABLE IF NOT EXISTS pdf_metric_coverage (
  family_key TEXT NOT NULL,
  family_label TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  namespace TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  document_count INTEGER NOT NULL,
  available_document_count INTEGER NOT NULL,
  coverage_ratio REAL NOT NULL,
  PRIMARY KEY (family_key, namespace, metric_name)
);

CREATE TABLE IF NOT EXISTS pdf_result_tables (
  pdf_result_table_id INTEGER PRIMARY KEY AUTOINCREMENT,
  pdf_document_id INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  table_order INTEGER NOT NULL,
  table_ref TEXT,
  title TEXT NOT NULL,
  table_type TEXT NOT NULL,
  table_group TEXT NOT NULL,
  extraction_method TEXT NOT NULL,
  header_json TEXT,
  metadata_json TEXT,
  raw_text TEXT,
  raw_table_json TEXT,
  row_count INTEGER NOT NULL DEFAULT 0,
  UNIQUE(pdf_document_id, page_number, table_order),
  FOREIGN KEY(pdf_document_id) REFERENCES pdf_documents(pdf_document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_result_rows (
  pdf_result_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
  pdf_result_table_id INTEGER NOT NULL,
  row_order INTEGER NOT NULL,
  section_name TEXT,
  seat_position TEXT,
  section_key TEXT,
  label TEXT,
  normalized_label TEXT,
  quality_status TEXT,
  quality_score REAL,
  quality_flags TEXT,
  code TEXT,
  unit TEXT,
  threshold_text TEXT,
  threshold_number REAL,
  result_text TEXT,
  result_number REAL,
  time_text TEXT,
  time_number REAL,
  left_text TEXT,
  left_number REAL,
  left_time_text TEXT,
  left_time_number REAL,
  right_text TEXT,
  right_number REAL,
  right_time_text TEXT,
  right_time_number REAL,
  longitudinal_text TEXT,
  longitudinal_number REAL,
  lateral_text TEXT,
  lateral_number REAL,
  vertical_text TEXT,
  vertical_number REAL,
  resultant_text TEXT,
  resultant_number REAL,
  measure_text TEXT,
  measure_number REAL,
  raw_row_json TEXT,
  UNIQUE(pdf_result_table_id, row_order),
  FOREIGN KEY(pdf_result_table_id) REFERENCES pdf_result_tables(pdf_result_table_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_result_table_summary (
  table_type TEXT PRIMARY KEY,
  table_group TEXT NOT NULL,
  document_count INTEGER NOT NULL,
  table_count INTEGER NOT NULL,
  row_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pdf_common_measure_summary (
  table_type TEXT NOT NULL,
  table_group TEXT NOT NULL,
  section_key TEXT NOT NULL DEFAULT '',
  section_label TEXT NOT NULL DEFAULT '',
  normalized_label TEXT NOT NULL,
  display_label TEXT NOT NULL,
  unit TEXT NOT NULL DEFAULT '',
  seat_positions TEXT,
  document_count INTEGER NOT NULL,
  row_count INTEGER NOT NULL,
  sample_test_codes TEXT,
  PRIMARY KEY (table_type, section_key, normalized_label, unit)
);

CREATE INDEX IF NOT EXISTS idx_pdf_document_inventory_role ON pdf_document_inventory(pdf_role);
CREATE INDEX IF NOT EXISTS idx_pdf_document_inventory_family ON pdf_document_inventory(family_key);
CREATE INDEX IF NOT EXISTS idx_pdf_document_inventory_test_code ON pdf_document_inventory(test_code);
CREATE INDEX IF NOT EXISTS idx_pdf_result_tables_document ON pdf_result_tables(pdf_document_id, page_number);
CREATE INDEX IF NOT EXISTS idx_pdf_result_tables_type ON pdf_result_tables(table_type);
CREATE INDEX IF NOT EXISTS idx_pdf_result_rows_table ON pdf_result_rows(pdf_result_table_id, row_order);
CREATE INDEX IF NOT EXISTS idx_pdf_common_measure_summary_type ON pdf_common_measure_summary(table_type, document_count);
"""

PDF_LAYOUT_FAMILIES = [
    (
        "report_legacy_crashworthiness",
        "Legacy Crashworthiness Report",
        "report",
        "Older IIHS crashworthiness report template with 'Crashworthiness Evaluation Crash Test Report' heading.",
    ),
    (
        "report_modern_small_overlap_v7",
        "Modern Small Overlap Report V7",
        "report",
        "Modern IIHS report template for small overlap tests using protocol version 7.",
    ),
    (
        "report_modern_small_overlap_v8",
        "Modern Small Overlap Report V8",
        "report",
        "Modern IIHS report template for small overlap tests using protocol version 8.",
    ),
    (
        "report_iihs_generic",
        "Generic IIHS Report",
        "report",
        "IIHS-branded report PDF that does not match a stricter small-overlap family rule.",
    ),
    (
        "edr_bosch_cdr",
        "Bosch CDR Export",
        "edr",
        "Bosch Crash Data Retrieval export PDF with the standard Robert Bosch notice.",
    ),
    (
        "edr_hyundai_g_edr",
        "Hyundai G-EDR Export",
        "edr",
        "Hyundai G-EDR PDF export with pipe-delimited vehicle information and G-EDR version text.",
    ),
    (
        "edr_restraint_control_module",
        "Restraint Control Module Analysis",
        "edr",
        "Legacy restraint control module analysis report PDF.",
    ),
    (
        "edr_generic",
        "Generic EDR PDF",
        "edr",
        "EDR-origin PDF that does not match a known Bosch or Hyundai family.",
    ),
    (
        "pdf_unknown",
        "Unknown PDF",
        "unknown",
        "PDF that could not be confidently assigned to a known family.",
    ),
]

REPORT_DIMENSION_FIELDS = {
    "wheelbase": "cm",
    "overall_length": "cm",
    "overall_width": "cm",
    "curb_weight": "kg",
    "test_weight": "kg",
}

ROMAN_NUMERAL_VALUES = {
    "I": 1.0,
    "II": 2.0,
    "III": 3.0,
    "IV": 4.0,
    "V": 5.0,
    "VI": 6.0,
    "VII": 7.0,
    "VIII": 8.0,
    "IX": 9.0,
    "X": 10.0,
}

TABLE_START_RE = re.compile(r"^(Table|Attachment)\s*([0-9]+)\b\s*(.*)$", flags=re.IGNORECASE)
RESULT_VALUE_PATTERN = r"(?:[+\-]?\d+(?:\.\d+)?|±\d+(?:\.\d+)?|--|n/a|\d+(?:\.\d+)?-\d+(?:\.\d+)?)(?:\s*\*+)?"
TIME_VALUE_PATTERN = r"(?:--|\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?)"
RESULT_VALUE_RE = re.compile(rf"^{RESULT_VALUE_PATTERN}$", flags=re.IGNORECASE)
TIME_VALUE_RE = re.compile(rf"^{TIME_VALUE_PATTERN}$", flags=re.IGNORECASE)
RESULT_TABLE_PATTERNS = [
    ("restraint_kinematics", "kinematics", "restraint system performance and dummy kinematics"),
    ("intrusion", "intrusion", "residual measurements of intrusion relative to driver seat"),
    ("head_injury", "injury", "head injury measurements"),
    ("neck_injury", "injury", "neck injury measurements"),
    ("chest_injury", "injury", "chest injury measurements"),
    ("leg_foot_injury", "injury", "leg and foot injury measurements"),
    ("thigh_hip_injury", "injury", "thigh and hip injury measurements"),
    ("dummy_clearance", "measurements", "dummy clearance measurements"),
]
RESULT_TOKEN_RE2 = re.compile(r"(?:[±+\-–−]?\d+(?:\.\d+)?(?:-[±+\-–−]?\d+(?:\.\d+)?)?(?:°)?\*{0,2}|--|n/?a)", flags=re.IGNORECASE)
CODE_TOKEN_RE = re.compile(r"^[A-Z]{2,4}$")
UNIT_ONLY_RE = re.compile(r"^\((?:mm|cm|Nm|kN|g|Ns|m/s)\)$", flags=re.IGNORECASE)
INJURY_SECTION_HEADERS = {"upper tibia", "lower tibia", "foot"}
OCR_ALIAS_PATTERNS = [
    (re.compile(r"\bseat[- ]beltcrash\b", flags=re.IGNORECASE), "seat belt crash"),
    (re.compile(r"\bheadcontacts\b", flags=re.IGNORECASE), "Head contacts"),
    (re.compile(r"\bA\s*-\s*pillar\b", flags=re.IGNORECASE), "A-pillar"),
    (re.compile(r"\bhea\s+de\s*r\b", flags=re.IGNORECASE), "header"),
    (re.compile(r"\bhead\s+er\b", flags=re.IGNORECASE), "header"),
    (re.compile(r"\babdom\s+en\b", flags=re.IGNORECASE), "abdomen"),
    (re.compile(r"\bdo\s+or\b", flags=re.IGNORECASE), "door"),
    (re.compile(r"\bd\s+oor\b", flags=re.IGNORECASE), "door"),
    (re.compile(r"\bk\s+nee\b", flags=re.IGNORECASE), "knee"),
    (re.compile(r"\ba\s+nkle\b", flags=re.IGNORECASE), "ankle"),
    (re.compile(r"\ban\s+gle\b", flags=re.IGNORECASE), "angle"),
    (re.compile(r"\bs\s+ide\b", flags=re.IGNORECASE), "side"),
    (re.compile(r"\bwind\s+ow\b", flags=re.IGNORECASE), "window"),
    (re.compile(r"\bwin\s+dow\b", flags=re.IGNORECASE), "window"),
    (re.compile(r"\bverti?\s+cal\b", flags=re.IGNORECASE), "vertical"),
    (re.compile(r"\bhori\s+zontal\b", flags=re.IGNORECASE), "horizontal"),
    (re.compile(r"\bdas\s+h\b", flags=re.IGNORECASE), "dash"),
    (re.compile(r"\bp\s+oint\b", flags=re.IGNORECASE), "point"),
    (re.compile(r"\bwhee\s+l\b", flags=re.IGNORECASE), "wheel"),
    (re.compile(r"\bwhe\s+el\b", flags=re.IGNORECASE), "wheel"),
    (re.compile(r"\bwh\s+ee\s+l\b", flags=re.IGNORECASE), "wheel"),
    (re.compile(r"\br\s+oof\b", flags=re.IGNORECASE), "roof"),
]
RESIDUAL_OCR_FRAGMENT_RE = re.compile(
    r"\b(?:hea\s+de\s*r|head\s+er|abdom\s+en|do\s+or|d\s+oor|k\s+nee|a\s+nkle|an\s+gle|s\s+ide|wind\s+ow|win\s+dow|verti?\s+cal|hori\s+zontal|das\s+h|p\s+oint|whee\s+l|whe\s+el|wh\s+ee\s+l|r\s+oof)\b",
    flags=re.IGNORECASE,
)
LABEL_NUMERIC_PREFIX_RE = re.compile(r"^\d{1,3}\s+")
LABEL_TABLE_PREFIX_RE = re.compile(r"^(?:table|attachment)\s+\d+\b", flags=re.IGNORECASE)


@dataclass
class PdfJob:
    pdf_document_id: int
    asset_id: int
    filegroup_id: int
    test_code: str
    title: str
    folder_path: str
    filename: str
    local_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify and extract PDF content into the research database.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--pdf-document-id", type=int, default=None)
    parser.add_argument("--all", action="store_true", help="Process all PDF documents instead of only pending/error rows.")
    parser.add_argument(
        "--include-skipped",
        action="store_true",
        help="Include documents marked as skipped when --all is used.",
    )
    parser.add_argument("--render-previews", action="store_true", help="Render first-page previews for every processed PDF.")
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def nonempty_lines(value: str) -> list[str]:
    return [normalize_text(line) for line in (value or "").splitlines() if normalize_text(line)]


def ensure_column_exists(connection: sqlite3.Connection, table_name: str, column_name: str, ddl: str) -> None:
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}
    if column_name not in existing:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")


def refresh_pdf_catalog_views(connection: sqlite3.Connection) -> None:
    connection.execute("DROP VIEW IF EXISTS pdf_result_row_catalog")
    connection.execute(
        """
        CREATE VIEW pdf_result_row_catalog AS
        SELECT prr.pdf_result_row_id,
               prr.pdf_result_table_id,
               prt.pdf_document_id,
               pdi.filegroup_id,
               pdi.test_code,
               pdi.title AS document_title,
               pdi.vehicle_year,
               pdi.vehicle_make_model,
               pdi.pdf_role,
               pdi.family_key,
               pdi.family_label,
               pdi.report_test_side,
               pdi.local_path,
               prt.page_number,
               prt.table_order,
               prt.table_ref,
               prt.title AS table_title,
               prt.table_type,
               prt.table_group,
               prr.row_order,
               prr.section_name,
               prr.seat_position,
               prr.section_key,
               prr.label,
               prr.normalized_label,
               prr.quality_status,
               prr.quality_score,
               prr.quality_flags,
               prr.code,
               prr.unit,
               prr.threshold_text,
               prr.threshold_number,
               prr.result_text,
               prr.result_number,
               prr.time_text,
               prr.time_number,
               prr.left_text,
               prr.left_number,
               prr.left_time_text,
               prr.left_time_number,
               prr.right_text,
               prr.right_number,
               prr.right_time_text,
               prr.right_time_number,
               prr.longitudinal_text,
               prr.longitudinal_number,
               prr.lateral_text,
               prr.lateral_number,
               prr.vertical_text,
               prr.vertical_number,
               prr.resultant_text,
               prr.resultant_number,
               prr.measure_text,
               prr.measure_number,
               prr.raw_row_json
          FROM pdf_result_rows prr
          JOIN pdf_result_tables prt ON prt.pdf_result_table_id = prr.pdf_result_table_id
          JOIN pdf_document_inventory pdi ON pdi.pdf_document_id = prt.pdf_document_id
        """
    )


def ensure_pdf_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(PDF_SCHEMA_SQL)
    ensure_column_exists(connection, "pdf_result_rows", "seat_position", "TEXT")
    ensure_column_exists(connection, "pdf_result_rows", "section_key", "TEXT")
    ensure_column_exists(connection, "pdf_result_rows", "normalized_label", "TEXT")
    ensure_column_exists(connection, "pdf_result_rows", "quality_status", "TEXT")
    ensure_column_exists(connection, "pdf_result_rows", "quality_score", "REAL")
    ensure_column_exists(connection, "pdf_result_rows", "quality_flags", "TEXT")
    ensure_column_exists(connection, "pdf_common_measure_summary", "seat_positions", "TEXT")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_pdf_result_rows_label ON pdf_result_rows(normalized_label, section_key)")
    refresh_pdf_catalog_views(connection)
    connection.executemany(
        "INSERT OR IGNORE INTO pdf_layout_families (family_key, family_label, source_kind, description) VALUES (?, ?, ?, ?)",
        PDF_LAYOUT_FAMILIES,
    )


def create_run(connection: sqlite3.Connection, scope: str) -> int:
    cursor = connection.execute(
        "INSERT INTO pdf_extraction_runs (started_at, parser_version, scope, notes) VALUES (?, ?, ?, ?)",
        (utc_now_iso(), PARSER_VERSION, scope, "Initial layout classification and first-pass PDF extraction."),
    )
    return int(cursor.lastrowid)


def finalize_run(connection: sqlite3.Connection, run_id: int, notes: str) -> None:
    connection.execute(
        "UPDATE pdf_extraction_runs SET finished_at = ?, notes = ? WHERE pdf_extraction_run_id = ?",
        (utc_now_iso(), notes, run_id),
    )


def build_scope(args: argparse.Namespace) -> str:
    if args.pdf_document_id:
        return f"pdf_document_id={args.pdf_document_id}"
    if args.limit:
        return f"limit={args.limit}, all={args.all}, include_skipped={args.include_skipped}"
    return f"all={args.all}, include_skipped={args.include_skipped}"


def load_jobs(connection: sqlite3.Connection, args: argparse.Namespace) -> list[PdfJob]:
    query = """
        SELECT pd.pdf_document_id,
               pd.asset_id,
               pd.filegroup_id,
               fg.test_code,
               fg.title,
               a.folder_path,
               a.filename,
               a.local_path
          FROM pdf_documents pd
          JOIN assets a ON a.asset_id = pd.asset_id
          JOIN filegroups fg ON fg.filegroup_id = pd.filegroup_id
    """
    clauses = []
    params: list[Any] = []

    if args.pdf_document_id:
        clauses.append("pd.pdf_document_id = ?")
        params.append(args.pdf_document_id)
    elif not args.all:
        clauses.append("pd.extraction_status IN ('pending', 'error')")
    elif not args.include_skipped:
        clauses.append("pd.extraction_status <> 'skipped'")

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY pd.pdf_document_id"
    if args.limit:
        query += " LIMIT ?"
        params.append(args.limit)

    rows = connection.execute(query, params).fetchall()
    return [PdfJob(**dict(row)) for row in rows]


def clean_for_signature(value: str) -> str:
    value = normalize_text(value).lower()
    value = re.sub(r"[^a-z0-9\s:/-]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def build_fingerprint(job: PdfJob, metadata: dict[str, Any], first_page_text: str, second_page_text: str, page_count: int, first_page_size: tuple[float, float], table_count_page1: int) -> tuple[str, dict[str, Any]]:
    lines = nonempty_lines(first_page_text)[:8]
    normalized_lines = [clean_for_signature(line) for line in lines]
    fingerprint = {
        "folder_path": job.folder_path,
        "filename": job.filename,
        "page_count": page_count,
        "page_width": round(first_page_size[0], 2),
        "page_height": round(first_page_size[1], 2),
        "table_count_page1": table_count_page1,
        "top_lines": lines,
        "normalized_top_lines": normalized_lines,
        "first_page_excerpt": normalize_text(first_page_text)[:1200],
        "second_page_excerpt": normalize_text(second_page_text)[:600],
        "pdf_metadata": metadata,
    }
    signature_basis = "|".join([job.folder_path, str(page_count), *normalized_lines[:5]])
    signature_hash = hashlib.sha256(signature_basis.encode("utf-8")).hexdigest()
    return signature_hash, fingerprint


def classify_pdf(job: PdfJob, first_page_text: str, second_page_text: str, page_count: int, fingerprint: dict[str, Any]) -> tuple[str, float, str, str]:
    text = f"{first_page_text}\n{second_page_text}".lower()
    lines = [line.lower() for line in fingerprint.get("top_lines", [])]
    is_report_folder = job.folder_path.upper().endswith("REPORTS")
    is_edr_folder = job.folder_path.upper().endswith("DATA\\EDR")

    if is_report_folder:
        if ("crashworthiness evaluation crash test report" in text) or (
            "crashworthiness evaluation" in text and "crash test report" in text
        ) or (
            any("crashworthiness evaluation" in line for line in lines)
            and any("crash test report" in line for line in lines)
        ):
            return "report_legacy_crashworthiness", 0.99, "rule:legacy_heading", "Legacy crashworthiness heading matched."
        if ("crashworthiness evaluation" in text and "small overlap front test" in text) or (
            any("crashworthiness evaluation" in line for line in lines)
            and any("small overlap front test" in line for line in lines)
        ):
            version_match = re.search(r"small overlap crash test protocol,\s*version\s*([0-9.]+)", text)
            version = version_match.group(1) if version_match else ""
            if version.startswith("8"):
                return "report_modern_small_overlap_v8", 0.99, "rule:protocol_version", "Modern small-overlap template with protocol version 8."
            if version.startswith("7"):
                return "report_modern_small_overlap_v7", 0.99, "rule:protocol_version", "Modern small-overlap template with protocol version 7."
            return "report_iihs_generic", 0.85, "rule:report_branding", "IIHS-branded report matched without a known protocol version."
        if "insurance institute for highway safety" in text:
            return "report_iihs_generic", 0.7, "rule:report_branding", "IIHS-branded report matched generic report fallback."

    if is_edr_folder:
        if "restraint control module analysis" in text:
            return "edr_restraint_control_module", 0.98, "rule:rcm_heading", "Legacy restraint control module analysis heading matched."
        if "robert bosch llc" in text and "crash data retrieval" in text:
            return "edr_bosch_cdr", 0.99, "rule:bosch_notice", "Bosch CDR notice matched."
        if "g-edr software version" in text or "vehicle information hy |" in text:
            return "edr_hyundai_g_edr", 0.99, "rule:hyundai_gedr", "Hyundai G-EDR heading matched."
        if "event data recorder" in text or "airbag system" in text:
            return "edr_generic", 0.75, "rule:edr_generic", "EDR-like first-page text matched generic fallback."

    if page_count >= 8 and "insurance institute for highway safety" in text:
        return "report_iihs_generic", 0.55, "heuristic:page_count_brand", "Generic IIHS report heuristic matched."
    if is_edr_folder:
        return "edr_generic", 0.4, "heuristic:folder_path", "Generic EDR fallback from folder path."

    return "pdf_unknown", 0.1, "fallback:unknown", f"No known rule matched. Signature={fingerprint['normalized_top_lines'][:3]}"


def extract_tables(page: pdfplumber.page.Page) -> list[list[list[str | None]]]:
    candidates = []
    settings_list = [
        {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
        },
        {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "text_x_tolerance": 2,
            "text_y_tolerance": 2,
        },
    ]
    for settings in settings_list:
        try:
            tables = page.extract_tables(settings)
        except Exception:
            tables = []
        score = 0
        cleaned_tables = []
        for table in tables or []:
            if not table:
                continue
            row_count = len(table)
            col_count = max((len(row) for row in table), default=0)
            nonempty = sum(1 for row in table for cell in row if normalize_text(cell or ""))
            if row_count < 2 or col_count < 2:
                continue
            if col_count > 12:
                continue
            cleaned_tables.append(table)
            score += nonempty
        candidates.append((score, cleaned_tables))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1] if candidates else []


def render_preview(pdf_path: Path, pdf_document_id: int) -> str | None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    prefix = PREVIEW_DIR / f"pdf-{pdf_document_id}-p1"
    png_path = prefix.with_suffix(".png")
    command = [
        "pdftoppm",
        "-f",
        "1",
        "-singlefile",
        "-png",
        str(pdf_path),
        str(prefix),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not png_path.exists():
        return None
    return str(png_path)


def parse_numeric(value: str) -> float | None:
    cleaned = value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_version_number(value: str) -> float | None:
    numeric = parse_numeric(value)
    if numeric is not None:
        return numeric
    return ROMAN_NUMERAL_VALUES.get(value.strip().upper())


def find_line_value(lines: list[str], patterns: list[str]) -> str | None:
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if match:
                return normalize_text(match.group(1))
    return None


def find_line_with_test_code(lines: list[str], test_code: str) -> str | None:
    code = test_code.lower()
    for line in lines:
        if code in line.lower():
            return line
    return None


def infer_test_side(job: PdfJob, text: str) -> str | None:
    lowered = text.lower()
    path_lower = job.local_path.lower()
    if "passenger side small overlap" in lowered or "passenger-side" in lowered or "small-overlap-passenger-side" in path_lower:
        return "passenger"
    if "driver side small overlap" in lowered or "driver-side" in lowered or "small-overlap-driver-side" in path_lower:
        return "driver"
    return None


def numbers_before_parenthetical(value: str) -> list[float]:
    prefix = value.split("(")[0]
    numbers = []
    for token in re.findall(r"[0-9][0-9,]*(?:\.[0-9]+)?", prefix):
        numeric = parse_numeric(token)
        if numeric is not None:
            numbers.append(numeric)
    return numbers


def numbers_in_text(value: str) -> list[float]:
    numbers = []
    for token in re.findall(r"[0-9][0-9,]*(?:\.[0-9]+)?", value):
        numeric = parse_numeric(token)
        if numeric is not None:
            numbers.append(numeric)
    return numbers


def append_metric(
    metrics: list[tuple[Any, ...]],
    job: PdfJob,
    source_type: str,
    source_locator: str,
    namespace: str,
    metric_name: str,
    metric_value_text: str | None,
    metric_value_number: float | None,
    metric_unit: str | None,
    confidence: float,
    extraction_method: str,
) -> None:
    metrics.append(
        metric_row(
            job,
            source_type,
            source_locator,
            namespace,
            metric_name,
            metric_value_text,
            metric_value_number,
            metric_unit,
            confidence,
            extraction_method,
        )
    )


def metric_row(job: PdfJob, source_type: str, source_locator: str, namespace: str, metric_name: str, metric_value_text: str | None, metric_value_number: float | None, metric_unit: str | None, confidence: float, extraction_method: str) -> tuple[Any, ...]:
    return (
        job.filegroup_id,
        job.asset_id,
        source_type,
        source_locator,
        namespace,
        metric_name,
        metric_value_text,
        metric_value_number,
        metric_unit,
        confidence,
        extraction_method,
    )


def extract_report_dimension_metrics(job: PdfJob, metrics: list[tuple[Any, ...]], lines: list[str]) -> None:
    section_mode: str | None = None
    for line in lines:
        lowered = line.lower()
        if lowered.startswith("vehicle specifications (provided by manufacturer)"):
            section_mode = "manufacturer"
            continue
        if lowered.startswith("vehicle specifications (measured)"):
            section_mode = "measured"
            continue
        if lowered.startswith("vehicle specifications provided by manufacturer measured") or lowered.startswith("provided by manufacturer measured"):
            section_mode = "dual"
            continue
        if lowered == "vehicle specifications":
            continue
        if lowered.startswith("test protocol") or lowered.startswith("test protocols") or lowered.startswith("nominal test parameters"):
            section_mode = None

        metric_base = None
        unit = None
        if lowered.startswith("wheelbase"):
            metric_base = "wheelbase"
            unit = REPORT_DIMENSION_FIELDS[metric_base]
        elif lowered.startswith("overall length"):
            metric_base = "overall_length"
            unit = REPORT_DIMENSION_FIELDS[metric_base]
        elif lowered.startswith("overall width"):
            metric_base = "overall_width"
            unit = REPORT_DIMENSION_FIELDS[metric_base]
        elif lowered.startswith("curb weight"):
            metric_base = "curb_weight"
            unit = REPORT_DIMENSION_FIELDS[metric_base]
        elif lowered.startswith("test weight"):
            metric_base = "test_weight"
            unit = REPORT_DIMENSION_FIELDS[metric_base]

        if not metric_base:
            continue

        values = numbers_in_text(line)
        if not values:
            continue

        manufacturer_value = None
        measured_value = None
        if section_mode == "manufacturer":
            manufacturer_value = values[0]
        elif section_mode == "measured":
            measured_value = values[0]
        else:
            if metric_base == "test_weight":
                measured_value = values[0]
            else:
                manufacturer_value = values[0]
                if len(values) > 1:
                    measured_value = values[1]

        if manufacturer_value is not None:
            append_metric(
                metrics,
                job,
                "pdf_report",
                "page:1",
                "report",
                f"{metric_base}_{unit}_manufacturer",
                f"{manufacturer_value:g}",
                manufacturer_value,
                unit,
                0.92,
                "line:vehicle_specs",
            )
        if measured_value is not None:
            append_metric(
                metrics,
                job,
                "pdf_report",
                "page:1",
                "report",
                f"{metric_base}_{unit}_measured",
                f"{measured_value:g}",
                measured_value,
                unit,
                0.92,
                "line:vehicle_specs",
            )


def extract_common_report_metrics(job: PdfJob, family_key: str, text: str) -> list[tuple[Any, ...]]:
    lines = nonempty_lines(text)
    metrics: list[tuple[Any, ...]] = []
    append_metric(metrics, job, "pdf_report", "page:1", "document", "layout_family", family_key, None, None, 1.0, "classifier")

    title_line = find_line_with_test_code(lines, job.test_code)
    if title_line:
        append_metric(metrics, job, "pdf_report", "page:1", "report", "vehicle_title", title_line, None, None, 0.9, "line:test_code")

    tested_on = find_line_value(
        lines,
        [
            r"^Crash Test Date:\s*(.+)$",
            r"^Tested on\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})$",
        ],
    )
    if tested_on:
        append_metric(metrics, job, "pdf_report", "page:1", "report", "tested_on", tested_on, None, None, 0.95, "line:test_date")

    vin = find_line_value(
        lines,
        [
            r"^Vehicle identification number[:\s]+([A-HJ-NPR-Z0-9]{17})$",
            r"^Vehicle identification number\s+([A-HJ-NPR-Z0-9]{17})$",
        ],
    )
    if vin:
        append_metric(metrics, job, "pdf_report", "page:1", "document", "vehicle_identification_number", vin, None, None, 0.98, "line:vin")

    body_type = find_line_value(
        lines,
        [
            r"^Vehicle class/body type\s+(.+)$",
            r"^Vehicle class \| Body style:\s*(.+)$",
            r"^Body style:\s*(.+)$",
        ],
    )
    if body_type:
        append_metric(metrics, job, "pdf_report", "page:1", "report", "body_type", body_type, None, None, 0.88, "line:body_type")

    engine_transmission = find_line_value(
        lines,
        [
            r"^Engine/transmission:\s*(.+)$",
            r"^Engine & transmission\s+(.+)$",
        ],
    )
    if engine_transmission:
        append_metric(
            metrics,
            job,
            "pdf_report",
            "page:1",
            "report",
            "engine_transmission",
            engine_transmission,
            None,
            None,
            0.88,
            "line:engine_transmission",
        )

    protocol_text = find_line_value(lines, [r"^Test Protocol(?:s)?[:\s]+(.+)$"])
    if protocol_text:
        append_metric(metrics, job, "pdf_report", "page:1", "report", "test_protocol", protocol_text, None, None, 0.94, "line:test_protocol")
        version_match = re.search(r"Version\s+([A-Za-z0-9.]+)", protocol_text, flags=re.IGNORECASE)
        if version_match:
            version_text = normalize_text(version_match.group(1))
            append_metric(
                metrics,
                job,
                "pdf_report",
                "page:1",
                "report",
                "test_protocol_version",
                version_text,
                parse_version_number(version_text),
                None,
                0.94,
                "line:test_protocol",
            )

    speed_line = next((line for line in lines if line.lower().startswith("speed ")), None)
    if speed_line:
        speed_values = numbers_in_text(speed_line)
        if speed_values:
            append_metric(metrics, job, "pdf_report", "page:1", "report", "speed_target_kmh", f"{speed_values[0]:g}", speed_values[0], "km/h", 0.93, "line:speed")
        if len(speed_values) > 1:
            append_metric(metrics, job, "pdf_report", "page:1", "report", "speed_actual_kmh", f"{speed_values[1]:g}", speed_values[1], "km/h", 0.93, "line:speed")

    overlap_line = next((line for line in lines if line.lower().startswith("overlap")), None)
    if overlap_line:
        overlap_values = numbers_in_text(overlap_line)
        if overlap_values:
            append_metric(metrics, job, "pdf_report", "page:1", "report", "overlap_target_pct", f"{overlap_values[0]:g}", overlap_values[0], "%", 0.93, "line:overlap")
        if len(overlap_values) > 1:
            append_metric(metrics, job, "pdf_report", "page:1", "report", "overlap_actual_pct", f"{overlap_values[1]:g}", overlap_values[1], "%", 0.93, "line:overlap")

    nominal_line = next((line for line in lines if line.lower().startswith("nominal test parameters:")), None)
    if nominal_line and not speed_line:
        match = re.search(r"([0-9.]+)\s*km/h,\s*([0-9.]+)\s*%\s*overlap", nominal_line, flags=re.IGNORECASE)
        if match:
            speed_target = parse_numeric(match.group(1))
            overlap_target = parse_numeric(match.group(2))
            if speed_target is not None:
                append_metric(metrics, job, "pdf_report", "page:1", "report", "speed_target_kmh", f"{speed_target:g}", speed_target, "km/h", 0.9, "line:nominal_parameters")
            if overlap_target is not None:
                append_metric(metrics, job, "pdf_report", "page:1", "report", "overlap_target_pct", f"{overlap_target:g}", overlap_target, "%", 0.9, "line:nominal_parameters")

    legacy_nominal_line = next((line for line in lines if line.lower().startswith("small overlap @")), None)
    if legacy_nominal_line:
        match = re.search(r"@\s*([0-9.]+)\s*km/h\s*\((\d+(?:\.\d+)?)%\s*overlap", legacy_nominal_line, flags=re.IGNORECASE)
        if match:
            speed_target = parse_numeric(match.group(1))
            overlap_target = parse_numeric(match.group(2))
            if speed_target is not None:
                append_metric(metrics, job, "pdf_report", "page:1", "report", "speed_target_kmh", f"{speed_target:g}", speed_target, "km/h", 0.9, "line:legacy_nominal")
            if overlap_target is not None:
                append_metric(metrics, job, "pdf_report", "page:1", "report", "overlap_target_pct", f"{overlap_target:g}", overlap_target, "%", 0.9, "line:legacy_nominal")

    side = infer_test_side(job, text)
    if side:
        append_metric(metrics, job, "pdf_report", "page:1", "report", "test_side", side, None, None, 0.98, "rule:test_side")

    extract_report_dimension_metrics(job, metrics, lines)
    return metrics


def extract_bosch_metrics(job: PdfJob, family_key: str, full_text: str) -> list[tuple[Any, ...]]:
    lines = nonempty_lines(full_text)
    metrics: list[tuple[Any, ...]] = []
    append_metric(metrics, job, "pdf_edr", "page:1", "document", "layout_family", family_key, None, None, 1.0, "classifier")
    append_metric(metrics, job, "pdf_edr", "page:1", "edr", "vendor", "Robert Bosch LLC", None, None, 0.99, "rule:bosch_notice")

    vin = find_line_value(lines, [r"^User Entered VIN\s+([A-HJ-NPR-Z0-9]{17})$"])
    if vin:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "vehicle_identification_number", vin, None, None, 0.95, "line:vin")

    case_number = find_line_value(lines, [r"^Case Number\s+(.+)$"])
    if case_number:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "case_number", case_number, None, None, 0.9, "line:case_number")

    crash_date = find_line_value(lines, [r"^Crash Date\s+(.+)$"])
    if crash_date:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "crash_date", crash_date, None, None, 0.88, "line:crash_date")

    saved_on = find_line_value(lines, [r"^Saved on\s+(.+)$"])
    if saved_on:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "saved_on", saved_on, None, None, 0.88, "line:saved_on")

    cdr_version = find_line_value(
        lines,
        [
            r"^Reported with CDR version\s+(.+)$",
            r"^Collected with CDR version\s+(.+)$",
        ],
    )
    if cdr_version:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "cdr_software_version", cdr_version, None, None, 0.9, "line:cdr_version")

    device_type = find_line_value(lines, [r"^EDR Device Type\s+(.+)$"])
    if device_type:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "device_type", device_type, None, None, 0.86, "line:device_type")

    return metrics


def extract_hyundai_metrics(job: PdfJob, family_key: str, full_text: str) -> list[tuple[Any, ...]]:
    lines = nonempty_lines(full_text)
    metrics: list[tuple[Any, ...]] = []
    append_metric(metrics, job, "pdf_edr", "page:1", "document", "layout_family", family_key, None, None, 1.0, "classifier")
    append_metric(metrics, job, "pdf_edr", "page:1", "edr", "vendor_family", "Hyundai G-EDR", None, None, 0.99, "rule:gedr")

    vehicle_info = re.search(
        r"Vehicle Information\s+([A-Z]{2})\s*\|\s*([A-Za-z0-9\-\(\) ]+)\s*\|\s*(\d{4})\s*\|\s*([A-Za-z ]+)",
        full_text,
        flags=re.IGNORECASE,
    )
    if vehicle_info:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "vehicle_platform_code", vehicle_info.group(1), None, None, 0.9, "regex:vehicle_info")
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "vehicle_model", normalize_text(vehicle_info.group(2)), None, None, 0.9, "regex:vehicle_info")
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "vehicle_year", vehicle_info.group(3), float(vehicle_info.group(3)), None, 0.9, "regex:vehicle_info")
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "device_type", normalize_text(vehicle_info.group(4)), None, None, 0.85, "regex:vehicle_info")

    case_number = find_line_value(lines, [r"^CaseNumber\s*:\s*(.+)$"])
    if case_number:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "case_number", case_number, None, None, 0.9, "line:case_number")

    crash_date = find_line_value(lines, [r"^CrashDate\s*:\s*(.+)$"])
    if crash_date:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "crash_date", crash_date, None, None, 0.88, "line:crash_date")

    part_number = find_line_value(lines, [r"^Part No\.\s*:\s*(.+)$"])
    if part_number:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "part_number", part_number, None, None, 0.88, "line:part_number")

    save_on = find_line_value(lines, [r"^Save on\s*:\s*(.+)$"])
    if save_on:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "saved_on", save_on, None, None, 0.88, "line:saved_on")

    version_text = find_line_value(lines, [r"^G-EDR Software Version\s*:\s*(.+)$"])
    if version_text:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "gedr_software_version", version_text, None, None, 0.9, "line:gedr_version")

    return metrics


def extract_restraint_metrics(job: PdfJob, family_key: str, full_text: str) -> list[tuple[Any, ...]]:
    lines = nonempty_lines(full_text)
    metrics: list[tuple[Any, ...]] = []
    append_metric(metrics, job, "pdf_edr", "page:1", "document", "layout_family", family_key, None, None, 1.0, "classifier")
    append_metric(metrics, job, "pdf_edr", "page:1", "edr", "vendor_family", "Restraint Control Module", None, None, 0.98, "rule:rcm_heading")

    report_date = find_line_value(lines, [r"REPORT DATE\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})"])
    if report_date:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "report_date", report_date, None, None, 0.85, "line:report_date")

    build_date = find_line_value(lines, [r"BUILD DATE\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})"])
    if build_date:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "build_date", build_date, None, None, 0.85, "line:build_date")

    part_number = find_line_value(lines, [r"PART #\s+([A-Za-z0-9\-]+)"])
    if part_number:
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "part_number", part_number, None, None, 0.88, "line:part_number")

    vin = find_line_value(lines, [r"VIN\s+([A-HJ-NPR-Z0-9]{17}|Data not supplied)"])
    if vin and vin.lower() != "data not supplied":
        append_metric(metrics, job, "pdf_edr", "page:1", "edr", "vehicle_identification_number", vin, None, None, 0.8, "line:vin")

    return metrics


def extract_metrics(job: PdfJob, family_key: str, first_page_text: str, second_page_text: str, full_text: str, page_count: int, confidence: float) -> list[tuple[Any, ...]]:
    metrics = [
        metric_row(job, "pdf_document", "document", "document", "page_count", str(page_count), float(page_count), "pages", 1.0, "reader"),
        metric_row(job, "pdf_document", "document", "document", "classification_confidence", f"{confidence:.3f}", confidence, None, 1.0, "classifier"),
    ]
    if family_key.startswith("report_"):
        metrics.extend(extract_common_report_metrics(job, family_key, first_page_text))
    elif family_key == "edr_bosch_cdr":
        metrics.extend(extract_bosch_metrics(job, family_key, full_text))
    elif family_key == "edr_hyundai_g_edr":
        metrics.extend(extract_hyundai_metrics(job, family_key, full_text))
    elif family_key == "edr_restraint_control_module":
        metrics.extend(extract_restraint_metrics(job, family_key, full_text))
    else:
        metrics.append(metric_row(job, "pdf_document", "page:1", "document", "layout_family", family_key, None, None, 0.5, "classifier"))
    return metrics


def raw_nonempty_lines(value: str) -> list[str]:
    return [line.rstrip() for line in (value or "").splitlines() if normalize_text(line)]


def normalize_numeric_text(value: str | None) -> str:
    return normalize_text(value or "").replace("−", "-").replace("–", "-").replace("—", "-").replace("º", "°")


def compact_numeric_token(value: str | None) -> str:
    text = normalize_numeric_text(value)
    text = text.replace(" ", "").replace("°", "").replace("*", "")
    if text.startswith("±"):
        text = text[1:]
    return text.lower()


def looks_like_result_value(value: str | None) -> bool:
    token = compact_numeric_token(value)
    if not token:
        return False
    if token in {"--", "n/a", "na"}:
        return True
    return bool(re.fullmatch(r"-?\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?", token))


def looks_like_time_value(value: str | None) -> bool:
    token = compact_numeric_token(value)
    if not token:
        return False
    if token == "--":
        return True
    return bool(re.fullmatch(r"\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?", token))


def parse_numericish_value(value: str | None) -> float | None:
    token = compact_numeric_token(value)
    if not token or token in {"--", "n/a", "na"}:
        return None
    range_match = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)", token)
    if range_match:
        return (float(range_match.group(1)) + float(range_match.group(2))) / 2.0
    try:
        return float(token)
    except ValueError:
        return None


def split_columns(line: str) -> list[str]:
    return [normalize_text(part) for part in re.split(r"\s{2,}", line.strip()) if normalize_text(part)]


def extract_unit_from_label(label: str, fallback_unit: str | None = None) -> str | None:
    match = re.search(r"\(([^)]+)\)\s*$", normalize_text(label))
    if match:
        return normalize_text(match.group(1))
    return fallback_unit


def is_footer_line(line: str) -> bool:
    lowered = clean_for_signature(line)
    return (
        "insurance institute for highway safety" in lowered
        or "iihsorg" in lowered
        or "all rights reserved" in lowered
        or lowered.startswith("1005 n glebe road")
        or lowered.startswith("988 dairy road")
    )


def is_note_line(line: str) -> bool:
    normalized = normalize_numeric_text(line)
    return normalized.startswith("*") or normalized.lower().startswith("all distance measurements")


def classify_result_table(title: str) -> tuple[str, str] | None:
    signature = clean_for_signature(title)
    for table_type, table_group, needle in RESULT_TABLE_PATTERNS:
        if needle in signature:
            return table_type, table_group
    return None


RESULT_ROW_FIELDS = [
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
    "threshold_number",
    "result_text",
    "result_number",
    "time_text",
    "time_number",
    "left_text",
    "left_number",
    "left_time_text",
    "left_time_number",
    "right_text",
    "right_number",
    "right_time_text",
    "right_time_number",
    "longitudinal_text",
    "longitudinal_number",
    "lateral_text",
    "lateral_number",
    "vertical_text",
    "vertical_number",
    "resultant_text",
    "resultant_number",
    "measure_text",
    "measure_number",
    "raw_row_json",
]


def make_result_row(**kwargs: Any) -> dict[str, Any]:
    row = {field: None for field in RESULT_ROW_FIELDS}
    row.update(kwargs)
    return row


def split_result_sections(text: str) -> list[dict[str, Any]]:
    lines = raw_nonempty_lines(text)
    sections: list[dict[str, Any]] = []
    current_lines: list[str] = []

    for line in lines:
        normalized = normalize_text(line)
        if TABLE_START_RE.match(normalized):
            if current_lines:
                sections.append({"lines": current_lines})
            current_lines = [line]
        elif current_lines:
            current_lines.append(line)

    if current_lines:
        sections.append({"lines": current_lines})

    if not sections and lines:
        first_line = normalize_text(lines[0])
        if classify_result_table(first_line):
            sections.append({"lines": lines, "fallback_ref": "Attachment 1"})

    finalized: list[dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        section_lines = section["lines"]
        first_line = normalize_text(section_lines[0])
        match = TABLE_START_RE.match(first_line)
        table_ref = None
        remainder = ""
        if match:
            table_ref = f"{match.group(1).title()} {match.group(2)}"
            remainder = normalize_text(match.group(3))
        else:
            table_ref = section.get("fallback_ref")

        body_start = 1
        if remainder:
            title = remainder
        elif match and len(section_lines) > 1:
            title = normalize_text(section_lines[1])
            body_start = 2
        else:
            title = normalize_text(section_lines[0])

        full_title = f"{table_ref} {title}".strip() if table_ref and title and title != table_ref else (title or table_ref or "")
        finalized.append(
            {
                "table_order": index,
                "table_ref": table_ref,
                "title": title,
                "full_title": full_title,
                "lines": section_lines,
                "body_lines": section_lines[body_start:],
            }
        )

    return finalized


def parse_single_result_line(line: str) -> tuple[str, str | None, str, str] | None:
    columns = split_columns(line)
    if len(columns) >= 4 and looks_like_result_value(columns[-1]) and looks_like_result_value(columns[-2]) and looks_like_result_value(columns[-3]):
        return " ".join(columns[:-3]), columns[-3], columns[-2], columns[-1]
    if len(columns) >= 3 and looks_like_result_value(columns[-1]) and looks_like_result_value(columns[-2]):
        return " ".join(columns[:-2]), None, columns[-2], columns[-1]

    normalized = normalize_numeric_text(line)
    pattern_with_threshold = re.compile(
        rf"^(?P<label>.+?)\s+(?P<threshold>{RESULT_VALUE_PATTERN})\s+(?P<result>{RESULT_VALUE_PATTERN})\s+(?P<time>{TIME_VALUE_PATTERN})$",
        flags=re.IGNORECASE,
    )
    match = pattern_with_threshold.match(normalized)
    if match:
        return (
            normalize_text(match.group("label")),
            normalize_text(match.group("threshold")),
            normalize_text(match.group("result")),
            normalize_text(match.group("time")),
        )

    pattern_without_threshold = re.compile(
        rf"^(?P<label>.+?)\s+(?P<result>{RESULT_VALUE_PATTERN})\s+(?P<time>{TIME_VALUE_PATTERN})$",
        flags=re.IGNORECASE,
    )
    match = pattern_without_threshold.match(normalized)
    if match:
        return (
            normalize_text(match.group("label")),
            None,
            normalize_text(match.group("result")),
            normalize_text(match.group("time")),
        )
    return None


def parse_single_result_table(lines: list[str], fallback_unit: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    rows: list[dict[str, Any]] = []
    header_found = False
    notes: list[str] = []
    for raw_line in lines:
        line = normalize_text(raw_line)
        if not line:
            continue
        if is_footer_line(line):
            break
        if is_note_line(line):
            notes.append(line)
            continue
        lowered = line.lower()
        if lowered == "published" or lowered == "tolerance":
            continue
        if lowered.startswith("measure") and "result" in lowered:
            header_found = True
            continue
        if not header_found:
            continue
        if line == "ij" and rows:
            if rows[-1]["label"] and rows[-1]["label"].startswith("N "):
                rows[-1]["label"] = rows[-1]["label"].replace("N ", "Nij ", 1)
            elif rows[-1]["label"]:
                rows[-1]["label"] = f"{rows[-1]['label']} ij"
            continue

        parsed = parse_single_result_line(raw_line)
        if parsed:
            label, threshold_text, result_text, time_text = parsed
            unit = extract_unit_from_label(label, fallback_unit)
            rows.append(
                make_result_row(
                    label=label,
                    unit=unit,
                    threshold_text=threshold_text,
                    threshold_number=parse_numericish_value(threshold_text),
                    result_text=result_text,
                    result_number=parse_numericish_value(result_text),
                    time_text=time_text,
                    time_number=parse_numericish_value(time_text),
                    raw_row_json=json.dumps({"line": line}, ensure_ascii=False),
                )
            )
        elif rows:
            rows[-1]["label"] = normalize_text(f"{rows[-1]['label']} {line}")
            rows[-1]["raw_row_json"] = json.dumps({"line": line, "continued": True}, ensure_ascii=False)

    return rows, {"notes": notes} if notes else {}, ["Measure", "Threshold", "Result", "Time (ms)"]


def parse_intrusion_line(line: str) -> tuple[str, str | None, str | None, str | None, str | None] | None:
    columns = split_columns(line)
    if len(columns) >= 5 and all(looks_like_result_value(value) for value in columns[-4:]):
        return " ".join(columns[:-4]), columns[-4], columns[-3], columns[-2], columns[-1]
    if len(columns) == 2 and looks_like_result_value(columns[1]):
        label = columns[0]
        lowered = label.lower()
        if "average lateral" in lowered:
            return label, None, columns[1], None, None
        if "max resultant" in lowered:
            return label, None, None, None, columns[1]
    normalized = normalize_numeric_text(line)
    pattern = re.compile(
        rf"^(?P<label>.+?)\s+(?P<longitudinal>{RESULT_VALUE_PATTERN})\s+(?P<lateral>{RESULT_VALUE_PATTERN})\s+(?P<vertical>{RESULT_VALUE_PATTERN})\s+(?P<resultant>{RESULT_VALUE_PATTERN})$",
        flags=re.IGNORECASE,
    )
    match = pattern.match(normalized)
    if match:
        return (
            normalize_text(match.group("label")),
            normalize_text(match.group("longitudinal")),
            normalize_text(match.group("lateral")),
            normalize_text(match.group("vertical")),
            normalize_text(match.group("resultant")),
        )
    return None


def parse_intrusion_table(lines: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    rows: list[dict[str, Any]] = []
    header_found = False
    notes: list[str] = []
    for raw_line in lines:
        line = normalize_text(raw_line)
        if not line:
            continue
        if is_footer_line(line):
            break
        if is_note_line(line):
            notes.append(line)
            continue
        lowered = line.lower()
        if lowered.startswith("selected locations"):
            header_found = True
            continue
        if not header_found:
            continue
        parsed = parse_intrusion_line(raw_line)
        if parsed:
            label, longitudinal, lateral, vertical, resultant = parsed
            rows.append(
                make_result_row(
                    label=label,
                    unit="cm",
                    longitudinal_text=longitudinal,
                    longitudinal_number=parse_numericish_value(longitudinal),
                    lateral_text=lateral,
                    lateral_number=parse_numericish_value(lateral),
                    vertical_text=vertical,
                    vertical_number=parse_numericish_value(vertical),
                    resultant_text=resultant,
                    resultant_number=parse_numericish_value(resultant),
                    raw_row_json=json.dumps({"line": line}, ensure_ascii=False),
                )
            )
        elif rows:
            rows[-1]["label"] = normalize_text(f"{rows[-1]['label']} {line}")
            rows[-1]["raw_row_json"] = json.dumps({"line": line, "continued": True}, ensure_ascii=False)
    return rows, {"notes": notes} if notes else {}, ["Location", "Longitudinal", "Lateral", "Vertical", "Resultant"]


def parse_dual_side_threshold_line(line: str) -> tuple[str, str | None, str, str | None, str, str | None] | None:
    columns = split_columns(line)
    if len(columns) >= 6:
        candidate = columns[-5:]
        if all(looks_like_result_value(value) or looks_like_time_value(value) for value in candidate):
            return " ".join(columns[:-5]), candidate[0], candidate[1], candidate[2], candidate[3], candidate[4]
    normalized = normalize_numeric_text(line)
    pattern = re.compile(
        rf"^(?P<label>.+?)\s+(?P<threshold>{RESULT_VALUE_PATTERN})\s+(?P<left>{RESULT_VALUE_PATTERN})\s+(?P<left_time>{TIME_VALUE_PATTERN})\s+(?P<right>{RESULT_VALUE_PATTERN})\s+(?P<right_time>{TIME_VALUE_PATTERN})$",
        flags=re.IGNORECASE,
    )
    match = pattern.match(normalized)
    if match:
        return (
            normalize_text(match.group("label")),
            normalize_text(match.group("threshold")),
            normalize_text(match.group("left")),
            normalize_text(match.group("left_time")),
            normalize_text(match.group("right")),
            normalize_text(match.group("right_time")),
        )
    return None


def parse_dual_side_no_threshold_line(line: str) -> tuple[str, str, str | None, str, str | None] | None:
    columns = split_columns(line)
    if len(columns) >= 5:
        return " ".join(columns[:-4]), columns[-4], columns[-3], columns[-2], columns[-1]
    normalized = normalize_numeric_text(line)
    pattern = re.compile(
        rf"^(?P<label>.+?)\s+(?P<left>\S+)\s+(?P<left_time>{TIME_VALUE_PATTERN})\s+(?P<right>\S+)\s+(?P<right_time>{TIME_VALUE_PATTERN})$",
        flags=re.IGNORECASE,
    )
    match = pattern.match(normalized)
    if match:
        return (
            normalize_text(match.group("label")),
            normalize_text(match.group("left")),
            normalize_text(match.group("left_time")),
            normalize_text(match.group("right")),
            normalize_text(match.group("right_time")),
        )
    return None


def parse_dual_side_table(lines: list[str], include_threshold: bool) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    rows: list[dict[str, Any]] = []
    header_found = False
    current_section: str | None = None
    notes: list[str] = []
    for raw_line in lines:
        line = normalize_text(raw_line)
        if not line:
            continue
        if is_footer_line(line):
            break
        if is_note_line(line):
            notes.append(line)
            continue
        lowered = line.lower()
        if lowered.startswith("published") or lowered.startswith("tolerance") or lowered.startswith("time"):
            continue
        if lowered.startswith("measure"):
            header_found = True
            continue
        if not header_found:
            continue

        parsed = parse_dual_side_threshold_line(raw_line) if include_threshold else parse_dual_side_no_threshold_line(raw_line)
        if parsed:
            if include_threshold:
                label, threshold_text, left_text, left_time_text, right_text, right_time_text = parsed
            else:
                label, left_text, left_time_text, right_text, right_time_text = parsed
                threshold_text = None
            rows.append(
                make_result_row(
                    section_name=current_section,
                    label=label,
                    unit=extract_unit_from_label(label),
                    threshold_text=threshold_text,
                    threshold_number=parse_numericish_value(threshold_text),
                    left_text=left_text,
                    left_number=parse_numericish_value(left_text),
                    left_time_text=left_time_text,
                    left_time_number=parse_numericish_value(left_time_text),
                    right_text=right_text,
                    right_number=parse_numericish_value(right_text),
                    right_time_text=right_time_text,
                    right_time_number=parse_numericish_value(right_time_text),
                    raw_row_json=json.dumps({"line": line}, ensure_ascii=False),
                )
            )
            continue

        if re.search(r"\d", compact_numeric_token(line)):
            if rows:
                rows[-1]["label"] = normalize_text(f"{rows[-1]['label']} {line}")
                rows[-1]["raw_row_json"] = json.dumps({"line": line, "continued": True}, ensure_ascii=False)
            continue

        current_section = line

    headers = ["Section", "Measure", "Threshold", "Left", "Left time", "Right", "Right time"] if include_threshold else ["Section", "Measure", "Left", "Left time", "Right", "Right time"]
    return rows, {"notes": notes} if notes else {}, headers


def parse_dummy_clearance_row(line: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"^(?P<label1>.+?)\s+(?P<code1>[A-Z]{2,4})\s+(?P<measure1>[+\-]?\d+(?:\.\d+)?°?)\s+(?P<label2>.+?)\s+(?P<code2>[A-Z]{2,4})\s+(?P<measure2>[+\-]?\d+(?:\.\d+)?°?)$"
    )
    match = pattern.match(normalize_text(line))
    if not match:
        return []

    rows = []
    for index in (1, 2):
        label = normalize_text(match.group(f"label{index}"))
        measure_text = normalize_text(match.group(f"measure{index}"))
        unit = "deg" if "°" in measure_text else "mm"
        rows.append(
            make_result_row(
                label=label,
                code=normalize_text(match.group(f"code{index}")),
                unit=unit,
                measure_text=measure_text,
                measure_number=parse_numericish_value(measure_text),
                raw_row_json=json.dumps({"line": normalize_text(line), "pair_index": index}, ensure_ascii=False),
            )
        )
    return rows


def parse_dummy_clearance_table(lines: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    rows: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    current_meta_key: str | None = None
    header_found = False
    notes: list[str] = []
    for raw_line in lines:
        line = normalize_text(raw_line)
        if not line:
            continue
        if is_footer_line(line):
            break
        lowered = line.lower()
        if lowered.startswith("location"):
            header_found = True
            current_meta_key = None
            continue
        if not header_found:
            if is_note_line(line):
                notes.append(line)
                continue
            meta_match = re.match(r"^(?P<key>[A-Za-z ][A-Za-z /()-]+):\s*(?P<value>.+)$", line)
            if meta_match:
                current_meta_key = clean_for_signature(meta_match.group("key")).replace(" ", "_")
                metadata[current_meta_key] = normalize_text(meta_match.group("value"))
            elif current_meta_key:
                metadata[current_meta_key] = normalize_text(f"{metadata[current_meta_key]} {line}")
            continue
        if is_note_line(line):
            notes.append(line)
            continue
        rows.extend(parse_dummy_clearance_row(line))

    if notes:
        metadata["notes"] = notes
    return rows, metadata, ["Code", "Location", "Measure"]


def parse_kinematics_line(line: str) -> tuple[str, str] | None:
    columns = split_columns(line)
    if len(columns) >= 2 and looks_like_time_value(columns[-1]):
        return " ".join(columns[:-1]), columns[-1]
    normalized = normalize_numeric_text(line)
    match = re.match(rf"^(?P<label>.+?)\s+(?P<time>{TIME_VALUE_PATTERN})$", normalized, flags=re.IGNORECASE)
    if match:
        return normalize_text(match.group("label")), normalize_text(match.group("time"))
    return None


def parse_kinematics_table(lines: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    rows: list[dict[str, Any]] = []
    header_found = False
    notes: list[str] = []
    for raw_line in lines:
        line = normalize_text(raw_line)
        if not line:
            continue
        if is_footer_line(line):
            break
        if is_note_line(line):
            notes.append(line)
            continue
        if line.lower().startswith("event"):
            header_found = True
            continue
        if not header_found:
            continue
        parsed = parse_kinematics_line(raw_line)
        if parsed:
            label, time_text = parsed
            rows.append(
                make_result_row(
                    label=label,
                    unit="ms",
                    time_text=time_text,
                    time_number=parse_numericish_value(time_text),
                    raw_row_json=json.dumps({"line": line}, ensure_ascii=False),
                )
            )
        elif rows:
            rows[-1]["label"] = normalize_text(f"{rows[-1]['label']} {line}")
            rows[-1]["raw_row_json"] = json.dumps({"line": line, "continued": True}, ensure_ascii=False)
    return rows, {"notes": notes} if notes else {}, ["Event", "Time (ms)"]


def clean_result_label(value: str | None) -> str:
    text = normalize_numeric_text(value)
    text = text.replace("\uf0d3", " ").replace("\uf6d9", " ").replace("", " ")
    replacements = {
        "Sternumdeflection": "Sternum deflection",
        "Knee-thigh-hipinjury": "Knee-thigh-hip injury",
        "Deployment ofdriver": "Deployment of driver",
        "seat beltcrash": "seat belt crash",
        "loadingfrontal": "loading frontal",
        "Rim toabdomen": "Rim to abdomen",
        "toH-point": "to H-point",
        "Head toroof": "Head to roof",
        "Head tohead": "Head to head",
        "Vector resultantmoment": "Vector resultant moment",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    for pattern, replacement in OCR_ALIAS_PATTERNS:
        text = pattern.sub(replacement, text)
    for marker in ("Insurance Institute for Highway Safety", "988 Dairy Road", "1005 N. Glebe Road"):
        position = text.find(marker)
        if position >= 0:
            text = text[:position]
    text = re.sub(r"\s+([,;:)\]])", r"\1", text)
    text = re.sub(r"([(])\s+", r"\1", text)
    text = normalize_text(text)
    match = re.match(r"^N\s+(.+?)\s+ij$", text, flags=re.IGNORECASE)
    if match:
        text = f"Nij {normalize_text(match.group(1))}"
    if re.fullmatch(r"\d{4}", text):
        return ""
    return text.strip()


def canonical_result_label(value: str | None) -> str:
    text = clean_result_label(value)
    text = text.replace("N ij", "Nij").replace("n ij", "nij")
    text = text.replace("A-P", "AP").replace("a-p", "ap")
    text = text.replace("L-M", "LM").replace("l-m", "lm")
    text = text.replace("I-S", "IS").replace("i-s", "is")
    text = re.sub(r"[–—−]", "-", text)
    text = re.sub(r"[^0-9A-Za-z]+", " ", text.lower())
    return normalize_text(text)


def preferred_summary_text(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    ranked = sorted(counts.items(), key=lambda item: (-item[1], len(item[0]), item[0].lower()))
    return ranked[0][0]


def common_measure_section(section_name: str | None, raw_payload: dict[str, Any]) -> tuple[str, str]:
    cleaned = clean_result_label(section_name or "")
    if cleaned.lower() in {"driver", "passenger"} and raw_payload.get("seat_position"):
        return "", ""
    return canonical_result_label(cleaned), cleaned


def normalize_seat_position(value: str | None) -> str | None:
    lowered = normalize_text(value or "").lower()
    return lowered if lowered in {"driver", "passenger"} else None


def assess_result_row_quality(row: dict[str, Any]) -> tuple[str, float, list[str]]:
    flags: list[str] = []
    label_text = clean_result_label(row.get("label") or row.get("code") or row.get("measure_text") or "")
    normalized_label = normalize_text(row.get("normalized_label") or "")

    if not normalized_label:
        flags.append("missing_label")
    if label_text and LABEL_NUMERIC_PREFIX_RE.search(label_text):
        flags.append("label_numeric_prefix")
    if label_text and LABEL_TABLE_PREFIX_RE.search(label_text):
        flags.append("label_table_prefix")
    if label_text and RESIDUAL_OCR_FRAGMENT_RE.search(label_text):
        flags.append("residual_ocr_fragment")

    primary_value_fields = (
        "result_text",
        "left_text",
        "right_text",
        "longitudinal_text",
        "lateral_text",
        "vertical_text",
        "resultant_text",
        "measure_text",
        "time_text",
    )
    if not any(normalize_text(row.get(field) or "") for field in primary_value_fields):
        flags.append("missing_primary_value")

    def add_numeric_flag(text_field: str, number_field: str, flag_name: str, *, time_field: bool = False) -> None:
        text_value = normalize_text(row.get(text_field) or "")
        if not text_value or text_value.lower() in {"--", "n/a", "na"}:
            return
        if row.get(number_field) is not None:
            return
        looks_numeric = looks_like_time_value(text_value) if time_field else looks_like_result_value(text_value)
        if not looks_numeric:
            flags.append(flag_name)

    add_numeric_flag("threshold_text", "threshold_number", "unparsed_threshold")
    add_numeric_flag("result_text", "result_number", "unparsed_result")
    add_numeric_flag("time_text", "time_number", "unparsed_time", time_field=True)
    add_numeric_flag("left_text", "left_number", "unparsed_left")
    add_numeric_flag("left_time_text", "left_time_number", "unparsed_left_time", time_field=True)
    add_numeric_flag("right_text", "right_number", "unparsed_right")
    add_numeric_flag("right_time_text", "right_time_number", "unparsed_right_time", time_field=True)
    add_numeric_flag("longitudinal_text", "longitudinal_number", "unparsed_longitudinal")
    add_numeric_flag("lateral_text", "lateral_number", "unparsed_lateral")
    add_numeric_flag("vertical_text", "vertical_number", "unparsed_vertical")
    add_numeric_flag("resultant_text", "resultant_number", "unparsed_resultant")
    add_numeric_flag("measure_text", "measure_number", "unparsed_measure")

    penalties = {
        "missing_label": 0.45,
        "missing_primary_value": 0.35,
        "label_numeric_prefix": 0.15,
        "label_table_prefix": 0.15,
        "residual_ocr_fragment": 0.15,
    }
    score = 1.0
    for flag in flags:
        if flag.startswith("unparsed_"):
            score -= 0.1
        else:
            score -= penalties.get(flag, 0.1)
    score = max(0.0, round(score, 3))
    status = "review" if flags else "ok"
    return status, score, sorted(set(flags))


def enrich_result_row_fields(row: dict[str, Any]) -> dict[str, Any]:
    raw_payload: dict[str, Any] = {}
    if row.get("raw_row_json"):
        try:
            raw_payload = json.loads(row["raw_row_json"])
        except json.JSONDecodeError:
            raw_payload = {}

    seat_position = normalize_seat_position(row.get("seat_position") or raw_payload.get("seat_position"))
    if seat_position:
        raw_payload["seat_position"] = seat_position
        row["raw_row_json"] = json.dumps(raw_payload, ensure_ascii=False)
    row["seat_position"] = seat_position

    label_source = clean_result_label(row.get("label") or row.get("code") or row.get("measure_text") or "")
    normalized_label = canonical_result_label(label_source)
    row["normalized_label"] = normalized_label or None

    section_key, _ = common_measure_section(row.get("section_name"), {"seat_position": seat_position})
    row["section_key"] = section_key or None
    quality_status, quality_score, quality_flags = assess_result_row_quality(row)
    row["quality_status"] = quality_status
    row["quality_score"] = quality_score
    row["quality_flags"] = json.dumps(quality_flags, ensure_ascii=False) if quality_flags else None
    return row


def join_cell_fragments(parts: list[str | None]) -> str:
    return clean_result_label(" ".join(normalize_text(part or "") for part in parts if normalize_text(part or "")))


def tail_values_from_text(text: str, counts: list[int]) -> tuple[str, list[str]] | None:
    prepared = clean_result_label(text)
    matches = list(RESULT_TOKEN_RE2.finditer(prepared))
    for count in counts:
        if len(matches) < count:
            continue
        selected = matches[-count:]
        fragments: list[str] = []
        cursor = 0
        for match in selected:
            fragments.append(prepared[cursor : match.start()])
            cursor = match.end()
        fragments.append(prepared[cursor:])
        label = clean_result_label(" ".join(fragments))
        if label:
            return label, [normalize_text(match.group(0)) for match in selected]
    return None


def is_injury_header_line(line: str) -> bool:
    lowered = clean_result_label(line).lower()
    if not lowered:
        return False
    return lowered.startswith(("published", "tolerance", "threshold", "measure", "result", "time", "driver", "passenger", "left", "right"))


def should_attach_injury_fragment(line: str) -> bool:
    if not line:
        return False
    lowered = line.lower()
    return lowered == "ij" or line.startswith("(") or line[0].islower()


def merge_fragment_before_values(record_text: str, fragment: str) -> str:
    prepared = clean_result_label(record_text)
    match = RESULT_TOKEN_RE2.search(normalize_numeric_text(prepared))
    if not match:
        return clean_result_label(f"{prepared} {fragment}")
    return clean_result_label(f"{prepared[:match.start()].rstrip()} {fragment} {prepared[match.start():].lstrip()}")


def build_injury_records(lines: list[str]) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    records: list[dict[str, Any]] = []
    header_lines: list[str] = []
    notes: list[str] = []
    current_section: str | None = None
    pending_text: str | None = None

    for raw_line in lines:
        line = clean_result_label(raw_line)
        if not line:
            continue
        if is_footer_line(line):
            break
        if is_note_line(line):
            notes.append(line)
            continue
        lowered = line.lower()
        if lowered in INJURY_SECTION_HEADERS:
            current_section = line.title() if lowered != "foot" else "Foot"
            pending_text = None
            continue
        if is_injury_header_line(line):
            header_lines.append(line)
            continue

        token_matches = list(RESULT_TOKEN_RE2.finditer(normalize_numeric_text(line)))
        fragment_with_embedded_number = should_attach_injury_fragment(line) and len(token_matches) <= 2 and not re.search(r"\s[±+\-–−]?\d", line)
        has_value = bool(token_matches) and not fragment_with_embedded_number
        if has_value:
            record_text = clean_result_label(f"{pending_text} {line}" if pending_text else line)
            pending_text = None
            records.append({"section_name": current_section, "text": record_text})
            continue

        if records and should_attach_injury_fragment(line):
            records[-1]["text"] = merge_fragment_before_values(records[-1]["text"], line)
        else:
            pending_text = clean_result_label(f"{pending_text} {line}" if pending_text else line)

    return records, header_lines, notes


def parse_injury_table(lines: list[str], table_type: str, title: str, report_test_side: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    records, header_lines, notes = build_injury_records(lines)
    header_signature = clean_for_signature(" ".join(header_lines))
    has_driver_passenger = "driver" in header_signature and "passenger" in header_signature
    has_left_right = "left" in header_signature and "right" in header_signature
    has_threshold = "threshold" in header_signature

    title_signature = clean_for_signature(title)
    default_seat = "driver" if "driver" in title_signature else "passenger" if "passenger" in title_signature else (report_test_side or None)

    rows: list[dict[str, Any]] = []
    metadata = {
        "seat_scope": "driver_passenger" if has_driver_passenger else default_seat,
        "notes": notes,
    }

    for record in records:
        section_name = record["section_name"]
        raw_text = record["text"]

        if has_driver_passenger and has_left_right:
            parsed = tail_values_from_text(raw_text, [9, 8] if has_threshold else [8])
            if not parsed:
                continue
            label, values = parsed
            threshold_text = values[0] if len(values) == 9 else None
            start = 1 if threshold_text is not None else 0
            if len(values[start:]) != 8:
                continue
            driver_left, driver_left_time, driver_right, driver_right_time, passenger_left, passenger_left_time, passenger_right, passenger_right_time = values[start:]
            for seat_position, left_text, left_time_text, right_text, right_time_text in (
                ("driver", driver_left, driver_left_time, driver_right, driver_right_time),
                ("passenger", passenger_left, passenger_left_time, passenger_right, passenger_right_time),
            ):
                rows.append(
                    make_result_row(
                        section_name=section_name,
                        label=label,
                        unit=extract_unit_from_label(label),
                        threshold_text=threshold_text,
                        threshold_number=parse_numericish_value(threshold_text),
                        left_text=left_text,
                        left_number=parse_numericish_value(left_text),
                        left_time_text=left_time_text,
                        left_time_number=parse_numericish_value(left_time_text),
                        right_text=right_text,
                        right_number=parse_numericish_value(right_text),
                        right_time_text=right_time_text,
                        right_time_number=parse_numericish_value(right_time_text),
                        raw_row_json=json.dumps({"line": raw_text, "seat_position": seat_position}, ensure_ascii=False),
                    )
                )
            continue

        if has_driver_passenger:
            parsed = tail_values_from_text(raw_text, [5, 4] if has_threshold else [4])
            if not parsed:
                continue
            label, values = parsed
            threshold_text = values[0] if len(values) == 5 else None
            start = 1 if threshold_text is not None else 0
            if len(values[start:]) != 4:
                continue
            driver_result, driver_time, passenger_result, passenger_time = values[start:]
            for seat_position, result_text, time_text in (
                ("driver", driver_result, driver_time),
                ("passenger", passenger_result, passenger_time),
            ):
                rows.append(
                    make_result_row(
                        section_name=seat_position.title(),
                        label=label,
                        unit=extract_unit_from_label(label),
                        threshold_text=threshold_text,
                        threshold_number=parse_numericish_value(threshold_text),
                        result_text=result_text,
                        result_number=parse_numericish_value(result_text),
                        time_text=time_text,
                        time_number=parse_numericish_value(time_text),
                        raw_row_json=json.dumps({"line": raw_text, "seat_position": seat_position}, ensure_ascii=False),
                    )
                )
            continue

        if has_left_right:
            parsed = tail_values_from_text(raw_text, [5, 4] if has_threshold else [4])
            if not parsed:
                continue
            label, values = parsed
            threshold_text = values[0] if len(values) == 5 else None
            start = 1 if threshold_text is not None else 0
            if len(values[start:]) != 4:
                continue
            left_text, left_time_text, right_text, right_time_text = values[start:]
            rows.append(
                make_result_row(
                    section_name=section_name,
                    label=label,
                    unit=extract_unit_from_label(label),
                    threshold_text=threshold_text,
                    threshold_number=parse_numericish_value(threshold_text),
                    left_text=left_text,
                    left_number=parse_numericish_value(left_text),
                    left_time_text=left_time_text,
                    left_time_number=parse_numericish_value(left_time_text),
                    right_text=right_text,
                    right_number=parse_numericish_value(right_text),
                    right_time_text=right_time_text,
                    right_time_number=parse_numericish_value(right_time_text),
                    raw_row_json=json.dumps({"line": raw_text, "seat_position": default_seat}, ensure_ascii=False),
                )
            )
            continue

        parsed = tail_values_from_text(raw_text, [3, 2] if has_threshold else [2])
        if not parsed:
            continue
        label, values = parsed
        threshold_text = values[0] if len(values) == 3 else None
        start = 1 if threshold_text is not None else 0
        if len(values[start:]) != 2:
            continue
        result_text, time_text = values[start:]
        rows.append(
            make_result_row(
                section_name=section_name or (default_seat.title() if default_seat else None),
                label=label,
                unit=extract_unit_from_label(label),
                threshold_text=threshold_text,
                threshold_number=parse_numericish_value(threshold_text),
                result_text=result_text,
                result_number=parse_numericish_value(result_text),
                time_text=time_text,
                time_number=parse_numericish_value(time_text),
                raw_row_json=json.dumps({"line": raw_text, "seat_position": default_seat}, ensure_ascii=False),
            )
        )

    if table_type in {"head_injury", "neck_injury", "chest_injury"}:
        headers = ["Seat", "Measure", "Threshold", "Result", "Time (ms)"] if has_driver_passenger else ["Measure", "Threshold", "Result", "Time (ms)"]
    else:
        headers = ["Seat", "Section", "Measure", "Threshold", "Left", "Left time", "Right", "Right time"] if has_driver_passenger else ["Section", "Measure", "Threshold", "Left", "Left time", "Right", "Right time"]
    return rows, metadata, headers


def parse_intrusion_table_v2(lines: list[str], raw_table: Any | None) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    notes = [clean_result_label(line) for line in lines if is_note_line(clean_result_label(line))]
    if raw_table:
        rows: list[dict[str, Any]] = []
        header_found = False
        for raw_row in raw_table:
            cells = [clean_result_label(cell or "") for cell in raw_row]
            if not any(cells):
                continue
            joined = join_cell_fragments(cells)
            if is_footer_line(joined):
                break
            if is_note_line(joined):
                notes.append(joined)
                continue
            if not header_found:
                if "selected locations" in clean_for_signature(joined):
                    header_found = True
                continue
            location = join_cell_fragments(cells[:-4])
            values = [clean_result_label(cell) or None for cell in cells[-4:]]
            if not location and not any(values):
                continue
            if "selected locations" in clean_for_signature(location):
                continue
            rows.append(
                make_result_row(
                    label=location,
                    unit="cm",
                    longitudinal_text=values[0],
                    longitudinal_number=parse_numericish_value(values[0]),
                    lateral_text=values[1],
                    lateral_number=parse_numericish_value(values[1]),
                    vertical_text=values[2],
                    vertical_number=parse_numericish_value(values[2]),
                    resultant_text=values[3],
                    resultant_number=parse_numericish_value(values[3]),
                    raw_row_json=json.dumps({"cells": cells}, ensure_ascii=False),
                )
            )
        if rows:
            metadata = {"notes": notes} if notes else {}
            return rows, metadata, ["Location", "Longitudinal", "Lateral", "Vertical", "Resultant"]
    return parse_intrusion_table(lines)


def parse_dummy_clearance_table_v2(lines: list[str], raw_table: Any | None) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    metadata: dict[str, Any] = {}
    notes: list[str] = []
    current_meta_key: str | None = None
    header_found = False
    for raw_line in lines:
        line = clean_result_label(raw_line)
        if not line:
            continue
        if is_footer_line(line):
            break
        if line.lower().startswith("location"):
            header_found = True
            current_meta_key = None
            break
        if is_note_line(line):
            notes.append(line)
            continue
        meta_match = re.match(r"^(?P<key>[A-Za-z][A-Za-z /()\-]+):\s*(?P<value>.+)$", line)
        if meta_match:
            current_meta_key = clean_for_signature(meta_match.group("key")).replace(" ", "_")
            metadata[current_meta_key] = clean_result_label(meta_match.group("value"))
        elif current_meta_key:
            metadata[current_meta_key] = clean_result_label(f"{metadata[current_meta_key]} {line}")

    if raw_table and header_found:
        rows: list[dict[str, Any]] = []
        table_header_found = False
        for raw_row in raw_table:
            cells = [clean_result_label(cell or "") for cell in raw_row]
            compact = [cell for cell in cells if cell]
            if not compact:
                continue
            joined = join_cell_fragments(compact)
            if is_footer_line(joined):
                break
            if is_note_line(joined):
                notes.append(joined)
                continue
            if not table_header_found:
                if "location" in clean_for_signature(joined) and "code" in clean_for_signature(joined):
                    table_header_found = True
                continue

            cursor = 0
            while cursor < len(compact):
                code_index = next((index for index in range(cursor, len(compact)) if CODE_TOKEN_RE.fullmatch(compact[index])), None)
                if code_index is None or code_index + 1 >= len(compact):
                    break
                label = join_cell_fragments(compact[cursor:code_index])
                code = compact[code_index]
                measure_text = clean_result_label(compact[code_index + 1])
                if label and measure_text:
                    unit = "deg" if "°" in measure_text else "mm"
                    rows.append(
                        make_result_row(
                            label=label,
                            code=code,
                            unit=unit,
                            measure_text=measure_text,
                            measure_number=parse_numericish_value(measure_text),
                            raw_row_json=json.dumps({"cells": compact, "code": code}, ensure_ascii=False),
                        )
                    )
                cursor = code_index + 2
        if rows:
            if notes:
                metadata["notes"] = notes
            return rows, metadata, ["Code", "Location", "Measure"]

    rows, fallback_metadata, headers = parse_dummy_clearance_table(lines)
    if fallback_metadata:
        metadata.update(fallback_metadata)
    if notes and "notes" not in metadata:
        metadata["notes"] = notes
    return rows, metadata, headers


def parse_result_tables_from_page(page_number: int, text_content: str, table_json: str | None, report_test_side: str | None = None) -> list[dict[str, Any]]:
    sections = split_result_sections(text_content)
    if not sections:
        return []

    page_tables: list[Any] = []
    if table_json:
        try:
            page_tables = json.loads(table_json)
        except json.JSONDecodeError:
            page_tables = []

    parsed_tables: list[dict[str, Any]] = []
    for section in sections:
        classified = classify_result_table(section["full_title"] or section["title"])
        if not classified:
            continue
        table_type, table_group = classified
        raw_table_payload: Any = None
        if len(page_tables) == 1 and len(sections) == 1:
            raw_table_payload = page_tables[0]
        elif section["table_order"] - 1 < len(page_tables):
            raw_table_payload = page_tables[section["table_order"] - 1]

        if table_type in {"head_injury", "neck_injury", "chest_injury", "leg_foot_injury", "thigh_hip_injury"}:
            rows, metadata, headers = parse_injury_table(section["body_lines"], table_type, section["full_title"] or section["title"], report_test_side=report_test_side)
        elif table_type == "intrusion":
            rows, metadata, headers = parse_intrusion_table_v2(section["body_lines"], raw_table_payload)
        elif table_type == "dummy_clearance":
            rows, metadata, headers = parse_dummy_clearance_table_v2(section["body_lines"], raw_table_payload)
        elif table_type == "restraint_kinematics":
            rows, metadata, headers = parse_kinematics_table(section["body_lines"])
        else:
            rows, metadata, headers = [], {}, []

        if not rows:
            continue

        parsed_tables.append(
            {
                "page_number": page_number,
                "table_order": section["table_order"],
                "table_ref": section["table_ref"],
                "title": section["full_title"] or section["title"],
                "table_type": table_type,
                "table_group": table_group,
                "extraction_method": "page_text_normalized",
                "header_json": json.dumps(headers, ensure_ascii=False),
                "metadata_json": json.dumps(metadata, ensure_ascii=False) if metadata else None,
                "raw_text": "\n".join(section["lines"]),
                "raw_table_json": json.dumps(raw_table_payload, ensure_ascii=False) if raw_table_payload is not None else None,
                "rows": rows,
            }
        )

    return parsed_tables


def refresh_pdf_result_tables(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM pdf_result_rows")
    connection.execute("DELETE FROM pdf_result_tables")

    page_rows = connection.execute(
        """
        SELECT p.pdf_document_id,
               p.page_number,
               p.text_content,
               p.table_json,
               i.report_test_side
          FROM pdf_pages p
          JOIN pdf_document_inventory i ON i.pdf_document_id = p.pdf_document_id
         WHERE i.local_exists = 1
           AND i.extraction_status = 'done'
           AND i.pdf_role = 'report'
         ORDER BY p.pdf_document_id, p.page_number
        """
    ).fetchall()

    row_columns = ", ".join(["pdf_result_table_id", "row_order", *RESULT_ROW_FIELDS])
    row_placeholders = ", ".join(["?"] * (2 + len(RESULT_ROW_FIELDS)))

    for page_row in page_rows:
        parsed_tables = parse_result_tables_from_page(
            page_number=page_row["page_number"],
            text_content=page_row["text_content"] or "",
            table_json=page_row["table_json"],
            report_test_side=page_row["report_test_side"],
        )
        for table in parsed_tables:
            cursor = connection.execute(
                """
                INSERT INTO pdf_result_tables (
                  pdf_document_id, page_number, table_order, table_ref, title, table_type,
                  table_group, extraction_method, header_json, metadata_json, raw_text,
                  raw_table_json, row_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    page_row["pdf_document_id"],
                    table["page_number"],
                    table["table_order"],
                    table["table_ref"],
                    table["title"],
                    table["table_type"],
                    table["table_group"],
                    table["extraction_method"],
                    table["header_json"],
                    table["metadata_json"],
                    table["raw_text"],
                    table["raw_table_json"],
                    len(table["rows"]),
                ),
            )
            pdf_result_table_id = int(cursor.lastrowid)
            enriched_rows = [enrich_result_row_fields(dict(row)) for row in table["rows"]]
            row_values = [
                (
                    pdf_result_table_id,
                    row_order,
                    *[row.get(field) for field in RESULT_ROW_FIELDS],
                )
                for row_order, row in enumerate(enriched_rows, start=1)
            ]
            if row_values:
                connection.executemany(
                    f"INSERT INTO pdf_result_rows ({row_columns}) VALUES ({row_placeholders})",
                    row_values,
                )

    connection.execute("DELETE FROM pdf_result_table_summary")
    connection.execute(
        """
        INSERT INTO pdf_result_table_summary (
          table_type, table_group, document_count, table_count, row_count
        )
        SELECT table_type,
               table_group,
               COUNT(DISTINCT pdf_document_id) AS document_count,
               COUNT(*) AS table_count,
               COALESCE(SUM(row_count), 0) AS row_count
          FROM pdf_result_tables
         GROUP BY table_type, table_group
        """
    )


def refresh_pdf_common_measure_summary(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM pdf_common_measure_summary")

    source_rows = connection.execute(
        """
        SELECT prt.pdf_document_id,
               prt.table_type,
               prt.table_group,
               prr.section_name,
               prr.section_key,
               prr.seat_position,
               prr.label,
               prr.normalized_label,
               prr.code,
               prr.unit,
               prr.measure_text,
               i.test_code
          FROM pdf_result_rows prr
          JOIN pdf_result_tables prt ON prt.pdf_result_table_id = prr.pdf_result_table_id
          LEFT JOIN pdf_document_inventory i ON i.pdf_document_id = prt.pdf_document_id
         ORDER BY prt.table_type, prt.pdf_document_id, prr.row_order
        """
    ).fetchall()

    grouped: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in source_rows:
        label_source = clean_result_label(row["label"] or row["code"] or row["measure_text"] or "")
        normalized_label = normalize_text(row["normalized_label"] or canonical_result_label(label_source))
        if not normalized_label:
            continue

        section_key = normalize_text(row["section_key"] or "")
        section_label = clean_result_label(row["section_name"] or "") if section_key else ""
        unit = normalize_text(row["unit"] or extract_unit_from_label(label_source) or "")
        key = (row["table_type"], row["table_group"], section_key, normalized_label, unit)
        bucket = grouped.setdefault(
            key,
            {
                "table_type": row["table_type"],
                "table_group": row["table_group"],
                "section_key": section_key,
                "section_counts": {},
                "display_counts": {},
                "unit": unit,
                "document_ids": set(),
                "row_count": 0,
                "seat_positions": set(),
                "sample_test_codes": [],
                "sample_codes_seen": set(),
            },
        )
        if section_label:
            bucket["section_counts"][section_label] = bucket["section_counts"].get(section_label, 0) + 1
        bucket["display_counts"][label_source] = bucket["display_counts"].get(label_source, 0) + 1
        bucket["document_ids"].add(row["pdf_document_id"])
        bucket["row_count"] += 1
        if row["seat_position"]:
            bucket["seat_positions"].add(normalize_text(row["seat_position"]))
        test_code = normalize_text(row["test_code"] or "")
        if test_code and test_code not in bucket["sample_codes_seen"] and len(bucket["sample_test_codes"]) < 5:
            bucket["sample_test_codes"].append(test_code)
            bucket["sample_codes_seen"].add(test_code)

    insert_rows = []
    for key, bucket in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][2], item[0][3], item[0][4])):
        insert_rows.append(
            (
                bucket["table_type"],
                bucket["table_group"],
                bucket["section_key"],
                preferred_summary_text(bucket["section_counts"]),
                key[3],
                preferred_summary_text(bucket["display_counts"]),
                bucket["unit"],
                ", ".join(sorted(bucket["seat_positions"])) or None,
                len(bucket["document_ids"]),
                bucket["row_count"],
                ", ".join(bucket["sample_test_codes"]) or None,
            )
        )

    if insert_rows:
        connection.executemany(
            """
            INSERT INTO pdf_common_measure_summary (
              table_type, table_group, section_key, section_label, normalized_label,
              display_label, unit, seat_positions, document_count, row_count, sample_test_codes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )


def store_page(connection: sqlite3.Connection, pdf_document_id: int, page_number: int, text: str, tables: list[list[list[str | None]]], page_width: float, page_height: float) -> None:
    lines = nonempty_lines(text)
    heading_lines = lines[:5]
    first_line = lines[0] if lines else None
    last_line = lines[-1] if lines else None
    layout_signature = hashlib.sha256("|".join(clean_for_signature(line) for line in heading_lines).encode("utf-8")).hexdigest() if heading_lines else None

    connection.execute(
        """
        INSERT OR REPLACE INTO pdf_pages (pdf_document_id, page_number, text_content, table_json)
        VALUES (?, ?, ?, ?)
        """,
        (pdf_document_id, page_number, text, json.dumps(tables, ensure_ascii=False)),
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO pdf_page_features (
          pdf_document_id, page_number, page_width, page_height, word_count, char_count, table_count,
          first_line, last_line, heading_lines_json, layout_signature
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pdf_document_id,
            page_number,
            page_width,
            page_height,
            len(re.findall(r"\S+", text)),
            len(text),
            len(tables),
            first_line,
            last_line,
            json.dumps(heading_lines, ensure_ascii=False),
            layout_signature,
        ),
    )


def infer_dataset_partition(local_path: str | None) -> str | None:
    if not local_path:
        return None
    try:
        relative = Path(local_path).resolve().relative_to(RAW_DATA_ROOT)
    except Exception:
        return None
    return relative.parts[0] if relative.parts else None


def infer_pdf_role(folder_path: str) -> str:
    upper = folder_path.upper()
    if upper.endswith("REPORTS"):
        return "report"
    if "DATA\\EDR" in upper:
        return "edr"
    return "document"


def build_metric_maps(metric_rows: list[sqlite3.Row]) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], float]]:
    text_map: dict[tuple[str, str], str] = {}
    number_map: dict[tuple[str, str], float] = {}
    for row in metric_rows:
        key = (row["namespace"], row["metric_name"])
        if row["metric_value_text"] is not None and key not in text_map:
            text_map[key] = row["metric_value_text"]
        if row["metric_value_number"] is not None and key not in number_map:
            number_map[key] = float(row["metric_value_number"])
    return text_map, number_map


def metric_text(text_map: dict[tuple[str, str], str], *keys: tuple[str, str]) -> str | None:
    for key in keys:
        value = text_map.get(key)
        if value:
            return value
    return None


def metric_number(number_map: dict[tuple[str, str], float], *keys: tuple[str, str]) -> float | None:
    for key in keys:
        value = number_map.get(key)
        if value is not None:
            return value
    return None


def refresh_pdf_inventory(connection: sqlite3.Connection) -> None:
    base_rows = connection.execute(
        """
        WITH latest_assignments AS (
          SELECT pdf_document_id,
                 family_key,
                 confidence,
                 classification_method,
                 preview_png_path,
                 ROW_NUMBER() OVER (PARTITION BY pdf_document_id ORDER BY pdf_layout_assignment_id DESC) AS rn
            FROM pdf_layout_assignments
        ),
        page_summary AS (
          SELECT pdf_document_id,
                 SUM(table_count) AS total_table_count,
                 SUM(CASE WHEN table_count > 0 THEN 1 ELSE 0 END) AS pages_with_tables,
                 SUM(word_count) AS total_word_count,
                 AVG(word_count * 1.0) AS avg_words_per_page
            FROM pdf_page_features
           GROUP BY pdf_document_id
        ),
        page_headings AS (
          SELECT pdf_document_id,
                 MAX(CASE WHEN page_number = 1 THEN first_line END) AS first_page_heading,
                 MAX(CASE WHEN page_number = 2 THEN first_line END) AS second_page_heading
            FROM pdf_page_features
           GROUP BY pdf_document_id
        )
        SELECT pd.pdf_document_id,
               pd.asset_id,
               pd.filegroup_id,
               pd.extraction_status,
               pd.page_count,
               pd.notes AS pdf_notes,
               a.local_path,
               a.relative_path,
               a.folder_path,
               a.filename,
               fg.test_code,
               fg.title,
               fg.tested_on AS filegroup_tested_on,
               tt.test_type_label,
               v.vehicle_year,
               v.vehicle_make_model,
               la.family_key,
               la.confidence,
               la.classification_method,
               la.preview_png_path,
               lf.family_label,
               lf.source_kind AS family_source_kind,
               ps.total_table_count,
               ps.pages_with_tables,
               ps.total_word_count,
               ps.avg_words_per_page,
               ph.first_page_heading,
               ph.second_page_heading
          FROM pdf_documents pd
          JOIN assets a ON a.asset_id = pd.asset_id
          JOIN filegroups fg ON fg.filegroup_id = pd.filegroup_id
          JOIN test_types tt ON tt.test_type_code = fg.test_type_code
          LEFT JOIN vehicles v ON v.vehicle_id = fg.vehicle_id
          LEFT JOIN latest_assignments la ON la.pdf_document_id = pd.pdf_document_id AND la.rn = 1
          LEFT JOIN pdf_layout_families lf ON lf.family_key = la.family_key
          LEFT JOIN page_summary ps ON ps.pdf_document_id = pd.pdf_document_id
          LEFT JOIN page_headings ph ON ph.pdf_document_id = pd.pdf_document_id
         ORDER BY pd.pdf_document_id
        """
    ).fetchall()

    inventory_rows = []
    for row in base_rows:
        local_exists = int(bool(row["local_path"]) and Path(row["local_path"]).exists())
        metric_rows = connection.execute(
            """
            SELECT namespace, metric_name, metric_value_text, metric_value_number
              FROM extracted_metrics
             WHERE asset_id = ? AND source_type LIKE 'pdf_%'
             ORDER BY extracted_metric_id
            """,
            (row["asset_id"],),
        ).fetchall()
        text_map, number_map = build_metric_maps(metric_rows)

        family_key = row["family_key"] if local_exists else None
        family_label = row["family_label"] if local_exists else None
        family_source_kind = row["family_source_kind"] if local_exists else None
        classification_confidence = row["confidence"] if local_exists else None
        classification_method = row["classification_method"] if local_exists else None
        preview_png_path = row["preview_png_path"] if local_exists else None

        inventory_rows.append(
            (
                row["pdf_document_id"],
                row["asset_id"],
                row["filegroup_id"],
                row["test_code"],
                row["title"],
                row["filegroup_tested_on"],
                row["test_type_label"],
                row["vehicle_year"],
                row["vehicle_make_model"],
                infer_dataset_partition(row["local_path"]),
                infer_pdf_role(row["folder_path"]),
                family_key,
                family_label,
                family_source_kind,
                row["extraction_status"],
                local_exists,
                row["local_path"],
                row["relative_path"],
                row["folder_path"],
                row["filename"],
                row["page_count"],
                row["total_table_count"],
                row["pages_with_tables"],
                row["total_word_count"],
                row["avg_words_per_page"],
                row["first_page_heading"],
                row["second_page_heading"],
                metric_text(text_map, ("report", "vehicle_title")),
                metric_text(text_map, ("report", "tested_on")),
                metric_text(text_map, ("report", "test_side")),
                metric_text(text_map, ("report", "body_type")),
                metric_text(text_map, ("report", "engine_transmission")),
                metric_text(text_map, ("report", "test_protocol")),
                metric_text(text_map, ("report", "test_protocol_version")),
                metric_number(number_map, ("report", "speed_target_kmh")),
                metric_number(number_map, ("report", "speed_actual_kmh")),
                metric_number(number_map, ("report", "overlap_target_pct")),
                metric_number(number_map, ("report", "overlap_actual_pct")),
                metric_number(number_map, ("report", "wheelbase_cm_manufacturer")),
                metric_number(number_map, ("report", "wheelbase_cm_measured")),
                metric_number(number_map, ("report", "overall_length_cm_manufacturer")),
                metric_number(number_map, ("report", "overall_length_cm_measured")),
                metric_number(number_map, ("report", "overall_width_cm_manufacturer")),
                metric_number(number_map, ("report", "overall_width_cm_measured")),
                metric_number(number_map, ("report", "curb_weight_kg_manufacturer")),
                metric_number(number_map, ("report", "curb_weight_kg_measured")),
                metric_number(number_map, ("report", "test_weight_kg_measured")),
                metric_text(text_map, ("edr", "vendor")),
                metric_text(text_map, ("edr", "vendor_family")),
                metric_text(text_map, ("edr", "case_number")),
                metric_text(text_map, ("edr", "cdr_software_version"), ("edr", "gedr_software_version")),
                metric_text(text_map, ("document", "vehicle_identification_number"), ("edr", "vehicle_identification_number")),
                classification_confidence,
                classification_method,
                preview_png_path,
                row["pdf_notes"],
            )
        )

    connection.execute("DELETE FROM pdf_document_inventory")
    connection.executemany(
        """
        INSERT INTO pdf_document_inventory (
          pdf_document_id, asset_id, filegroup_id, test_code, title, filegroup_tested_on, test_type_label,
          vehicle_year, vehicle_make_model, dataset_partition, pdf_role, family_key, family_label, family_source_kind,
          extraction_status, local_exists, local_path, relative_path, folder_path, filename, page_count,
          total_table_count, pages_with_tables, total_word_count, avg_words_per_page, first_page_heading,
          second_page_heading, report_vehicle_title, report_tested_on, report_test_side, report_body_type,
          report_engine_transmission, report_test_protocol, report_test_protocol_version, report_speed_target_kmh,
          report_speed_actual_kmh, report_overlap_target_pct, report_overlap_actual_pct,
          report_wheelbase_cm_manufacturer, report_wheelbase_cm_measured,
          report_overall_length_cm_manufacturer, report_overall_length_cm_measured,
          report_overall_width_cm_manufacturer, report_overall_width_cm_measured,
          report_curb_weight_kg_manufacturer, report_curb_weight_kg_measured,
          report_test_weight_kg_measured, edr_vendor, edr_vendor_family, edr_case_number,
          edr_software_version, vehicle_identification_number, classification_confidence,
          classification_method, preview_png_path, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        inventory_rows,
    )


def refresh_pdf_summary_tables(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM pdf_family_summary")
    connection.execute(
        """
        INSERT INTO pdf_family_summary (
          family_key, family_label, source_kind, document_count, locally_available_count, completed_count,
          avg_page_count, avg_table_count, avg_word_count, avg_confidence
        )
        SELECT COALESCE(family_key, '[unclassified]') AS family_key,
               COALESCE(family_label, 'Unclassified PDF') AS family_label,
               COALESCE(family_source_kind, pdf_role) AS source_kind,
               COUNT(*) AS document_count,
               SUM(local_exists) AS locally_available_count,
               SUM(CASE WHEN extraction_status = 'done' AND local_exists = 1 THEN 1 ELSE 0 END) AS completed_count,
               ROUND(AVG(CASE WHEN local_exists = 1 THEN page_count END), 2) AS avg_page_count,
               ROUND(AVG(CASE WHEN local_exists = 1 THEN total_table_count END), 2) AS avg_table_count,
               ROUND(AVG(CASE WHEN local_exists = 1 THEN total_word_count END), 2) AS avg_word_count,
               ROUND(AVG(CASE WHEN local_exists = 1 THEN classification_confidence END), 3) AS avg_confidence
          FROM pdf_document_inventory
         GROUP BY 1, 2, 3
        """
    )

    connection.execute("DELETE FROM pdf_metric_coverage")
    connection.execute(
        """
        WITH available_docs AS (
          SELECT pdf_document_id,
                 asset_id,
                 COALESCE(family_key, '[unclassified]') AS family_key,
                 COALESCE(family_label, 'Unclassified PDF') AS family_label,
                 COALESCE(family_source_kind, pdf_role) AS source_kind
            FROM pdf_document_inventory
           WHERE local_exists = 1 AND extraction_status = 'done'
        ),
        family_sizes AS (
          SELECT family_key, COUNT(*) AS available_document_count
            FROM available_docs
           GROUP BY family_key
        ),
        metric_docs AS (
          SELECT DISTINCT ad.family_key,
                          ad.family_label,
                          ad.source_kind,
                          ad.pdf_document_id,
                          em.namespace,
                          em.metric_name
            FROM available_docs ad
            JOIN extracted_metrics em
              ON em.asset_id = ad.asset_id
             AND em.source_type LIKE 'pdf_%'
        )
        INSERT INTO pdf_metric_coverage (
          family_key, family_label, source_kind, namespace, metric_name,
          document_count, available_document_count, coverage_ratio
        )
        SELECT md.family_key,
               md.family_label,
               md.source_kind,
               md.namespace,
               md.metric_name,
               COUNT(md.pdf_document_id) AS document_count,
               fs.available_document_count,
               ROUND(COUNT(md.pdf_document_id) * 1.0 / fs.available_document_count, 4) AS coverage_ratio
          FROM metric_docs md
          JOIN family_sizes fs ON fs.family_key = md.family_key
         GROUP BY md.family_key, md.family_label, md.source_kind, md.namespace, md.metric_name, fs.available_document_count
        """
    )
    connection.execute(
        """
        WITH available_docs AS (
          SELECT pdf_document_id, asset_id
            FROM pdf_document_inventory
           WHERE local_exists = 1 AND extraction_status = 'done'
        ),
        totals AS (
          SELECT COUNT(*) AS available_document_count FROM available_docs
        ),
        metric_docs AS (
          SELECT DISTINCT ad.pdf_document_id, em.namespace, em.metric_name
            FROM available_docs ad
            JOIN extracted_metrics em
              ON em.asset_id = ad.asset_id
             AND em.source_type LIKE 'pdf_%'
        )
        INSERT INTO pdf_metric_coverage (
          family_key, family_label, source_kind, namespace, metric_name,
          document_count, available_document_count, coverage_ratio
        )
        SELECT '[all]' AS family_key,
               'All PDFs' AS family_label,
               'all' AS source_kind,
               md.namespace,
               md.metric_name,
               COUNT(md.pdf_document_id) AS document_count,
               totals.available_document_count,
               ROUND(COUNT(md.pdf_document_id) * 1.0 / totals.available_document_count, 4) AS coverage_ratio
          FROM metric_docs md
          CROSS JOIN totals
         GROUP BY md.namespace, md.metric_name, totals.available_document_count
        """
    )


def refresh_pdf_derived_tables(connection: sqlite3.Connection) -> None:
    refresh_pdf_inventory(connection)
    refresh_pdf_result_tables(connection)
    refresh_pdf_common_measure_summary(connection)
    refresh_pdf_summary_tables(connection)


def process_job(connection: sqlite3.Connection, run_id: int, job: PdfJob, render_previews: bool) -> tuple[str, str]:
    pdf_path = Path(job.local_path)
    if not pdf_path.exists():
        connection.execute(
            """
            UPDATE pdf_documents
               SET extraction_status = 'skipped',
                   parser_name = ?,
                   notes = ?
             WHERE pdf_document_id = ?
            """,
            (PARSER_VERSION, f"Local file missing: {pdf_path}", job.pdf_document_id),
        )
        return "skipped", str(pdf_path)

    connection.execute(
        "UPDATE pdf_documents SET extraction_status = 'processing', parser_name = ? WHERE pdf_document_id = ?",
        (PARSER_VERSION, job.pdf_document_id),
    )
    connection.execute("DELETE FROM pdf_pages WHERE pdf_document_id = ?", (job.pdf_document_id,))
    connection.execute("DELETE FROM pdf_page_features WHERE pdf_document_id = ?", (job.pdf_document_id,))
    connection.execute("DELETE FROM extracted_metrics WHERE asset_id = ? AND source_type LIKE 'pdf_%'", (job.asset_id,))

    try:
        reader = PdfReader(str(pdf_path), strict=False)
        metadata = {
            "producer": normalize_text(str(reader.metadata.get("/Producer", ""))) if reader.metadata else "",
            "creator": normalize_text(str(reader.metadata.get("/Creator", ""))) if reader.metadata else "",
            "author": normalize_text(str(reader.metadata.get("/Author", ""))) if reader.metadata else "",
        }
        preview_path = render_preview(pdf_path, job.pdf_document_id) if render_previews else None
        full_page_texts: list[str] = []

        with pdfplumber.open(str(pdf_path)) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(layout=True) or page.extract_text() or ""
                text = text.replace("\x00", "")
                tables = extract_tables(page)
                store_page(connection, job.pdf_document_id, index, text, tables, float(page.width), float(page.height))
                full_page_texts.append(text)

            first_page_text = full_page_texts[0] if full_page_texts else ""
            second_page_text = full_page_texts[1] if len(full_page_texts) > 1 else ""
            first_page = pdf.pages[0] if pdf.pages else None
            table_count_page1 = len(extract_tables(first_page)) if first_page else 0
            first_page_size = (float(first_page.width), float(first_page.height)) if first_page else (0.0, 0.0)

        signature_hash, fingerprint = build_fingerprint(
            job=job,
            metadata=metadata,
            first_page_text=first_page_text,
            second_page_text=second_page_text,
            page_count=len(reader.pages),
            first_page_size=first_page_size,
            table_count_page1=table_count_page1,
        )
        family_key, confidence, classification_method, notes = classify_pdf(
            job=job,
            first_page_text=first_page_text,
            second_page_text=second_page_text,
            page_count=len(reader.pages),
            fingerprint=fingerprint,
        )
        connection.execute(
            """
            INSERT INTO pdf_layout_assignments (
              pdf_document_id, pdf_extraction_run_id, family_key, confidence, classification_method,
              signature_hash, preview_png_path, fingerprint_json, classified_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.pdf_document_id,
                run_id,
                family_key,
                confidence,
                classification_method,
                signature_hash,
                preview_path,
                json.dumps(fingerprint, ensure_ascii=False),
                utc_now_iso(),
                notes,
            ),
        )

        metrics = extract_metrics(
            job=job,
            family_key=family_key,
            first_page_text=first_page_text,
            second_page_text=second_page_text,
            full_text="\n".join(full_page_texts),
            page_count=len(reader.pages),
            confidence=confidence,
        )
        connection.executemany(
            """
            INSERT INTO extracted_metrics (
              filegroup_id, asset_id, source_type, source_locator, namespace, metric_name,
              metric_value_text, metric_value_number, metric_unit, confidence, extraction_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            metrics,
        )
        connection.execute(
            """
            UPDATE pdf_documents
               SET extraction_status = 'done',
                   page_count = ?,
                   parser_name = ?,
                   notes = ?
             WHERE pdf_document_id = ?
            """,
            (
                len(reader.pages),
                PARSER_VERSION,
                f"{family_key} ({confidence:.2f})",
                job.pdf_document_id,
            ),
        )
        return "processed", family_key
    except Exception as exc:
        connection.execute(
            """
            UPDATE pdf_documents
               SET extraction_status = 'error',
                   parser_name = ?,
                   notes = ?
             WHERE pdf_document_id = ?
            """,
            (PARSER_VERSION, str(exc), job.pdf_document_id),
        )
        return "error", str(exc)


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    ensure_pdf_schema(connection)
    scope = build_scope(args)
    run_id = create_run(connection, scope)
    jobs = load_jobs(connection, args)

    success_count = 0
    skipped_count = 0
    error_count = 0
    family_counter: dict[str, int] = {}

    for job in jobs:
        status, info = process_job(connection, run_id, job, render_previews=args.render_previews)
        if status == "processed":
            success_count += 1
            family_counter[info] = family_counter.get(info, 0) + 1
        elif status == "skipped":
            skipped_count += 1
        else:
            error_count += 1
        connection.commit()

    refresh_pdf_derived_tables(connection)
    connection.commit()

    notes = json.dumps(
        {
            "processed": len(jobs),
            "success": success_count,
            "skipped": skipped_count,
            "error": error_count,
            "family_counter": family_counter,
        },
        ensure_ascii=False,
    )
    finalize_run(connection, run_id, notes)
    connection.commit()
    print(notes)
    connection.close()


if __name__ == "__main__":
    main()
