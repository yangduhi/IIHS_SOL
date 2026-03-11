from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "small_overlap" / "dashboard" / "pdf_catalog"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a static HTML dashboard for the PDF inventory.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def relative_path(target: str | None, start: Path, preview_dir: Path) -> str:
    if not target:
        return ""
    path = Path(target)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.exists():
        return ""
    preview_dir.mkdir(parents=True, exist_ok=True)
    copied = preview_dir / path.name
    if not copied.exists():
        shutil.copy2(path, copied)
    return Path(os.path.relpath(copied, start=start)).as_posix()


def rounded(value: Any, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def load_result_tables(connection: sqlite3.Connection) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]], dict[int, dict[str, int]]]:
    row_rows = connection.execute(
        """
        SELECT pdf_result_table_id,
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
               result_text,
               time_text,
               left_text,
               left_time_text,
               right_text,
               right_time_text,
               longitudinal_text,
               lateral_text,
               vertical_text,
               resultant_text,
               measure_text,
               raw_row_json
          FROM pdf_result_rows
         ORDER BY pdf_result_table_id, row_order
        """
    ).fetchall()

    rows_by_table: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in row_rows:
        payload = {"row_order": row["row_order"]}
        raw_payload: dict[str, Any] = {}
        quality_flags: list[str] = []
        if row["raw_row_json"]:
            try:
                raw_payload = json.loads(row["raw_row_json"])
            except json.JSONDecodeError:
                raw_payload = {}
        if row["quality_flags"]:
            try:
                quality_flags = json.loads(row["quality_flags"])
            except json.JSONDecodeError:
                quality_flags = []
        for key in (
            "section_name",
            "seat_position",
            "section_key",
            "label",
            "normalized_label",
            "quality_status",
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
        ):
            if row[key] not in (None, ""):
                payload[key] = row[key]
        if row["quality_score"] is not None:
            payload["quality_score"] = rounded(row["quality_score"], 3)
        if quality_flags:
            payload["quality_flags"] = quality_flags
        if "seat_position" not in payload and raw_payload.get("seat_position"):
            payload["seat_position"] = raw_payload["seat_position"]
        rows_by_table[row["pdf_result_table_id"]].append(payload)

    table_rows = connection.execute(
        """
        SELECT prt.pdf_result_table_id,
               prt.pdf_document_id,
               prt.page_number,
               prt.table_order,
               prt.table_ref,
               prt.title,
               prt.table_type,
               prt.table_group,
               prt.row_count,
               prt.header_json,
               prt.metadata_json
          FROM pdf_result_tables prt
         ORDER BY prt.pdf_document_id, prt.page_number, prt.table_order
        """
    ).fetchall()

    tables_by_document: dict[int, list[dict[str, Any]]] = defaultdict(list)
    counts_by_document: dict[int, dict[str, int]] = defaultdict(lambda: {"table_count": 0, "row_count": 0})
    for row in table_rows:
        metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        headers = json.loads(row["header_json"]) if row["header_json"] else []
        tables_by_document[row["pdf_document_id"]].append(
            {
                "pdf_result_table_id": row["pdf_result_table_id"],
                "page_number": row["page_number"],
                "table_order": row["table_order"],
                "table_ref": row["table_ref"] or "",
                "title": row["title"],
                "table_type": row["table_type"],
                "table_group": row["table_group"],
                "row_count": row["row_count"],
                "headers": headers,
                "metadata": metadata,
                "rows": rows_by_table.get(row["pdf_result_table_id"], []),
            }
        )
        counts_by_document[row["pdf_document_id"]]["table_count"] += 1
        counts_by_document[row["pdf_document_id"]]["row_count"] += row["row_count"]

    summary_rows = [
        {
            "table_type": row["table_type"],
            "table_group": row["table_group"],
            "document_count": row["document_count"],
            "table_count": row["table_count"],
            "row_count": row["row_count"],
        }
        for row in connection.execute(
            """
            SELECT table_type, table_group, document_count, table_count, row_count
              FROM pdf_result_table_summary
             ORDER BY table_group, table_type
            """
        ).fetchall()
    ]
    return tables_by_document, summary_rows, counts_by_document


def load_inventory(
    connection: sqlite3.Connection,
    dashboard_dir: Path,
    counts_by_document: dict[int, dict[str, int]],
) -> list[dict[str, Any]]:
    preview_dir = dashboard_dir / "previews"
    rows = [dict(row) for row in connection.execute("SELECT * FROM pdf_document_inventory ORDER BY test_code, pdf_role, filename")]
    documents = []
    for row in rows:
        counts = counts_by_document.get(row["pdf_document_id"], {})
        protocol_or_vendor = row["report_test_protocol"] or row["edr_vendor"] or row["edr_vendor_family"] or ""
        documents.append(
            {
                "pdf_document_id": row["pdf_document_id"],
                "test_code": row["test_code"],
                "title": row["title"],
                "vehicle_year": row["vehicle_year"],
                "vehicle_make_model": row["vehicle_make_model"],
                "dataset_partition": row["dataset_partition"] or "",
                "pdf_role": row["pdf_role"],
                "family_key": row["family_key"] or "",
                "family_label": row["family_label"] or "Unclassified",
                "family_source_kind": row["family_source_kind"] or row["pdf_role"],
                "extraction_status": row["extraction_status"],
                "local_exists": bool(row["local_exists"]),
                "filename": row["filename"],
                "folder_path": row["folder_path"],
                "local_path": row["local_path"],
                "page_count": row["page_count"],
                "total_table_count": row["total_table_count"],
                "pages_with_tables": row["pages_with_tables"],
                "total_word_count": row["total_word_count"],
                "avg_words_per_page": rounded(row["avg_words_per_page"]),
                "first_page_heading": row["first_page_heading"] or "",
                "second_page_heading": row["second_page_heading"] or "",
                "filegroup_tested_on": row["filegroup_tested_on"] or "",
                "report_vehicle_title": row["report_vehicle_title"] or "",
                "report_tested_on": row["report_tested_on"] or "",
                "report_test_side": row["report_test_side"] or "",
                "report_body_type": row["report_body_type"] or "",
                "report_engine_transmission": row["report_engine_transmission"] or "",
                "report_test_protocol": row["report_test_protocol"] or "",
                "report_test_protocol_version": row["report_test_protocol_version"] or "",
                "report_speed_target_kmh": rounded(row["report_speed_target_kmh"]),
                "report_speed_actual_kmh": rounded(row["report_speed_actual_kmh"]),
                "report_overlap_target_pct": rounded(row["report_overlap_target_pct"]),
                "report_overlap_actual_pct": rounded(row["report_overlap_actual_pct"]),
                "report_wheelbase_cm_manufacturer": rounded(row["report_wheelbase_cm_manufacturer"]),
                "report_wheelbase_cm_measured": rounded(row["report_wheelbase_cm_measured"]),
                "report_curb_weight_kg_measured": rounded(row["report_curb_weight_kg_measured"]),
                "edr_vendor": row["edr_vendor"] or "",
                "edr_vendor_family": row["edr_vendor_family"] or "",
                "edr_case_number": row["edr_case_number"] or "",
                "edr_software_version": row["edr_software_version"] or "",
                "vehicle_identification_number": row["vehicle_identification_number"] or "",
                "classification_confidence": rounded(row["classification_confidence"], 3),
                "classification_method": row["classification_method"] or "",
                "protocol_or_vendor": protocol_or_vendor,
                "preview_rel": relative_path(row["preview_png_path"], dashboard_dir, preview_dir),
                "parsed_result_table_count": counts.get("table_count", 0),
                "parsed_result_row_count": counts.get("row_count", 0),
            }
        )
    return documents


def load_family_summary(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT family_key,
               family_label,
               source_kind,
               document_count,
               locally_available_count,
               completed_count,
               avg_page_count,
               avg_table_count,
               avg_word_count,
               avg_confidence
          FROM pdf_family_summary
         ORDER BY document_count DESC, family_key
        """
    ).fetchall()
    return [
        {
            "family_key": row["family_key"],
            "family_label": row["family_label"],
            "source_kind": row["source_kind"],
            "document_count": row["document_count"],
            "locally_available_count": row["locally_available_count"],
            "completed_count": row["completed_count"],
            "avg_page_count": rounded(row["avg_page_count"]),
            "avg_table_count": rounded(row["avg_table_count"]),
            "avg_word_count": rounded(row["avg_word_count"]),
            "avg_confidence": rounded(row["avg_confidence"], 3),
        }
        for row in rows
    ]


def load_common_measure_summary(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
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
    ).fetchall()
    return [
        {
            "table_type": row["table_type"],
            "table_group": row["table_group"],
            "section_key": row["section_key"] or "",
            "section_label": row["section_label"] or "",
            "normalized_label": row["normalized_label"],
            "display_label": row["display_label"],
            "unit": row["unit"] or "",
            "seat_positions": row["seat_positions"] or "",
            "document_count": row["document_count"],
            "row_count": row["row_count"],
            "sample_test_codes": row["sample_test_codes"] or "",
        }
        for row in rows
    ]


def build_summary(documents: list[dict[str, Any]], result_summary: list[dict[str, Any]]) -> dict[str, Any]:
    local_docs = [row for row in documents if row["local_exists"]]
    report_docs = [row for row in local_docs if row["pdf_role"] == "report"]
    edr_docs = [row for row in local_docs if row["pdf_role"] == "edr"]
    missing_docs = [row for row in documents if not row["local_exists"]]
    page_values = [row["page_count"] for row in local_docs if row["page_count"] is not None]
    return {
        "total_documents": len(documents),
        "local_documents": len(local_docs),
        "missing_local_documents": len(missing_docs),
        "report_documents": len(report_docs),
        "edr_documents": len(edr_docs),
        "total_pages": sum(page_values),
        "avg_pages": round(sum(page_values) / len(page_values), 2) if page_values else None,
        "docs_with_results": sum(1 for row in documents if row["parsed_result_table_count"] > 0),
        "result_table_count": sum(row["table_count"] for row in result_summary),
        "result_row_count": sum(row["row_count"] for row in result_summary),
    }


def build_chart_data(documents: list[dict[str, Any]], family_summary: list[dict[str, Any]], result_summary: list[dict[str, Any]]) -> dict[str, Any]:
    local_docs = [row for row in documents if row["local_exists"]]
    family_rows = [row for row in family_summary if row["locally_available_count"] > 0]
    role_counts = {
        "Report": sum(1 for row in local_docs if row["pdf_role"] == "report"),
        "EDR": sum(1 for row in local_docs if row["pdf_role"] == "edr"),
        "Missing local": sum(1 for row in documents if not row["local_exists"]),
    }
    year_counts: dict[str, int] = {}
    for row in local_docs:
        if row["vehicle_year"] is None:
            continue
        key = str(row["vehicle_year"])
        year_counts[key] = year_counts.get(key, 0) + 1

    coverage_fields = [
        ("vehicle_identification_number", "VIN"),
        ("report_tested_on", "Report date"),
        ("report_test_protocol", "Protocol"),
        ("report_test_protocol_version", "Protocol version"),
        ("report_speed_target_kmh", "Target speed"),
        ("report_overlap_target_pct", "Target overlap"),
        ("report_wheelbase_cm_manufacturer", "Wheelbase"),
        ("report_curb_weight_kg_measured", "Measured curb weight"),
        ("edr_case_number", "EDR case no."),
        ("edr_software_version", "EDR software"),
    ]
    coverage_rows = []
    total_local = len(local_docs) or 1
    for key, label in coverage_fields:
        count = sum(1 for row in local_docs if row.get(key) not in ("", None))
        coverage_rows.append({"field": key, "label": label, "count": count, "ratio": round(count / total_local, 4)})

    return {
        "familyLabels": [row["family_label"] for row in family_rows],
        "familyCounts": [row["locally_available_count"] for row in family_rows],
        "familyKinds": [row["source_kind"] for row in family_rows],
        "roleLabels": list(role_counts.keys()),
        "roleCounts": list(role_counts.values()),
        "yearLabels": sorted(year_counts.keys()),
        "yearCounts": [year_counts[key] for key in sorted(year_counts.keys())],
        "pageCounts": [row["page_count"] for row in local_docs if row["page_count"] is not None],
        "coverageRows": coverage_rows,
        "resultTypeLabels": [row["table_type"] for row in result_summary],
        "resultTypeDocCounts": [row["document_count"] for row in result_summary],
        "resultTypeRowCounts": [row["row_count"] for row in result_summary],
    }


def build_dashboard_data(connection: sqlite3.Connection, dashboard_dir: Path) -> dict[str, Any]:
    result_tables_by_document, result_summary, counts_by_document = load_result_tables(connection)
    documents = load_inventory(connection, dashboard_dir, counts_by_document)
    family_summary = load_family_summary(connection)
    common_measure_summary = load_common_measure_summary(connection)
    return {
        "summary": build_summary(documents, result_summary),
        "familySummary": family_summary,
        "resultSummary": result_summary,
        "commonMeasureSummary": common_measure_summary,
        "documents": documents,
        "resultTablesByDocument": result_tables_by_document,
        "chartData": build_chart_data(documents, family_summary, result_summary),
        "filters": {
            "roles": sorted({row["pdf_role"] for row in documents}),
            "families": sorted({row["family_label"] for row in documents}),
            "sides": sorted({row["report_test_side"] for row in documents if row["report_test_side"]}),
        },
    }


def dashboard_html(data: dict[str, Any]) -> str:
    summary = data["summary"]
    data_json = json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")
    meta_cards = [
        ("PDF in DB", summary["total_documents"]),
        ("Present locally", summary["local_documents"]),
        ("Total pages", summary["total_pages"]),
        ("Docs with results", summary["docs_with_results"]),
        ("Parsed tables", summary["result_table_count"]),
        ("Parsed rows", summary["result_row_count"]),
        ("Reports", summary["report_documents"]),
        ("EDR", summary["edr_documents"]),
        ("Missing local", summary["missing_local_documents"]),
    ]
    cards_html = "".join(
        f'<div class="meta-pill"><span>{label}</span><strong>{value}</strong></div>' for label, value in meta_cards
    )
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>IIHS PDF Catalog Dashboard</title>
  <link rel="icon" href="data:,">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root{--bg:#f3ede3;--card:#fffaf2;--surface:#fffdf8;--muted:#6a6054;--ink:#1d1814;--line:rgba(0,0,0,.09);--accent:#bc4b32;--accent2:#0f7173;--accent3:#785589}
    *{box-sizing:border-box} body{margin:0;color:var(--ink);font-family:"IBM Plex Sans","Segoe UI",sans-serif;background:radial-gradient(circle at top left, rgba(188,75,50,.10), transparent 28%),radial-gradient(circle at top right, rgba(15,113,115,.10), transparent 32%),linear-gradient(180deg,#f8f3ea 0%,#f3ede3 100%)}
    .page{max-width:1680px;margin:0 auto;padding:26px}.hero,.charts,.tables,.explorer{display:grid;gap:18px}.hero{grid-template-columns:1.15fr .85fr}.charts,.tables{grid-template-columns:repeat(2,minmax(0,1fr))}.explorer{grid-template-columns:1.08fr .92fr;align-items:start}
    .card{background:rgba(255,250,242,.94);border:1px solid var(--line);border-radius:22px;box-shadow:0 12px 32px rgba(29,24,20,.08);padding:20px 22px}.eyebrow{font-family:"Space Grotesk",sans-serif;text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:var(--muted);margin-bottom:10px}
    h1,h2,h3{font-family:"Space Grotesk",sans-serif;margin:0;line-height:1.08} h1{font-size:clamp(34px,4vw,56px);margin-bottom:12px}.hero-copy{color:#322a22;line-height:1.6;font-size:15px}
    .meta-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:18px}.meta-pill{background:#f5edde;border:1px solid var(--line);border-radius:16px;padding:12px 14px}.meta-pill span{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px}.meta-pill strong{font-size:22px}
    .note{background:linear-gradient(135deg,rgba(188,75,50,.08),rgba(15,113,115,.05));border-radius:18px;border:1px solid var(--line);padding:16px}.note+.note{margin-top:12px}.note strong{display:block;margin-bottom:8px;font-family:"Space Grotesk",sans-serif;font-size:18px}
    .controls{display:grid;grid-template-columns:1.6fr repeat(4,minmax(0,1fr));gap:10px;margin-bottom:14px}.controls input,.controls select{width:100%;padding:12px 14px;border-radius:14px;border:1px solid var(--line);background:#fffdf8;font:inherit}
    .result-controls{grid-template-columns:1.8fr repeat(4,minmax(0,1fr));margin-top:14px}
    .common-controls{grid-template-columns:1fr 1.8fr;margin-top:14px}
    .common-grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:18px;align-items:start;margin-top:14px}
    .section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap}.section-head .footnote{margin-top:6px}
    .action-button{border:1px solid var(--line);background:#1d1814;color:#fff8ef;border-radius:999px;padding:11px 16px;font:600 13px "IBM Plex Sans",sans-serif;cursor:pointer;transition:transform .14s ease, opacity .14s ease}.action-button:hover{transform:translateY(-1px);opacity:.94}
    .plot{width:100%;height:330px}.table-shell{max-height:720px;overflow:auto;border:1px solid var(--line);border-radius:18px;background:#fffdf8}.summary-table,.doc-table,.result-summary-table,.parsed-table{width:100%;border-collapse:collapse;font-size:14px}
    .summary-table th,.summary-table td,.doc-table th,.doc-table td,.result-summary-table th,.result-summary-table td,.parsed-table th,.parsed-table td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
    .summary-table th,.doc-table th,.result-summary-table th,.parsed-table th{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);position:sticky;top:0;background:#fffaf2}
    .doc-table tbody tr{cursor:pointer;transition:background .14s ease}.doc-table tbody tr:hover{background:#f7efe4}.doc-table tbody tr.active{background:#241d17;color:#fff8ef}.doc-table tbody tr.active .muted{color:rgba(255,248,239,.72)}.doc-table tbody tr.result-active{background:#f5edde}.muted{color:var(--muted)}
    .chip-row{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}.chip{background:#f5edde;border:1px solid var(--line);border-radius:14px;padding:8px 10px;font-size:13px;color:var(--muted)}
    .quality-pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.06em}
    .quality-ok{background:rgba(15,113,115,.10);color:#0f7173}
    .quality-review{background:rgba(188,75,50,.12);color:#8f3726}
    .quality-unknown{background:rgba(0,0,0,.06);color:#5e5448}
    .preview{display:block;width:100%;border-radius:18px;border:1px solid var(--line);background:#fff;margin-top:14px;min-height:240px;object-fit:contain}.detail-grid{display:grid;gap:10px;margin-top:14px}
    .detail-row{padding:12px 14px;border:1px solid var(--line);border-radius:16px;background:#fffdf8}.detail-row span{display:block;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
    .parsed-block{border:1px solid var(--line);border-radius:18px;background:#fff;overflow:hidden;margin-top:14px}.parsed-block:first-child{margin-top:0}.parsed-head{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;padding:14px 16px;border-bottom:1px solid var(--line);background:linear-gradient(135deg,rgba(188,75,50,.08),rgba(15,113,115,.04))}.parsed-head strong{font-family:"Space Grotesk",sans-serif}.parsed-meta,.footnote,.path-display{color:var(--muted);font-size:13px}.path-display{display:block;word-break:break-all;color:var(--accent2)}
    @media (max-width:1320px){.hero,.charts,.tables,.explorer,.common-grid{grid-template-columns:1fr}.meta-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.controls,.common-controls{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="card">
        <div class="eyebrow">IIHS Research Database</div>
        <h1>PDF Catalog Dashboard</h1>
        <div class="hero-copy">
          This catalog surveys every PDF under <code>data/raw</code>. Report result tables are normalized into
          <code>pdf_result_tables</code> and <code>pdf_result_rows</code>, so injury, intrusion, dummy clearance,
          and restraint timing data can be inspected directly from the dashboard.
        </div>
        <div class="meta-grid">__CARDS__</div>
      </div>
      <div class="card">
        <div class="note">
          <strong>Database layers</strong>
          <div><code>pdf_document_inventory</code> covers document-level metadata, while <code>pdf_result_tables</code> and <code>pdf_result_rows</code> store normalized measurement tables.</div>
          <div class="footnote">Average pages per locally available PDF: __AVG_PAGES__</div>
        </div>
        <div class="note">
          <strong>Parsed result coverage</strong>
          <div>Head, neck, chest, leg and foot, thigh and hip, intrusion, dummy clearance, and restraint timing tables are indexed when present.</div>
          <div class="footnote">Select a document below or use the Measurement Explorer to inspect normalized rows across all PDFs.</div>
        </div>
      </div>
    </section>
    <section class="charts">
      <div class="card"><h2 style="font-size:24px; margin-bottom:12px;">Family Distribution</h2><div class="plot" id="family-plot"></div></div>
      <div class="card"><h2 style="font-size:24px; margin-bottom:12px;">Result Table Coverage</h2><div class="plot" id="result-type-plot"></div></div>
      <div class="card"><h2 style="font-size:24px; margin-bottom:12px;">Vehicle Year Coverage</h2><div class="plot" id="year-plot"></div></div>
      <div class="card"><h2 style="font-size:24px; margin-bottom:12px;">Common Field Coverage</h2><div class="plot" id="coverage-plot"></div></div>
    </section>
    <section class="tables">
      <div class="card">
        <h2 style="font-size:24px; margin-bottom:12px;">Family Summary</h2>
        <div class="table-shell" style="max-height:320px;">
          <table class="summary-table">
            <thead><tr><th>Family</th><th>Kind</th><th>Docs</th><th>Local</th><th>Done</th><th>Avg Pages</th><th>Avg Tables</th><th>Avg Words</th><th>Avg Confidence</th></tr></thead>
            <tbody id="family-summary-body"></tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <h2 style="font-size:24px; margin-bottom:12px;">Result Table Summary</h2>
        <div class="table-shell" style="max-height:320px;">
          <table class="result-summary-table">
            <thead><tr><th>Table type</th><th>Group</th><th>Documents</th><th>Tables</th><th>Rows</th></tr></thead>
            <tbody id="result-summary-body"></tbody>
          </table>
        </div>
      </div>
    </section>
    <section class="card" style="margin-top:18px;">
      <h2 style="font-size:24px; margin-bottom:6px;">Common Measure Summary</h2>
      <div class="footnote">Recurring normalized measures across parsed result tables. Click a row to push that measure into the Measurement Explorer.</div>
      <div class="controls common-controls">
        <select id="common-type-filter"><option value="all">All result types</option></select>
        <input id="common-search-box" type="text" placeholder="Search measure, section, unit, sample test code" />
      </div>
      <div class="footnote" id="common-table-note"></div>
      <div class="common-grid">
        <div>
          <div class="plot" id="common-measure-plot" style="height:420px;"></div>
        </div>
        <div class="table-shell" style="max-height:420px;">
          <table class="result-summary-table">
            <thead><tr><th>Type</th><th>Section</th><th>Measure</th><th>Unit</th><th>Seats</th><th>Documents</th><th>Rows</th><th>Samples</th></tr></thead>
            <tbody id="common-measure-body"></tbody>
          </table>
        </div>
      </div>
    </section>
    <section class="explorer">
      <div class="card">
        <h2 style="font-size:24px; margin-bottom:12px;">Document Explorer</h2>
        <div class="controls">
          <input id="search-box" type="text" placeholder="Search test code, vehicle, VIN, filename" />
          <select id="role-filter"><option value="all">All roles</option></select>
          <select id="family-filter"><option value="all">All families</option></select>
          <select id="side-filter"><option value="all">All sides</option></select>
          <select id="local-filter"><option value="present">Present locally</option><option value="all">All rows</option><option value="missing">Missing locally</option></select>
        </div>
        <div class="footnote" id="table-note"></div>
        <div class="table-shell">
          <table class="doc-table">
            <thead><tr><th>Test</th><th>Role</th><th>Family</th><th>Vehicle</th><th>Pages</th><th>Parsed</th><th>Side</th><th>Status</th></tr></thead>
            <tbody id="doc-body"></tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="eyebrow">Selected Document</div>
        <h2 id="detail-title" style="font-size:28px;"></h2>
        <div class="muted" id="detail-subtitle" style="margin-top:6px;"></div>
        <div class="chip-row" id="detail-chips"></div>
        <img id="detail-preview" class="preview" alt="PDF preview" />
        <div class="detail-grid">
          <div class="detail-row"><span>Headings</span><div id="detail-headings"></div></div>
          <div class="detail-row"><span>Structured Fields</span><div id="detail-fields"></div></div>
          <div class="detail-row"><span>Parsed Result Tables</span><div id="detail-results"></div></div>
          <div class="detail-row"><span>Local Path</span><div id="detail-path" class="path-display"></div></div>
        </div>
      </div>
    </section>
    <section class="card" style="margin-top:18px;">
      <div class="section-head">
        <div>
          <h2 style="font-size:24px; margin-bottom:0;">Measurement Explorer</h2>
          <div class="footnote">Search normalized injury, intrusion, dummy clearance, restraint timing, and other parsed result rows across the full PDF survey.</div>
        </div>
        <button id="export-result-csv" class="action-button" type="button">Export filtered CSV</button>
      </div>
      <div class="controls result-controls">
        <input id="result-search-box" type="text" placeholder="Search test code, vehicle, measure, location, table title" />
        <select id="result-type-filter"><option value="all">All result types</option></select>
        <select id="result-seat-filter"><option value="all">All seats</option></select>
        <select id="result-quality-filter"><option value="all">All quality states</option></select>
        <select id="result-scope-filter"><option value="all">All documents</option><option value="selected">Selected document only</option></select>
      </div>
      <div class="footnote" id="result-table-note"></div>
      <div class="table-shell" style="max-height:680px; margin-top:12px;">
        <table class="doc-table">
          <thead><tr><th>Test</th><th>Vehicle</th><th>Table</th><th>Seat</th><th>Section</th><th>Measure</th><th>Quality</th><th>Values</th><th>Page</th></tr></thead>
          <tbody id="result-row-body"></tbody>
        </table>
      </div>
    </section>
  </div>
  <script id="dashboard-data" type="application/json">__DATA_JSON__</script>
  <script>
    const dashboard = JSON.parse(document.getElementById("dashboard-data").textContent);
    const palette = ["#bc4b32","#0f7173","#785589","#c97c10","#2f6690","#6d9f71","#ba6f8b","#495057"];
    const resultRowLimit = 500;
    const commonMeasureLimit = 250;
    const tableTypeLabels = { head_injury:"Head injury", neck_injury:"Neck injury", chest_injury:"Chest injury", leg_foot_injury:"Leg and foot injury", thigh_hip_injury:"Thigh and hip injury", intrusion:"Intrusion / deformation", dummy_clearance:"Dummy clearance", restraint_kinematics:"Restraint timing / kinematics" };
    const state = { search:"", role:"all", family:"all", side:"all", local:"present", selectedId: dashboard.documents.find((row) => row.local_exists)?.pdf_document_id ?? dashboard.documents[0]?.pdf_document_id ?? null, resultSearch:"", resultType:"all", resultSeat:"all", resultQuality:"all", resultScope:"all", commonType:"all", commonSearch:"" };
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => (char === "&" ? "&amp;" : char === "<" ? "&lt;" : char === ">" ? "&gt;" : char === '"' ? "&quot;" : "&#39;"));
    const fmt = (value, fallback="n/a") => value === null || value === undefined || value === "" ? fallback : value;
    const prettyTableType = (value) => tableTypeLabels[value] || String(value || "").replace(/_/g, " ");
    const docTables = (id) => dashboard.resultTablesByDocument[String(id)] ?? [];
    const docIndex = new Map(dashboard.documents.map((row) => [row.pdf_document_id, row]));
    const commonMeasureRows = dashboard.commonMeasureSummary || [];
    const resultRows = Object.entries(dashboard.resultTablesByDocument).flatMap(([documentId, tables]) => {
      const doc = docIndex.get(Number(documentId)) || {};
      return tables.flatMap((table) => (table.rows || []).map((row, index) => ({
        ...row,
        key: `${documentId}:${table.pdf_result_table_id}:${index}`,
        pdf_document_id: Number(documentId),
        test_code: doc.test_code || "",
        vehicle_make_model: doc.vehicle_make_model || doc.title || "",
        family_label: doc.family_label || "",
        report_test_side: doc.report_test_side || "",
        page_number: table.page_number,
        table_order: table.table_order,
        table_ref: table.table_ref || "",
        table_title: table.title || "",
        table_type: table.table_type,
        table_label: prettyTableType(table.table_type),
      })));
    });
    function populateFilters() {
      [["role-filter", dashboard.filters.roles],["family-filter", dashboard.filters.families],["side-filter", dashboard.filters.sides]].forEach(([id, values]) => {
        const select = document.getElementById(id);
        values.forEach((value) => { const option = document.createElement("option"); option.value = value; option.textContent = value; select.appendChild(option); });
      });
    }
    function populateResultFilters() {
      const typeFilter = document.getElementById("result-type-filter");
      [...new Set(resultRows.map((row) => row.table_type).filter(Boolean))].sort().forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = prettyTableType(value);
        typeFilter.appendChild(option);
      });
      const seatFilter = document.getElementById("result-seat-filter");
      [...new Set(resultRows.map((row) => row.seat_position).filter(Boolean))].sort().forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        seatFilter.appendChild(option);
      });
      const qualityFilter = document.getElementById("result-quality-filter");
      [...new Set(resultRows.map((row) => row.quality_status).filter(Boolean))].sort().forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        qualityFilter.appendChild(option);
      });
    }
    function populateCommonFilters() {
      const typeFilter = document.getElementById("common-type-filter");
      [...new Set(commonMeasureRows.map((row) => row.table_type).filter(Boolean))].sort().forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = prettyTableType(value);
        typeFilter.appendChild(option);
      });
    }
    function filteredDocuments() {
      const q = state.search.trim().toLowerCase();
      return dashboard.documents.filter((row) => {
        if (state.local === "present" && !row.local_exists) return false;
        if (state.local === "missing" && row.local_exists) return false;
        if (state.role !== "all" && row.pdf_role !== state.role) return false;
        if (state.family !== "all" && row.family_label !== state.family) return false;
        if (state.side !== "all" && row.report_test_side !== state.side) return false;
        if (!q) return true;
        return [row.test_code,row.title,row.vehicle_make_model,row.filename,row.vehicle_identification_number,row.protocol_or_vendor].join(" ").toLowerCase().includes(q);
      });
    }
    function selectedDocument() { return dashboard.documents.find((row) => row.pdf_document_id === state.selectedId) ?? null; }
    function renderFamilySummary() {
      const body = document.getElementById("family-summary-body"); body.innerHTML = "";
      dashboard.familySummary.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><strong>${esc(row.family_label)}</strong><div class="muted">${esc(row.family_key)}</div></td><td>${esc(row.source_kind)}</td><td>${row.document_count}</td><td>${row.locally_available_count}</td><td>${row.completed_count}</td><td>${fmt(row.avg_page_count)}</td><td>${fmt(row.avg_table_count)}</td><td>${fmt(row.avg_word_count)}</td><td>${fmt(row.avg_confidence)}</td>`;
        body.appendChild(tr);
      });
    }
    function renderResultSummary() {
      const body = document.getElementById("result-summary-body"); body.innerHTML = "";
      dashboard.resultSummary.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><strong>${esc(prettyTableType(row.table_type))}</strong><div class="muted">${esc(row.table_type)}</div></td><td>${esc(row.table_group)}</td><td>${row.document_count}</td><td>${row.table_count}</td><td>${row.row_count}</td>`;
        body.appendChild(tr);
      });
    }
    function commonMeasureLabel(row) {
      return row.section_label ? `${row.section_label} | ${row.display_label}` : row.display_label;
    }
    function filteredCommonMeasures() {
      const q = state.commonSearch.trim().toLowerCase();
      return commonMeasureRows.filter((row) => {
        if (state.commonType !== "all" && row.table_type !== state.commonType) return false;
        if (!q) return true;
        return [row.display_label,row.section_label,row.unit,row.seat_positions,row.sample_test_codes,prettyTableType(row.table_type)].join(" ").toLowerCase().includes(q);
      }).sort((left, right) => {
        if (right.document_count !== left.document_count) return right.document_count - left.document_count;
        if (right.row_count !== left.row_count) return right.row_count - left.row_count;
        return commonMeasureLabel(left).localeCompare(commonMeasureLabel(right));
      });
    }
    function syncResultControls() {
      document.getElementById("result-search-box").value = state.resultSearch;
      document.getElementById("result-type-filter").value = state.resultType;
      document.getElementById("result-seat-filter").value = state.resultSeat;
      document.getElementById("result-quality-filter").value = state.resultQuality;
      document.getElementById("result-scope-filter").value = state.resultScope;
    }
    function renderCommonMeasureSummary() {
      const rows = filteredCommonMeasures();
      const visibleRows = rows.slice(0, commonMeasureLimit);
      const body = document.getElementById("common-measure-body");
      const note = document.getElementById("common-table-note");
      body.innerHTML = "";
      note.textContent = rows.length > commonMeasureLimit ? `Showing first ${commonMeasureLimit} of ${rows.length} recurring measures. Narrow the filter to inspect more precisely.` : `Showing ${rows.length} recurring measures.`;
      visibleRows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><strong>${esc(prettyTableType(row.table_type))}</strong><div class="muted">${esc(row.table_type)}</div></td><td>${esc(row.section_label || "n/a")}</td><td><strong>${esc(row.display_label)}</strong><div class="muted">${esc(row.normalized_label)}</div></td><td>${esc(row.unit || "n/a")}</td><td>${esc(row.seat_positions || "n/a")}</td><td>${row.document_count}</td><td>${row.row_count}</td><td>${esc(row.sample_test_codes || "n/a")}</td>`;
        tr.onclick = () => {
          state.resultType = row.table_type;
          state.resultSearch = row.display_label;
          state.resultSeat = row.seat_positions && !row.seat_positions.includes(",") ? row.seat_positions : "all";
          syncResultControls();
          renderResultExplorer();
        };
        body.appendChild(tr);
      });
      if (!visibleRows.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = '<td colspan="8" class="muted">No common measures matched the current filters.</td>';
        body.appendChild(tr);
      }
    }
    function renderCommonMeasureChart() {
      const topRows = filteredCommonMeasures().slice(0, 12).reverse();
      Plotly.newPlot("common-measure-plot", [{
        type:"bar",
        orientation:"h",
        x:topRows.map((row) => row.document_count),
        y:topRows.map((row) => commonMeasureLabel(row)),
        marker:{ color:"#c97c10" },
        customdata:topRows.map((row) => [prettyTableType(row.table_type), row.row_count, row.unit || "n/a", row.seat_positions || "n/a"]),
        hovertemplate:"<b>%{y}</b><br>type=%{customdata[0]}<br>documents=%{x}<br>rows=%{customdata[1]}<br>unit=%{customdata[2]}<br>seats=%{customdata[3]}<extra></extra>"
      }], {
        margin:{ l:260,r:18,t:10,b:48 },
        paper_bgcolor:"#fffaf2",
        plot_bgcolor:"#fffdf8",
        font:{ family:"IBM Plex Sans, sans-serif", color:"#1d1814" },
        xaxis:{ title:"Documents", gridcolor:"rgba(0,0,0,.09)" }
      }, { responsive:true, displaylogo:false });
    }
    function renderTable() {
      const rows = filteredDocuments(); const body = document.getElementById("doc-body"); body.innerHTML = "";
      document.getElementById("table-note").textContent = `Showing ${rows.length} / ${dashboard.documents.length} documents`;
      if (!rows.some((row) => row.pdf_document_id === state.selectedId)) state.selectedId = rows[0]?.pdf_document_id ?? null;
      rows.forEach((row) => {
        const tr = document.createElement("tr"); if (row.pdf_document_id === state.selectedId) tr.className = "active";
        tr.innerHTML = `<td><strong>${esc(row.test_code)}</strong><div class="muted">${esc(row.filename)}</div></td><td>${esc(row.pdf_role)}</td><td>${esc(row.family_label)}</td><td><strong>${esc(row.vehicle_make_model || row.title)}</strong><div class="muted">${fmt(row.vehicle_year)}</div></td><td>${fmt(row.page_count)}</td><td><strong>${row.parsed_result_table_count}</strong><div class="muted">${row.parsed_result_row_count} rows</div></td><td>${esc(row.report_test_side || "n/a")}</td><td>${esc(row.local_exists ? row.extraction_status : "missing_local")}</td>`;
        tr.onclick = () => { state.selectedId = row.pdf_document_id; renderTable(); renderDetails(); renderResultExplorer(); };
        body.appendChild(tr);
      });
      if (!rows.length) { const tr = document.createElement("tr"); tr.innerHTML = '<td colspan="8" class="muted">No documents matched the current filters.</td>'; body.appendChild(tr); }
    }
"""
    html += """
    function detailFields(row) {
      return [
        ["VIN", row.vehicle_identification_number],
        ["Report date", row.report_tested_on || row.filegroup_tested_on],
        ["Protocol", row.report_test_protocol],
        ["Protocol version", row.report_test_protocol_version],
        ["Body type", row.report_body_type],
        ["Engine / transmission", row.report_engine_transmission],
        ["Speed target", row.report_speed_target_kmh ? `${row.report_speed_target_kmh} km/h` : ""],
        ["Overlap target", row.report_overlap_target_pct ? `${row.report_overlap_target_pct} %` : ""],
        ["Wheelbase", row.report_wheelbase_cm_manufacturer ? `${row.report_wheelbase_cm_manufacturer} cm` : ""],
        ["Measured curb weight", row.report_curb_weight_kg_measured ? `${row.report_curb_weight_kg_measured} kg` : ""],
        ["EDR vendor", row.edr_vendor || row.edr_vendor_family],
        ["EDR case", row.edr_case_number],
        ["EDR software", row.edr_software_version],
      ].filter((entry) => entry[1]);
    }
    function tableHasSeat(table) { return (table.rows || []).some((row) => row.seat_position); }
    function headersForTable(table) {
      const seatHeader = tableHasSeat(table) ? ["Seat"] : [];
      if (["head_injury","neck_injury","chest_injury"].includes(table.table_type)) return [...seatHeader, "Measure","Threshold","Result","Time (ms)"];
      if (table.table_type === "leg_foot_injury") return [...seatHeader, "Section","Measure","Threshold","Left","Left time","Right","Right time"];
      if (table.table_type === "thigh_hip_injury") return [...seatHeader, "Section","Measure","Left","Left time","Right","Right time"];
      if (table.table_type === "intrusion") return ["Location","Longitudinal","Lateral","Vertical","Resultant"];
      if (table.table_type === "dummy_clearance") return ["Code","Location","Measure","Unit"];
      if (table.table_type === "restraint_kinematics") return ["Event","Time (ms)"];
      return table.headers?.length ? table.headers : ["Value"];
    }
    function cellsForRow(table, row) {
      const seatCell = tableHasSeat(table) ? [row.seat_position] : [];
      if (["head_injury","neck_injury","chest_injury"].includes(table.table_type)) return [...seatCell, row.label,row.threshold_text,row.result_text,row.time_text];
      if (table.table_type === "leg_foot_injury") return [...seatCell, row.section_name,row.label,row.threshold_text,row.left_text,row.left_time_text,row.right_text,row.right_time_text];
      if (table.table_type === "thigh_hip_injury") return [...seatCell, row.section_name,row.label,row.left_text,row.left_time_text,row.right_text,row.right_time_text];
      if (table.table_type === "intrusion") return [row.label,row.longitudinal_text,row.lateral_text,row.vertical_text,row.resultant_text];
      if (table.table_type === "dummy_clearance") return [row.code,row.label,row.measure_text,row.unit];
      if (table.table_type === "restraint_kinematics") return [row.label,row.time_text];
      return Object.values(row).filter((value) => value !== undefined && value !== null && value !== "");
    }
    function joinParts(parts) { return parts.filter((value) => value !== undefined && value !== null && value !== "").join(" | "); }
    function qualityClass(value) {
      if (value === "ok") return "quality-pill quality-ok";
      if (value === "review") return "quality-pill quality-review";
      return "quality-pill quality-unknown";
    }
    function qualitySummary(row) {
      const status = row.quality_status || "unknown";
      const score = row.quality_score !== undefined ? `${Number(row.quality_score).toFixed(2)}` : "";
      const flags = (row.quality_flags || []).join(", ");
      return { status, score, flags };
    }
    function resultValueSummary(row) {
      if (["head_injury","neck_injury","chest_injury"].includes(row.table_type)) return joinParts([row.threshold_text ? `threshold ${row.threshold_text}` : "", row.result_text ? `result ${row.result_text}` : "", row.time_text ? `time ${row.time_text}` : ""]);
      if (row.table_type === "leg_foot_injury") return joinParts([row.threshold_text ? `threshold ${row.threshold_text}` : "", row.left_text ? `left ${row.left_text}${row.left_time_text ? ` @ ${row.left_time_text}` : ""}` : "", row.right_text ? `right ${row.right_text}${row.right_time_text ? ` @ ${row.right_time_text}` : ""}` : ""]);
      if (row.table_type === "thigh_hip_injury") return joinParts([row.left_text ? `left ${row.left_text}${row.left_time_text ? ` @ ${row.left_time_text}` : ""}` : "", row.right_text ? `right ${row.right_text}${row.right_time_text ? ` @ ${row.right_time_text}` : ""}` : ""]);
      if (row.table_type === "intrusion") return joinParts([row.longitudinal_text ? `long ${row.longitudinal_text}` : "", row.lateral_text ? `lat ${row.lateral_text}` : "", row.vertical_text ? `vert ${row.vertical_text}` : "", row.resultant_text ? `resultant ${row.resultant_text}` : ""]);
      if (row.table_type === "dummy_clearance") return joinParts([row.measure_text, row.unit]);
      if (row.table_type === "restraint_kinematics") return joinParts([row.time_text ? `time ${row.time_text}` : ""]);
      return joinParts([row.result_text, row.measure_text, row.left_text, row.right_text]);
    }
    function filteredResultRows() {
      const q = state.resultSearch.trim().toLowerCase();
      return resultRows.filter((row) => {
        if (state.resultScope === "selected" && row.pdf_document_id !== state.selectedId) return false;
        if (state.resultType !== "all" && row.table_type !== state.resultType) return false;
        if (state.resultSeat !== "all" && (row.seat_position || "") !== state.resultSeat) return false;
        if (state.resultQuality !== "all" && (row.quality_status || "") !== state.resultQuality) return false;
        if (!q) return true;
        return [row.test_code,row.vehicle_make_model,row.family_label,row.table_label,row.table_title,row.section_name,row.section_key,row.label,row.normalized_label,row.code,row.table_ref,row.quality_status,(row.quality_flags || []).join(" ")].join(" ").toLowerCase().includes(q);
      });
    }
    function csvEscape(value) {
      const text = String(value ?? "");
      return /[",\\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    }
    function exportFilteredResults() {
      const rows = filteredResultRows();
      const columns = [
        ["test_code", "test_code"],
        ["vehicle_make_model", "vehicle_make_model"],
        ["family_label", "family_label"],
        ["report_test_side", "report_test_side"],
        ["table_type", "table_type"],
        ["table_title", "table_title"],
        ["page_number", "page_number"],
        ["table_ref", "table_ref"],
        ["seat_position", "seat_position"],
        ["section_name", "section_name"],
        ["section_key", "section_key"],
        ["label", "label"],
        ["normalized_label", "normalized_label"],
        ["quality_status", "quality_status"],
        ["quality_score", "quality_score"],
        ["quality_flags", "quality_flags"],
        ["code", "code"],
        ["unit", "unit"],
        ["threshold_text", "threshold_text"],
        ["result_text", "result_text"],
        ["time_text", "time_text"],
        ["left_text", "left_text"],
        ["left_time_text", "left_time_text"],
        ["right_text", "right_text"],
        ["right_time_text", "right_time_text"],
        ["longitudinal_text", "longitudinal_text"],
        ["lateral_text", "lateral_text"],
        ["vertical_text", "vertical_text"],
        ["resultant_text", "resultant_text"],
        ["measure_text", "measure_text"],
      ];
      const lines = [
        columns.map(([, header]) => csvEscape(header)).join(","),
        ...rows.map((row) => columns.map(([key]) => csvEscape(row[key])).join(",")),
      ];
      const blob = new Blob([lines.join("\\n")], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "pdf_result_row_catalog_filtered.csv";
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    }
    function renderResultExplorer() {
      const rows = filteredResultRows();
      const visibleRows = rows.slice(0, resultRowLimit);
      const body = document.getElementById("result-row-body");
      const note = document.getElementById("result-table-note");
      body.innerHTML = "";
      note.textContent = rows.length > resultRowLimit ? `Showing first ${resultRowLimit} of ${rows.length} parsed rows. Narrow the filters to inspect a smaller slice.` : `Showing ${rows.length} parsed rows.`;
      visibleRows.forEach((row) => {
        const tr = document.createElement("tr");
        if (row.pdf_document_id === state.selectedId) tr.className = "result-active";
        const quality = qualitySummary(row);
        tr.innerHTML = `<td><strong>${esc(row.test_code || "n/a")}</strong><div class="muted">${esc(row.family_label || "")}</div></td><td><strong>${esc(row.vehicle_make_model || "n/a")}</strong><div class="muted">${esc(row.report_test_side || "n/a")}</div></td><td><strong>${esc(row.table_label)}</strong><div class="muted">${esc(row.table_title || "")}</div></td><td>${esc(row.seat_position || "n/a")}</td><td>${esc(row.section_name || "n/a")}</td><td><strong>${esc(row.label || row.code || "n/a")}</strong>${row.code && row.label ? `<div class="muted">${esc(row.code)}</div>` : ""}<div class="muted">${esc(row.normalized_label || "")}</div></td><td><span class="${qualityClass(quality.status)}">${esc(quality.status)}</span>${quality.score ? `<div class="muted">score ${esc(quality.score)}</div>` : ""}${quality.flags ? `<div class="muted">${esc(quality.flags)}</div>` : ""}</td><td>${esc(resultValueSummary(row) || "n/a")}</td><td>${esc(joinParts([row.page_number ? `p.${row.page_number}` : "", row.table_ref || ""])) || "n/a"}</td>`;
        tr.onclick = () => { state.selectedId = row.pdf_document_id; renderTable(); renderDetails(); renderResultExplorer(); };
        body.appendChild(tr);
      });
      if (!visibleRows.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = '<td colspan="9" class="muted">No parsed result rows matched the current filters.</td>';
        body.appendChild(tr);
      }
    }
    function renderParsedTables(tables) {
      if (!tables.length) return '<div class="muted">No normalized result tables were captured for this document.</div>';
      return tables.map((table) => {
        const headers = headersForTable(table);
        const body = table.rows.map((row) => `<tr>${cellsForRow(table, row).map((value) => `<td>${esc(fmt(value, ""))}</td>`).join("")}</tr>`).join("");
        return `<div class="parsed-block"><div class="parsed-head"><div><strong>${esc(table.title)}</strong><div class="parsed-meta">Page ${table.page_number} | ${esc(table.table_type)} | ${table.row_count} rows</div></div><div class="parsed-meta">${esc(table.table_ref || "")}</div></div><div class="table-shell" style="max-height:360px; border:none; border-radius:0;"><table class="parsed-table"><thead><tr>${headers.map((header) => `<th>${esc(header)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div></div>`;
      }).join("");
    }
    function renderDetails() {
      const row = selectedDocument(); const title = document.getElementById("detail-title"); const subtitle = document.getElementById("detail-subtitle");
      const chips = document.getElementById("detail-chips"); const preview = document.getElementById("detail-preview"); const headings = document.getElementById("detail-headings");
      const fields = document.getElementById("detail-fields"); const results = document.getElementById("detail-results"); const pathDisplay = document.getElementById("detail-path");
      if (!row) { title.textContent = "No selection"; subtitle.textContent = ""; chips.innerHTML = ""; preview.removeAttribute("src"); headings.textContent = ""; fields.textContent = ""; results.textContent = ""; pathDisplay.textContent = ""; return; }
      const tables = docTables(row.pdf_document_id);
      title.textContent = `${row.test_code} | ${row.vehicle_make_model || row.title}`; subtitle.textContent = `${row.family_label} | ${row.pdf_role} | ${fmt(row.page_count)} pages`; chips.innerHTML = "";
      [`Year: ${fmt(row.vehicle_year)}`,`Side: ${row.report_test_side || "n/a"}`,`PDF tables: ${fmt(row.total_table_count)}`,`Parsed tables: ${row.parsed_result_table_count}`,`Parsed rows: ${row.parsed_result_row_count}`,`Confidence: ${fmt(row.classification_confidence)}`].forEach((text) => { const chip = document.createElement("div"); chip.className = "chip"; chip.textContent = text; chips.appendChild(chip); });
      if (row.preview_rel) preview.src = row.preview_rel; else preview.removeAttribute("src");
      headings.innerHTML = `<div><strong>Page 1:</strong> ${esc(row.first_page_heading || "n/a")}</div><div class="footnote"><strong>Page 2:</strong> ${esc(row.second_page_heading || "n/a")}</div>`;
      const fieldRows = detailFields(row);
      fields.innerHTML = fieldRows.length ? fieldRows.map((entry) => `<div><strong>${esc(entry[0])}:</strong> ${esc(entry[1])}</div>`).join("") : '<div class="muted">No structured fields captured for this row.</div>';
      results.innerHTML = renderParsedTables(tables); pathDisplay.textContent = row.local_path || "n/a";
    }
    function renderCharts() {
      Plotly.newPlot("family-plot", [{ type:"bar", x:dashboard.chartData.familyLabels, y:dashboard.chartData.familyCounts, marker:{ color:palette }, customdata:dashboard.chartData.familyKinds, hovertemplate:"<b>%{x}</b><br>count=%{y}<br>kind=%{customdata}<extra></extra>" }], { margin:{ l:48,r:18,t:10,b:120 }, paper_bgcolor:"#fffaf2", plot_bgcolor:"#fffdf8", font:{ family:"IBM Plex Sans, sans-serif", color:"#1d1814" }, xaxis:{ tickangle:-35 }, yaxis:{ title:"Documents", gridcolor:"rgba(0,0,0,.09)" } }, { responsive:true, displaylogo:false });
      Plotly.newPlot("result-type-plot", [{ type:"bar", orientation:"h", x:dashboard.chartData.resultTypeDocCounts, y:dashboard.chartData.resultTypeLabels.map((value) => prettyTableType(value)), marker:{ color:"#0f7173" }, customdata:dashboard.chartData.resultTypeRowCounts, hovertemplate:"<b>%{y}</b><br>documents=%{x}<br>rows=%{customdata}<extra></extra>" }], { margin:{ l:220,r:18,t:10,b:48 }, paper_bgcolor:"#fffaf2", plot_bgcolor:"#fffdf8", font:{ family:"IBM Plex Sans, sans-serif", color:"#1d1814" }, xaxis:{ title:"Documents", gridcolor:"rgba(0,0,0,.09)" } }, { responsive:true, displaylogo:false });
      Plotly.newPlot("year-plot", [{ type:"bar", x:dashboard.chartData.yearLabels, y:dashboard.chartData.yearCounts, marker:{ color:"#785589" } }], { margin:{ l:48,r:18,t:10,b:60 }, paper_bgcolor:"#fffaf2", plot_bgcolor:"#fffdf8", font:{ family:"IBM Plex Sans, sans-serif", color:"#1d1814" }, yaxis:{ title:"Documents", gridcolor:"rgba(0,0,0,.09)" } }, { responsive:true, displaylogo:false });
      Plotly.newPlot("coverage-plot", [{ type:"bar", orientation:"h", x:dashboard.chartData.coverageRows.map((row) => row.count), y:dashboard.chartData.coverageRows.map((row) => row.label), marker:{ color:"#bc4b32" }, customdata:dashboard.chartData.coverageRows.map((row) => row.ratio), hovertemplate:"<b>%{y}</b><br>count=%{x}<br>coverage=%{customdata:.1%}<extra></extra>" }], { margin:{ l:150,r:18,t:10,b:48 }, paper_bgcolor:"#fffaf2", plot_bgcolor:"#fffdf8", font:{ family:"IBM Plex Sans, sans-serif", color:"#1d1814" }, xaxis:{ title:"Documents", gridcolor:"rgba(0,0,0,.09)" } }, { responsive:true, displaylogo:false });
    }
    document.getElementById("search-box").oninput = (event) => { state.search = event.target.value; renderTable(); renderDetails(); renderResultExplorer(); };
    document.getElementById("role-filter").onchange = (event) => { state.role = event.target.value; renderTable(); renderDetails(); renderResultExplorer(); };
    document.getElementById("family-filter").onchange = (event) => { state.family = event.target.value; renderTable(); renderDetails(); renderResultExplorer(); };
    document.getElementById("side-filter").onchange = (event) => { state.side = event.target.value; renderTable(); renderDetails(); renderResultExplorer(); };
    document.getElementById("local-filter").onchange = (event) => { state.local = event.target.value; renderTable(); renderDetails(); renderResultExplorer(); };
    document.getElementById("result-search-box").oninput = (event) => { state.resultSearch = event.target.value; renderResultExplorer(); };
    document.getElementById("result-type-filter").onchange = (event) => { state.resultType = event.target.value; renderResultExplorer(); };
    document.getElementById("result-seat-filter").onchange = (event) => { state.resultSeat = event.target.value; renderResultExplorer(); };
    document.getElementById("result-quality-filter").onchange = (event) => { state.resultQuality = event.target.value; renderResultExplorer(); };
    document.getElementById("result-scope-filter").onchange = (event) => { state.resultScope = event.target.value; renderResultExplorer(); };
    document.getElementById("export-result-csv").onclick = () => { exportFilteredResults(); };
    document.getElementById("common-type-filter").onchange = (event) => { state.commonType = event.target.value; renderCommonMeasureSummary(); renderCommonMeasureChart(); };
    document.getElementById("common-search-box").oninput = (event) => { state.commonSearch = event.target.value; renderCommonMeasureSummary(); renderCommonMeasureChart(); };
    populateFilters(); populateResultFilters(); populateCommonFilters(); renderFamilySummary(); renderResultSummary(); renderCommonMeasureSummary(); renderCharts(); renderCommonMeasureChart(); renderTable(); renderDetails(); renderResultExplorer();
  </script>
</body>
</html>
"""
    return html.replace("__DATA_JSON__", data_json).replace("__CARDS__", cards_html).replace("__AVG_PAGES__", str(summary["avg_pages"] or "n/a"))


def main() -> None:
    args = parse_args()
    db_path = resolve_path(args.db)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    data = build_dashboard_data(connection, output_dir)
    output_path = output_dir / "index.html"
    output_path.write_text(dashboard_html(data), encoding="utf-8")
    print(json.dumps({"dashboard_html": str(output_path), "document_count": len(data["documents"])}, ensure_ascii=False, indent=2))
    connection.close()


if __name__ == "__main__":
    main()
