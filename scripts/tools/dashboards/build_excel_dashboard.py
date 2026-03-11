from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.core.catalog import excel_catalog_schema


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "small_overlap" / "dashboard" / "excel_catalog"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a static HTML dashboard for the Excel ETL catalog.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def rounded(value: Any, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def load_workbooks(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT excel_workbook_id, filegroup_id, test_code, filegroup_title, tested_on, test_type_label,
               vehicle_year, vehicle_make_model, workbook_type, extraction_status, notes, filename,
               local_path, folder_path, sheet_count, total_sheet_rows, metric_count, namespace_count,
               distinct_metric_count, avg_confidence, namespace_counts
          FROM excel_workbook_inventory
         ORDER BY test_code, workbook_type, filename
        """
    ).fetchall()
    return [
        {
            "excel_workbook_id": row["excel_workbook_id"],
            "filegroup_id": row["filegroup_id"],
            "test_code": row["test_code"],
            "filegroup_title": row["filegroup_title"],
            "tested_on": row["tested_on"] or "",
            "test_type_label": row["test_type_label"] or "",
            "vehicle_year": row["vehicle_year"],
            "vehicle_make_model": row["vehicle_make_model"] or "",
            "workbook_type": row["workbook_type"] or "unknown",
            "extraction_status": row["extraction_status"],
            "notes": row["notes"] or "",
            "filename": row["filename"],
            "local_path": row["local_path"] or "",
            "folder_path": row["folder_path"] or "",
            "sheet_count": row["sheet_count"],
            "total_sheet_rows": row["total_sheet_rows"],
            "metric_count": row["metric_count"],
            "namespace_count": row["namespace_count"],
            "distinct_metric_count": row["distinct_metric_count"],
            "avg_confidence": rounded(row["avg_confidence"], 3),
            "namespace_counts": row["namespace_counts"] or "",
        }
        for row in rows
    ]


def load_workbook_type_summary(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT workbook_type,
               COUNT(*) AS workbook_count,
               SUM(CASE WHEN extraction_status = 'done' THEN 1 ELSE 0 END) AS done_count,
               SUM(CASE WHEN extraction_status = 'skipped' THEN 1 ELSE 0 END) AS skipped_count,
               ROUND(AVG(sheet_count), 2) AS avg_sheet_count,
               ROUND(AVG(metric_count), 2) AS avg_metric_count,
               MAX(metric_count) AS max_metric_count
          FROM excel_workbook_inventory
         GROUP BY workbook_type
         ORDER BY workbook_count DESC, workbook_type
        """
    ).fetchall()
    return [dict(row) for row in rows]


def load_metric_summary(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT workbook_type, namespace, metric_name, metric_unit, metric_count, workbook_count,
               filegroup_count, avg_confidence, min_value_number, max_value_number, sample_test_codes
          FROM excel_metric_summary
         ORDER BY workbook_count DESC, metric_count DESC, workbook_type, namespace, metric_name
        """
    ).fetchall()
    return [
        {
            "workbook_type": row["workbook_type"],
            "namespace": row["namespace"],
            "metric_name": row["metric_name"],
            "metric_unit": row["metric_unit"] or "",
            "metric_count": row["metric_count"],
            "workbook_count": row["workbook_count"],
            "filegroup_count": row["filegroup_count"],
            "avg_confidence": rounded(row["avg_confidence"], 3),
            "min_value_number": rounded(row["min_value_number"], 3),
            "max_value_number": rounded(row["max_value_number"], 3),
            "sample_test_codes": row["sample_test_codes"] or "",
        }
        for row in rows
    ]


METRIC_ROW_COLUMNS = [
    "excel_workbook_id",
    "namespace",
    "metric_name",
    "metric_value_text",
    "metric_value_number",
    "metric_unit",
    "confidence",
    "extraction_method",
    "source_locator",
    "sheet_name",
]


def load_metric_rows(connection: sqlite3.Connection) -> list[list[Any]]:
    rows = connection.execute(
        """
        SELECT excel_workbook_id, namespace, metric_name, metric_value_text, metric_value_number,
               metric_unit, confidence, extraction_method, source_locator, sheet_name
          FROM excel_metric_catalog
         ORDER BY excel_workbook_id, extracted_metric_id
        """
    ).fetchall()
    return [
        [
            row["excel_workbook_id"],
            row["namespace"],
            row["metric_name"],
            row["metric_value_text"] or "",
            rounded(row["metric_value_number"], 3),
            row["metric_unit"] or "",
            rounded(row["confidence"], 3),
            row["extraction_method"] or "",
            row["source_locator"] or "",
            row["sheet_name"] or "",
        ]
        for row in rows
    ]


def build_dashboard_data(connection: sqlite3.Connection) -> dict[str, Any]:
    workbooks = load_workbooks(connection)
    workbook_type_summary = load_workbook_type_summary(connection)
    metric_summary = load_metric_summary(connection)
    metric_rows = load_metric_rows(connection)
    metric_row_count = len(metric_rows)
    namespace_totals: dict[str, int] = defaultdict(int)
    for row in metric_summary:
        namespace_totals[row["namespace"]] += int(row["metric_count"])
    summary = {
        "total_workbooks": len(workbooks),
        "done_workbooks": sum(1 for row in workbooks if row["extraction_status"] == "done"),
        "skipped_workbooks": sum(1 for row in workbooks if row["extraction_status"] == "skipped"),
        "filegroup_count": len({row["filegroup_id"] for row in workbooks}),
        "sheet_count": sum(int(row["sheet_count"] or 0) for row in workbooks),
        "metric_row_count": metric_row_count,
        "workbooks_with_metrics": sum(1 for row in workbooks if row["metric_count"]),
    }
    chart_data = {
        "typeLabels": [row["workbook_type"] for row in workbook_type_summary],
        "typeCounts": [row["workbook_count"] for row in workbook_type_summary],
        "typeMetricAverages": [row["avg_metric_count"] for row in workbook_type_summary],
        "namespaceLabels": [name for name, _ in sorted(namespace_totals.items(), key=lambda item: item[1], reverse=True)],
        "namespaceCounts": [count for _, count in sorted(namespace_totals.items(), key=lambda item: item[1], reverse=True)],
        "commonMetricLabels": [f"{row['namespace']} | {row['metric_name']}" for row in reversed(metric_summary[:12])],
        "commonMetricCounts": [row["workbook_count"] for row in reversed(metric_summary[:12])],
    }
    return {
        "summary": summary,
        "workbooks": workbooks,
        "workbookTypeSummary": workbook_type_summary,
        "metricSummary": metric_summary,
        "metricRowColumns": METRIC_ROW_COLUMNS,
        "metricRows": metric_rows[:2000],
        "metricRowCount": metric_row_count,
        "metricCatalogCsv": "excel_metric_catalog.csv",
        "chartData": chart_data,
        "filters": {
            "workbookTypes": sorted({row["workbook_type"] for row in workbooks}),
            "namespaces": sorted({row["namespace"] for row in metric_summary}),
            "statuses": sorted({row["extraction_status"] for row in workbooks}),
        },
    }


def dashboard_html(data: dict[str, Any]) -> str:
    summary = data["summary"]
    data_json = json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")
    cards = "".join(
        f'<div class="pill"><span>{label}</span><strong>{value}</strong></div>'
        for label, value in (
            ("Workbooks", summary["total_workbooks"]),
            ("Done", summary["done_workbooks"]),
            ("Skipped", summary["skipped_workbooks"]),
            ("Filegroups", summary["filegroup_count"]),
            ("Sheets", summary["sheet_count"]),
            ("Metric rows", summary["metric_row_count"]),
            ("With metrics", summary["workbooks_with_metrics"]),
        )
    )
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>IIHS Excel Catalog Dashboard</title>
  <link rel="icon" href="data:,">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root{--bg:#f3ede3;--card:#fffaf2;--surface:#fffdf8;--muted:#6a6054;--ink:#1d1814;--line:rgba(0,0,0,.09);--accent:#bc4b32;--accent2:#0f7173;--accent3:#785589}
    *{box-sizing:border-box} body{margin:0;color:var(--ink);font-family:"IBM Plex Sans","Segoe UI",sans-serif;background:radial-gradient(circle at top left, rgba(188,75,50,.10), transparent 28%),radial-gradient(circle at top right, rgba(15,113,115,.10), transparent 32%),linear-gradient(180deg,#f8f3ea 0%,#f3ede3 100%)}
    .page{max-width:1680px;margin:0 auto;padding:26px}.hero,.charts,.explorer{display:grid;gap:18px}.hero{grid-template-columns:1.1fr .9fr}.charts{grid-template-columns:repeat(2,minmax(0,1fr))}.explorer{grid-template-columns:1fr 1fr}.card{background:rgba(255,250,242,.94);border:1px solid var(--line);border-radius:22px;box-shadow:0 12px 32px rgba(29,24,20,.08);padding:20px 22px}
    .eyebrow{font-family:"Space Grotesk",sans-serif;text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:var(--muted);margin-bottom:10px} h1,h2{font-family:"Space Grotesk",sans-serif;margin:0;line-height:1.08} h1{font-size:clamp(34px,4vw,56px);margin-bottom:12px}.copy{color:#322a22;line-height:1.6;font-size:15px}
    .grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:18px}.pill{background:#f5edde;border:1px solid var(--line);border-radius:16px;padding:12px 14px}.pill span{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px}.pill strong{font-size:22px}
    .note{background:linear-gradient(135deg,rgba(188,75,50,.08),rgba(15,113,115,.05));border-radius:18px;border:1px solid var(--line);padding:16px}.note+.note{margin-top:12px}.note strong{display:block;margin-bottom:8px;font-family:"Space Grotesk",sans-serif;font-size:18px}.note a{color:var(--accent2);text-decoration:none;font-weight:600}
    .controls{display:grid;grid-template-columns:1.5fr repeat(4,minmax(0,1fr));gap:10px;margin:14px 0}.metric-controls{grid-template-columns:1.8fr repeat(3,minmax(0,1fr))}.controls input,.controls select{width:100%;padding:12px 14px;border-radius:14px;border:1px solid var(--line);background:#fffdf8;font:inherit}
    .table-shell{max-height:620px;overflow:auto;border:1px solid var(--line);border-radius:18px;background:#fffdf8}.table{width:100%;border-collapse:collapse;font-size:14px}.table th,.table td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}.table th{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);position:sticky;top:0;background:#fffaf2}
    .table tbody tr{cursor:pointer;transition:background .14s ease}.table tbody tr:hover{background:#f7efe4}.table tbody tr.active{background:#241d17;color:#fff8ef}.table tbody tr.active .muted{color:rgba(255,248,239,.72)}.table tbody tr.focus{background:#f5edde}.muted,.footnote,.path{color:var(--muted);font-size:13px}.path{word-break:break-all;color:var(--accent2)}
    .chips{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}.chip{background:#f5edde;border:1px solid var(--line);border-radius:14px;padding:8px 10px;font-size:13px;color:var(--muted)}
    .detail{display:grid;gap:10px}.detail-box{padding:12px 14px;border:1px solid var(--line);border-radius:16px;background:#fffdf8}.detail-box span{display:block;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
    .plot{height:330px}.action{border:1px solid var(--line);background:#1d1814;color:#fff8ef;border-radius:999px;padding:11px 16px;font:600 13px "IBM Plex Sans",sans-serif;cursor:pointer}
    @media (max-width:1320px){.hero,.charts,.explorer{grid-template-columns:1fr}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.controls,.metric-controls{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="card">
        <div class="eyebrow">IIHS Research Database</div>
        <h1>Excel Catalog Dashboard</h1>
        <div class="copy">Workbook-level ETL output from <code>excel_workbooks</code>, <code>excel_sheets</code>, and <code>extracted_metrics</code> is exposed here as workbook inventory, recurring metric summary, and row-level metric explorer.</div>
        <div class="grid">__CARDS__</div>
      </div>
      <div class="card">
        <div class="note">
          <strong>Scope</strong>
          <div>Summary, intrusion, UMTRI, DAS, environment, and generic workbook artifacts are normalized into a queryable catalog.</div>
          <div class="footnote">Select a workbook below or use the metric explorer to scan the entire Excel ETL layer.</div>
        </div>
        <div class="note">
          <strong>Cross-catalog</strong>
          <div>PDF and Excel result tables can now be reviewed side by side from the same research database.</div>
          <div class="footnote"><a href="../pdf_catalog/index.html">Open PDF catalog dashboard</a></div>
        </div>
      </div>
    </section>
    <section class="charts">
      <div class="card"><h2 style="font-size:24px; margin-bottom:12px;">Workbook Type Coverage</h2><div id="type-plot" class="plot"></div></div>
      <div class="card"><h2 style="font-size:24px; margin-bottom:12px;">Namespace Volume</h2><div id="namespace-plot" class="plot"></div></div>
      <div class="card"><h2 style="font-size:24px; margin-bottom:12px;">Average Metrics per Workbook</h2><div id="avg-plot" class="plot"></div></div>
      <div class="card"><h2 style="font-size:24px; margin-bottom:12px;">Most Reused Metrics</h2><div id="common-plot" class="plot"></div></div>
    </section>
    <section class="card" style="margin-top:18px;">
      <h2 style="font-size:24px; margin-bottom:12px;">Workbook Type Summary</h2>
      <div class="table-shell" style="max-height:280px;"><table class="table"><thead><tr><th>Type</th><th>Workbooks</th><th>Done</th><th>Skipped</th><th>Avg Sheets</th><th>Avg Metrics</th><th>Max Metrics</th></tr></thead><tbody id="type-body"></tbody></table></div>
    </section>
    <section class="card" style="margin-top:18px;">
      <h2 style="font-size:24px; margin-bottom:12px;">Common Metric Summary</h2>
      <div class="controls"><select id="summary-type-filter"><option value="all">All workbook types</option></select><input id="summary-search-box" type="text" placeholder="Search namespace, metric name, sample test codes" /><div></div><div></div><div></div></div>
      <div class="footnote" id="summary-note"></div>
      <div class="table-shell" style="max-height:320px;"><table class="table"><thead><tr><th>Type</th><th>Namespace</th><th>Metric</th><th>Unit</th><th>Workbooks</th><th>Rows</th><th>Avg Conf</th><th>Samples</th></tr></thead><tbody id="summary-body"></tbody></table></div>
    </section>
    <section class="explorer" style="margin-top:18px;">
      <div class="card">
        <h2 style="font-size:24px; margin-bottom:12px;">Workbook Explorer</h2>
        <div class="controls"><input id="search-box" type="text" placeholder="Search test code, vehicle, filename, folder" /><select id="type-filter"><option value="all">All workbook types</option></select><select id="status-filter"><option value="all">All statuses</option></select><select id="metrics-filter"><option value="all">All workbooks</option><option value="with_metrics">With metrics</option><option value="without_metrics">Without metrics</option></select><select id="namespace-filter"><option value="all">All namespace mixes</option></select></div>
        <div class="footnote" id="workbook-note"></div>
        <div class="table-shell"><table class="table"><thead><tr><th>Test</th><th>Type</th><th>Vehicle</th><th>Sheets</th><th>Metrics</th><th>Status</th></tr></thead><tbody id="workbook-body"></tbody></table></div>
      </div>
      <div class="card">
        <div class="eyebrow">Selected Workbook</div>
        <h2 id="detail-title" style="font-size:28px;"></h2>
        <div id="detail-subtitle" class="muted" style="margin-top:6px;"></div>
        <div id="detail-chips" class="chips"></div>
        <div class="detail">
          <div class="detail-box"><span>Workbook Fields</span><div id="detail-fields"></div></div>
          <div class="detail-box"><span>Namespace Coverage</span><div id="detail-namespaces"></div></div>
          <div class="detail-box"><span>Parser Notes</span><div id="detail-notes"></div></div>
          <div class="detail-box"><span>Local Path</span><div id="detail-path" class="path"></div></div>
        </div>
      </div>
    </section>
    <section class="card" style="margin-top:18px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;">
        <div><h2 style="font-size:24px; margin-bottom:0;">Metric Explorer</h2><div class="footnote">Search normalized metric rows across the full Excel ETL catalog.</div></div>
        <div style="display:flex; gap:10px; flex-wrap:wrap;"><button id="load-full-catalog" class="action" type="button">Load full catalog</button><button id="export-metric-csv" class="action" type="button">Export filtered CSV</button></div>
      </div>
      <div class="controls metric-controls"><input id="metric-search-box" type="text" placeholder="Search test code, metric name, value, sheet, source" /><select id="metric-type-filter"><option value="all">All workbook types</option></select><select id="metric-namespace-filter"><option value="all">All namespaces</option></select><select id="metric-scope-filter"><option value="all">All workbooks</option><option value="selected">Selected workbook only</option></select></div>
      <div class="footnote" id="metric-note"></div>
      <div class="table-shell" style="max-height:680px;"><table class="table"><thead><tr><th>Test</th><th>Workbook</th><th>Namespace</th><th>Metric</th><th>Value</th><th>Confidence</th><th>Source</th></tr></thead><tbody id="metric-body"></tbody></table></div>
    </section>
  </div>
  <script id="dashboard-data" type="application/json">__DATA_JSON__</script>
  <script>
    const dashboard = JSON.parse(document.getElementById("dashboard-data").textContent);
    const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => (char === "&" ? "&amp;" : char === "<" ? "&lt;" : char === ">" ? "&gt;" : char === '"' ? "&quot;" : "&#39;"));
    const fmt = (value, fallback="n/a") => value === null || value === undefined || value === "" ? fallback : value;
    const palette = ["#bc4b32","#0f7173","#785589","#c97c10","#2f6690","#6d9f71","#ba6f8b","#495057"];
    const rowLimit = 500;
    const summaryLimit = 250;
    const state = { search:"", type:"all", status:"all", metrics:"all", namespaceMix:"all", selectedId: dashboard.workbooks[0]?.excel_workbook_id ?? null, summaryType:"all", summarySearch:"", metricSearch:"", metricType:"all", metricNamespace:"all", metricScope:"all" };
    const workbookIndex = new Map(dashboard.workbooks.map((row) => [row.excel_workbook_id, row]));
    const metricColumns = dashboard.metricRowColumns;
    let metricRowsLoaded = false;
    let metricLoadError = "";
    let metricRows = dashboard.metricRows.map((row, index) => {
      const entry = Object.fromEntries(metricColumns.map((key, columnIndex) => [key, row[columnIndex]]));
      return { ...entry, key:`preview:${entry.excel_workbook_id}:${index}`, ...workbookIndex.get(entry.excel_workbook_id) };
    });
    const formatMetricName = (value) => String(value || "").replace(/_/g, " ").replace(/\\b\\w/g, (match) => match.toUpperCase());
    const formatValue = (row) => row.metric_value_text ? `${row.metric_value_text}${row.metric_unit ? ` ${row.metric_unit}` : ""}` : row.metric_value_number !== null && row.metric_value_number !== undefined ? `${row.metric_value_number}${row.metric_unit ? ` ${row.metric_unit}` : ""}` : "";
    function parseCsv(text) {
      const rows = [];
      let row = [];
      let value = "";
      let inQuotes = false;
      for (let index = 0; index < text.length; index += 1) {
        const char = text[index];
        const next = text[index + 1];
        if (char === '"') {
          if (inQuotes && next === '"') { value += '"'; index += 1; }
          else { inQuotes = !inQuotes; }
          continue;
        }
        if (char === "," && !inQuotes) { row.push(value); value = ""; continue; }
        if ((char === "\\n" || char === "\\r") && !inQuotes) {
          if (char === "\\r" && next === "\\n") index += 1;
          row.push(value);
          rows.push(row);
          row = [];
          value = "";
          continue;
        }
        value += char;
      }
      if (value !== "" || row.length) { row.push(value); rows.push(row); }
      return rows.filter((entry) => entry.length && entry.some((cell) => cell !== ""));
    }
    async function loadFullMetricRows() {
      try {
        const response = await fetch(dashboard.metricCatalogCsv, { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const parsed = parseCsv(await response.text());
        const headers = parsed[0] || [];
        const headerIndex = Object.fromEntries(headers.map((header, index) => [header, index]));
        metricRows = parsed.slice(1).map((cells, index) => {
          const excelWorkbookId = Number(cells[headerIndex.excel_workbook_id] || 0);
          const workbook = workbookIndex.get(excelWorkbookId) || {};
          return {
            excel_workbook_id: excelWorkbookId,
            namespace: cells[headerIndex.namespace] || "",
            metric_name: cells[headerIndex.metric_name] || "",
            metric_value_text: cells[headerIndex.metric_value_text] || "",
            metric_value_number: cells[headerIndex.metric_value_number] ? Number(cells[headerIndex.metric_value_number]) : null,
            metric_unit: cells[headerIndex.metric_unit] || "",
            confidence: cells[headerIndex.confidence] ? Number(cells[headerIndex.confidence]) : null,
            extraction_method: cells[headerIndex.extraction_method] || "",
            source_locator: cells[headerIndex.source_locator] || "",
            sheet_name: cells[headerIndex.sheet_name] || "",
            key: `full:${excelWorkbookId}:${index}`,
            ...workbook,
          };
        });
        metricRowsLoaded = true;
        metricLoadError = "";
      } catch (error) {
        metricLoadError = String(error);
      }
      renderMetricRows();
    }
    function filteredWorkbooks() {
      const q = state.search.trim().toLowerCase();
      return dashboard.workbooks.filter((row) => {
        if (state.type !== "all" && row.workbook_type !== state.type) return false;
        if (state.status !== "all" && row.extraction_status !== state.status) return false;
        if (state.metrics === "with_metrics" && !row.metric_count) return false;
        if (state.metrics === "without_metrics" && row.metric_count) return false;
        if (state.namespaceMix !== "all" && row.namespace_counts !== state.namespaceMix) return false;
        if (!q) return true;
        return [row.test_code,row.vehicle_make_model,row.filename,row.folder_path,row.workbook_type,row.namespace_counts].join(" ").toLowerCase().includes(q);
      });
    }
    function filteredMetricSummary() {
      const q = state.summarySearch.trim().toLowerCase();
      return dashboard.metricSummary.filter((row) => {
        if (state.summaryType !== "all" && row.workbook_type !== state.summaryType) return false;
        if (!q) return true;
        return [row.workbook_type,row.namespace,row.metric_name,row.metric_unit,row.sample_test_codes].join(" ").toLowerCase().includes(q);
      });
    }
    function filteredMetricRows() {
      const q = state.metricSearch.trim().toLowerCase();
      return metricRows.filter((row) => {
        if (state.metricScope === "selected" && row.excel_workbook_id !== state.selectedId) return false;
        if (state.metricType !== "all" && row.workbook_type !== state.metricType) return false;
        if (state.metricNamespace !== "all" && row.namespace !== state.metricNamespace) return false;
        if (!q) return true;
        return [row.test_code,row.vehicle_make_model,row.filename,row.workbook_type,row.namespace,row.metric_name,row.metric_value_text,row.metric_value_number,row.metric_unit,row.sheet_name,row.source_locator,row.extraction_method].join(" ").toLowerCase().includes(q);
      });
    }
    function renderTypeSummary() {
      const body = document.getElementById("type-body"); body.innerHTML = "";
      dashboard.workbookTypeSummary.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><strong>${esc(row.workbook_type)}</strong></td><td>${row.workbook_count}</td><td>${row.done_count}</td><td>${row.skipped_count}</td><td>${fmt(row.avg_sheet_count)}</td><td>${fmt(row.avg_metric_count)}</td><td>${fmt(row.max_metric_count)}</td>`;
        body.appendChild(tr);
      });
    }
    function renderMetricSummary() {
      const rows = filteredMetricSummary().sort((a, b) => b.workbook_count - a.workbook_count || b.metric_count - a.metric_count || a.metric_name.localeCompare(b.metric_name));
      const visible = rows.slice(0, summaryLimit);
      document.getElementById("summary-note").textContent = rows.length > summaryLimit ? `Showing first ${summaryLimit} of ${rows.length} recurring metrics.` : `Showing ${rows.length} recurring metrics.`;
      const body = document.getElementById("summary-body"); body.innerHTML = "";
      visible.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><strong>${esc(row.workbook_type)}</strong></td><td>${esc(row.namespace)}</td><td><strong>${esc(formatMetricName(row.metric_name))}</strong><div class="muted">${esc(row.metric_name)}</div></td><td>${esc(row.metric_unit || "n/a")}</td><td>${row.workbook_count}</td><td>${row.metric_count}</td><td>${fmt(row.avg_confidence)}</td><td>${esc(row.sample_test_codes || "n/a")}</td>`;
        tr.onclick = () => { state.metricType = row.workbook_type; state.metricNamespace = row.namespace; state.metricSearch = row.metric_name; syncMetricControls(); renderMetricRows(); };
        body.appendChild(tr);
      });
      if (!visible.length) body.innerHTML = '<tr><td colspan="8" class="muted">No recurring metrics matched the current filters.</td></tr>';
    }
    function renderWorkbooks() {
      const rows = filteredWorkbooks();
      document.getElementById("workbook-note").textContent = `Showing ${rows.length} / ${dashboard.workbooks.length} workbooks`;
      if (!rows.some((row) => row.excel_workbook_id === state.selectedId)) state.selectedId = rows[0]?.excel_workbook_id ?? null;
      const body = document.getElementById("workbook-body"); body.innerHTML = "";
      rows.forEach((row) => {
        const tr = document.createElement("tr");
        if (row.excel_workbook_id === state.selectedId) tr.className = "active";
        tr.innerHTML = `<td><strong>${esc(row.test_code)}</strong><div class="muted">${esc(row.filename)}</div></td><td>${esc(row.workbook_type)}</td><td><strong>${esc(row.vehicle_make_model || row.filegroup_title)}</strong><div class="muted">${fmt(row.vehicle_year)}</div></td><td><strong>${row.sheet_count}</strong><div class="muted">${row.total_sheet_rows} rows</div></td><td><strong>${row.metric_count}</strong><div class="muted">${row.namespace_count} namespaces</div></td><td>${esc(row.extraction_status)}</td>`;
        tr.onclick = () => { state.selectedId = row.excel_workbook_id; renderWorkbooks(); renderDetails(); renderMetricRows(); };
        body.appendChild(tr);
      });
      if (!rows.length) body.innerHTML = '<tr><td colspan="6" class="muted">No workbooks matched the current filters.</td></tr>';
    }
    function renderDetails() {
      const row = workbookIndex.get(state.selectedId);
      if (!row) { document.getElementById("detail-title").textContent = "No selection"; document.getElementById("detail-subtitle").textContent = ""; document.getElementById("detail-chips").innerHTML = ""; document.getElementById("detail-fields").textContent = ""; document.getElementById("detail-namespaces").textContent = ""; document.getElementById("detail-notes").textContent = ""; document.getElementById("detail-path").textContent = ""; return; }
      document.getElementById("detail-title").textContent = `${row.test_code} | ${row.filename}`;
      document.getElementById("detail-subtitle").textContent = `${row.workbook_type} | ${row.vehicle_make_model || row.filegroup_title}`;
      const chips = document.getElementById("detail-chips"); chips.innerHTML = "";
      [`Sheets: ${row.sheet_count}`,`Metrics: ${row.metric_count}`,`Namespaces: ${row.namespace_count}`,`Distinct metrics: ${row.distinct_metric_count}`,`Avg confidence: ${fmt(row.avg_confidence)}`].forEach((text) => { const chip = document.createElement("div"); chip.className = "chip"; chip.textContent = text; chips.appendChild(chip); });
      document.getElementById("detail-fields").innerHTML = [["Vehicle", row.vehicle_make_model],["Year", row.vehicle_year],["Test type", row.test_type_label],["Test date", row.tested_on],["Filegroup", row.filegroup_id]].filter((entry) => entry[1] !== null && entry[1] !== undefined && entry[1] !== "").map((entry) => `<div><strong>${esc(entry[0])}:</strong> ${esc(entry[1])}</div>`).join("") || '<div class="muted">No workbook fields available.</div>';
      document.getElementById("detail-namespaces").innerHTML = row.namespace_counts ? row.namespace_counts.split(", ").map((entry) => `<div>${esc(entry)}</div>`).join("") : '<div class="muted">No namespace metrics captured.</div>';
      document.getElementById("detail-notes").textContent = row.notes || "n/a";
      document.getElementById("detail-path").textContent = row.local_path || "n/a";
    }
    function syncMetricControls() {
      document.getElementById("metric-search-box").value = state.metricSearch;
      document.getElementById("metric-type-filter").value = state.metricType;
      document.getElementById("metric-namespace-filter").value = state.metricNamespace;
      document.getElementById("metric-scope-filter").value = state.metricScope;
    }
    function renderMetricRows() {
      const rows = filteredMetricRows();
      const visible = rows.slice(0, rowLimit);
      if (metricRowsLoaded) document.getElementById("metric-note").textContent = rows.length > rowLimit ? `Showing first ${rowLimit} of ${rows.length} metric rows from the full catalog.` : `Showing ${rows.length} metric rows from the full catalog.`;
      else if (metricLoadError) document.getElementById("metric-note").textContent = `Showing preview rows only (${metricRows.length} loaded in HTML, ${dashboard.metricRowCount} total in CSV). Full catalog load failed: ${metricLoadError}`;
      else document.getElementById("metric-note").textContent = `Showing preview rows only (${metricRows.length} loaded in HTML, ${dashboard.metricRowCount} total in CSV). Use "Load full catalog" for the complete metric table.`;
      const body = document.getElementById("metric-body"); body.innerHTML = "";
      visible.forEach((row) => {
        const tr = document.createElement("tr");
        if (row.excel_workbook_id === state.selectedId) tr.className = "focus";
        tr.innerHTML = `<td><strong>${esc(row.test_code || "n/a")}</strong><div class="muted">${esc(row.filename || "")}</div></td><td><strong>${esc(row.workbook_type || "n/a")}</strong><div class="muted">${esc(row.vehicle_make_model || row.filegroup_title || "n/a")}</div></td><td><strong>${esc(row.namespace || "n/a")}</strong><div class="muted">${esc(row.sheet_name || "workbook")}</div></td><td><strong>${esc(formatMetricName(row.metric_name))}</strong><div class="muted">${esc(row.metric_name || "")}</div></td><td>${esc(formatValue(row) || "n/a")}</td><td>${fmt(row.confidence)}</td><td>${esc(row.source_locator || "n/a")}<div class="muted">${esc(row.extraction_method || "")}</div></td>`;
        tr.onclick = () => { state.selectedId = row.excel_workbook_id; renderWorkbooks(); renderDetails(); renderMetricRows(); };
        body.appendChild(tr);
      });
      if (!visible.length) body.innerHTML = '<tr><td colspan="7" class="muted">No metric rows matched the current filters.</td></tr>';
    }
    function csvEscape(value) { const text = String(value ?? ""); return /[",\\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text; }
    function exportFiltered() {
      const columns = [["test_code","test_code"],["vehicle_make_model","vehicle_make_model"],["workbook_type","workbook_type"],["filename","filename"],["namespace","namespace"],["metric_name","metric_name"],["metric_value_text","metric_value_text"],["metric_value_number","metric_value_number"],["metric_unit","metric_unit"],["confidence","confidence"],["sheet_name","sheet_name"],["source_locator","source_locator"],["extraction_method","extraction_method"]];
      const lines = [columns.map(([, header]) => csvEscape(header)).join(","), ...filteredMetricRows().map((row) => columns.map(([key]) => csvEscape(row[key])).join(","))];
      const blob = new Blob([lines.join("\\n")], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = "excel_metric_catalog_filtered.csv"; document.body.appendChild(anchor); anchor.click(); document.body.removeChild(anchor); URL.revokeObjectURL(url);
    }
    function populateFilters() {
      [["type-filter", dashboard.filters.workbookTypes],["summary-type-filter", dashboard.filters.workbookTypes],["metric-type-filter", dashboard.filters.workbookTypes],["status-filter", dashboard.filters.statuses],["metric-namespace-filter", dashboard.filters.namespaces]].forEach(([id, values]) => {
        const select = document.getElementById(id); values.forEach((value) => { const option = document.createElement("option"); option.value = value; option.textContent = value; select.appendChild(option); });
      });
      const namespaceMix = document.getElementById("namespace-filter");
      [...new Set(dashboard.workbooks.map((row) => row.namespace_counts).filter(Boolean))].sort().forEach((value) => { const option = document.createElement("option"); option.value = value; option.textContent = value; namespaceMix.appendChild(option); });
    }
    function renderCharts() {
      Plotly.newPlot("type-plot", [{ type:"bar", x:dashboard.chartData.typeLabels, y:dashboard.chartData.typeCounts, marker:{ color:palette } }], { margin:{ l:48,r:18,t:10,b:80 }, paper_bgcolor:"#fffaf2", plot_bgcolor:"#fffdf8", font:{ family:"IBM Plex Sans, sans-serif", color:"#1d1814" }, xaxis:{ tickangle:-30 }, yaxis:{ title:"Workbooks", gridcolor:"rgba(0,0,0,.09)" } }, { responsive:true, displaylogo:false });
      Plotly.newPlot("namespace-plot", [{ type:"bar", orientation:"h", x:dashboard.chartData.namespaceCounts, y:dashboard.chartData.namespaceLabels, marker:{ color:"#0f7173" } }], { margin:{ l:170,r:18,t:10,b:48 }, paper_bgcolor:"#fffaf2", plot_bgcolor:"#fffdf8", font:{ family:"IBM Plex Sans, sans-serif", color:"#1d1814" }, xaxis:{ title:"Metric rows", gridcolor:"rgba(0,0,0,.09)" } }, { responsive:true, displaylogo:false });
      Plotly.newPlot("avg-plot", [{ type:"bar", x:dashboard.chartData.typeLabels, y:dashboard.chartData.typeMetricAverages, marker:{ color:"#785589" } }], { margin:{ l:48,r:18,t:10,b:80 }, paper_bgcolor:"#fffaf2", plot_bgcolor:"#fffdf8", font:{ family:"IBM Plex Sans, sans-serif", color:"#1d1814" }, xaxis:{ tickangle:-30 }, yaxis:{ title:"Average metrics", gridcolor:"rgba(0,0,0,.09)" } }, { responsive:true, displaylogo:false });
      Plotly.newPlot("common-plot", [{ type:"bar", orientation:"h", x:dashboard.chartData.commonMetricCounts, y:dashboard.chartData.commonMetricLabels, marker:{ color:"#c97c10" } }], { margin:{ l:250,r:18,t:10,b:48 }, paper_bgcolor:"#fffaf2", plot_bgcolor:"#fffdf8", font:{ family:"IBM Plex Sans, sans-serif", color:"#1d1814" }, xaxis:{ title:"Workbooks", gridcolor:"rgba(0,0,0,.09)" } }, { responsive:true, displaylogo:false });
    }
    document.getElementById("search-box").oninput = (event) => { state.search = event.target.value; renderWorkbooks(); renderDetails(); renderMetricRows(); };
    document.getElementById("type-filter").onchange = (event) => { state.type = event.target.value; renderWorkbooks(); renderDetails(); renderMetricRows(); };
    document.getElementById("status-filter").onchange = (event) => { state.status = event.target.value; renderWorkbooks(); renderDetails(); renderMetricRows(); };
    document.getElementById("metrics-filter").onchange = (event) => { state.metrics = event.target.value; renderWorkbooks(); renderDetails(); renderMetricRows(); };
    document.getElementById("namespace-filter").onchange = (event) => { state.namespaceMix = event.target.value; renderWorkbooks(); renderDetails(); renderMetricRows(); };
    document.getElementById("summary-type-filter").onchange = (event) => { state.summaryType = event.target.value; renderMetricSummary(); };
    document.getElementById("summary-search-box").oninput = (event) => { state.summarySearch = event.target.value; renderMetricSummary(); };
    document.getElementById("metric-search-box").oninput = (event) => { state.metricSearch = event.target.value; renderMetricRows(); };
    document.getElementById("metric-type-filter").onchange = (event) => { state.metricType = event.target.value; renderMetricRows(); };
    document.getElementById("metric-namespace-filter").onchange = (event) => { state.metricNamespace = event.target.value; renderMetricRows(); };
    document.getElementById("metric-scope-filter").onchange = (event) => { state.metricScope = event.target.value; renderMetricRows(); };
    document.getElementById("load-full-catalog").onclick = () => { document.getElementById("metric-note").textContent = `Loading ${dashboard.metricRowCount} metric rows from CSV...`; loadFullMetricRows(); };
    document.getElementById("export-metric-csv").onclick = () => { exportFiltered(); };
    populateFilters(); renderCharts(); renderTypeSummary(); renderMetricSummary(); renderWorkbooks(); renderDetails(); renderMetricRows();
  </script>
</body>
</html>
""".replace("__DATA_JSON__", data_json).replace("__CARDS__", cards)


def main() -> None:
    args = parse_args()
    db_path = resolve_path(args.db)
    output_dir = resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    excel_catalog_schema.ensure_excel_catalog_schema(connection)
    connection.commit()
    data = build_dashboard_data(connection)
    output_path = output_dir / "index.html"
    output_path.write_text(dashboard_html(data), encoding="utf-8")
    print(json.dumps({"dashboard_html": str(output_path), "workbook_count": len(data["workbooks"]), "metric_row_count": len(data["metricRows"])}, ensure_ascii=False, indent=2))
    connection.close()


if __name__ == "__main__":
    main()
