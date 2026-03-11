from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.core.signals.preprocess_known_signal_families import ensure_preprocessing_schema, resolve_repo_path
from scripts.tools.analytics.build_signal_feature_batch import ANALYSIS_WINDOW_END_S, ANALYSIS_WINDOW_START_S, crop_frame_to_analysis_window


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "small_overlap" / "dashboard" / "signal_catalog"
DEFAULT_SOURCE_MODE = "standard_baseline"
DEFAULT_FEATURE_SPACE = "official_known_harmonized_v5"
MAX_PLOT_POINTS = 1001
DEFAULT_CHANNELS = (
    "vehicle_longitudinal_accel_g",
    "vehicle_resultant_accel_g",
    "seat_mid_deflection_mm",
    "foot_left_x_accel_g",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a DB-backed signal catalog dashboard.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE)
    parser.add_argument("--feature-space", default=DEFAULT_FEATURE_SPACE)
    parser.add_argument("--max-plot-points", type=int, default=MAX_PLOT_POINTS)
    return parser.parse_args()


def rounded(value: Any, digits: int = 4) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        return None
    return round(numeric, digits)


def to_json_list(values: list[float], digits: int = 6) -> list[float | None]:
    output: list[float | None] = []
    for value in values:
        numeric = float(value)
        output.append(round(numeric, digits) if math.isfinite(numeric) else None)
    return output


def repo_relative(path: Path, start: Path) -> str:
    return Path(os.path.relpath(path, start=start)).as_posix()


def link_if_exists(target: Path, start: Path) -> str:
    return repo_relative(target, start) if target.exists() else ""


def infer_unit(column_name: str) -> str:
    if column_name.endswith("_g"):
        return "g"
    if column_name.endswith("_mm"):
        return "mm"
    if column_name.endswith("_s"):
        return "s"
    return ""


def downsample_stride(length: int, max_points: int) -> int:
    return 1 if length <= max_points else max(1, math.ceil(length / max_points))


def vehicle_display_label(vehicle_year: int | None, vehicle_make_model: str) -> str:
    if vehicle_year is not None and str(vehicle_make_model).startswith(str(vehicle_year)):
        return str(vehicle_make_model)
    if vehicle_year is None:
        return str(vehicle_make_model)
    return f"{vehicle_year} {vehicle_make_model}"


def summarize_series(time_values: list[float], values: list[float]) -> dict[str, Any]:
    series = pd.Series(values, dtype="float64")
    finite = series.dropna()
    if finite.empty:
        return {"sample_count": len(values), "min": None, "max": None, "mean": None, "std": None}
    return {
        "sample_count": len(values),
        "min": rounded(finite.min(), 6),
        "max": rounded(finite.max(), 6),
        "mean": rounded(finite.mean(), 6),
        "std": rounded(finite.std(ddof=0), 6),
    }


def resolve_feature_space_algorithms(connection: sqlite3.Connection, feature_space: str) -> dict[str, str]:
    algorithms: dict[str, str] = {}
    for table_name, key in (
        ("preprocessing_neighbors", "neighbor"),
        ("preprocessing_clusters", "cluster"),
        ("preprocessing_representatives", "representative"),
    ):
        row = connection.execute(
            f"""
            SELECT algorithm, COUNT(*) AS row_count
              FROM {table_name}
             WHERE feature_space = ?
             GROUP BY algorithm
             ORDER BY row_count DESC, algorithm
             LIMIT 1
            """,
            (feature_space,),
        ).fetchone()
        algorithms[key] = row["algorithm"] if row and row["algorithm"] else ""
    if not algorithms["representative"]:
        algorithms["representative"] = algorithms["cluster"]
    return algorithms


def load_case_rows(
    connection: sqlite3.Connection,
    source_mode: str,
    feature_space: str,
    cluster_algorithm: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT pc.preprocessing_case_id,
               pc.filegroup_id,
               pc.mode,
               pc.status,
               pc.manifest_path,
               pc.harmonized_wide_path,
               fg.test_code,
               v.vehicle_year,
               v.vehicle_make_model,
               fs.feature_count,
               fs.coverage_json,
               c.cluster_label,
               c.outlier_score,
               c.robust_distance_score,
               c.local_density_outlier_score,
               c.stability_score,
               c.coverage_score,
               c.is_outlier
          FROM preprocessing_cases pc
          JOIN filegroups fg ON fg.filegroup_id = pc.filegroup_id
          JOIN vehicles v ON v.vehicle_id = fg.vehicle_id
          JOIN preprocessing_feature_sets fs
            ON fs.preprocessing_case_id = pc.preprocessing_case_id
           AND fs.source_mode = ?
           AND fs.feature_space = ?
          LEFT JOIN preprocessing_clusters c
            ON c.preprocessing_feature_set_id = fs.preprocessing_feature_set_id
           AND c.feature_space = ?
           AND c.algorithm = ?
         WHERE pc.mode = ?
           AND pc.status = 'done'
           AND pc.harmonized_wide_path IS NOT NULL
         ORDER BY v.vehicle_year DESC, v.vehicle_make_model, fg.test_code
        """,
        (source_mode, feature_space, feature_space, cluster_algorithm, source_mode),
    ).fetchall()
    cases: list[dict[str, Any]] = []
    for row in rows:
        manifest_path = Path(row["manifest_path"]) if row["manifest_path"] else None
        case_slug = manifest_path.parent.name if manifest_path else f"{row['filegroup_id']}-{row['test_code']}"
        coverage = json.loads(row["coverage_json"]) if row["coverage_json"] else {}
        coverage_values = [float(value) for value in coverage.values() if isinstance(value, (int, float))]
        cases.append(
            {
                "preprocessing_case_id": int(row["preprocessing_case_id"]),
                "filegroup_id": int(row["filegroup_id"]),
                "mode": row["mode"],
                "status": row["status"],
                "test_code": row["test_code"],
                "vehicle_year": int(row["vehicle_year"]) if row["vehicle_year"] is not None else None,
                "vehicle_make_model": row["vehicle_make_model"],
                "vehicle_label": vehicle_display_label(row["vehicle_year"], row["vehicle_make_model"]),
                "case_label": f"{vehicle_display_label(row['vehicle_year'], row['vehicle_make_model'])} ({row['test_code']})",
                "case_slug": case_slug,
                "harmonized_wide_path": row["harmonized_wide_path"],
                "feature_count": int(row["feature_count"]) if row["feature_count"] is not None else 0,
                "coverage_mean": rounded(sum(coverage_values) / len(coverage_values), 4) if coverage_values else None,
                "cluster_label": int(row["cluster_label"]) if row["cluster_label"] is not None else None,
                "outlier_score": rounded(row["outlier_score"], 4),
                "robust_distance_score": rounded(row["robust_distance_score"], 4),
                "local_density_outlier_score": rounded(row["local_density_outlier_score"], 4),
                "stability_score": rounded(row["stability_score"], 4),
                "coverage_score": rounded(row["coverage_score"], 4),
                "is_outlier": bool(row["is_outlier"]) if row["is_outlier"] is not None else False,
            }
        )
    return cases


def load_neighbor_rows(
    connection: sqlite3.Connection,
    source_mode: str,
    feature_space: str,
    neighbor_algorithm: str,
) -> dict[str, list[dict[str, Any]]]:
    rows = connection.execute(
        """
        SELECT src.filegroup_id AS source_filegroup_id,
               tgt.filegroup_id AS target_filegroup_id,
               fg2.test_code AS target_test_code,
               v2.vehicle_year AS target_year,
               v2.vehicle_make_model AS target_vehicle,
               n.rank,
               n.similarity_score,
               n.distance_score,
               n.weighted_correlation,
               n.dtw_distance,
               n.overlap_channel_count,
               n.multiview_score,
               n.pulse_phase_score
          FROM preprocessing_neighbors n
          JOIN preprocessing_feature_sets sfs ON sfs.preprocessing_feature_set_id = n.source_feature_set_id
          JOIN preprocessing_feature_sets tfs ON tfs.preprocessing_feature_set_id = n.target_feature_set_id
          JOIN preprocessing_cases src ON src.preprocessing_case_id = sfs.preprocessing_case_id
          JOIN preprocessing_cases tgt ON tgt.preprocessing_case_id = tfs.preprocessing_case_id
          JOIN filegroups fg2 ON fg2.filegroup_id = tgt.filegroup_id
          JOIN vehicles v2 ON v2.vehicle_id = fg2.vehicle_id
         WHERE sfs.source_mode = ?
           AND sfs.feature_space = ?
           AND n.algorithm = ?
         ORDER BY src.filegroup_id, n.rank
        """,
        (source_mode, feature_space, neighbor_algorithm),
    ).fetchall()
    payload: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = str(int(row["source_filegroup_id"]))
        payload.setdefault(key, []).append(
            {
                "target_filegroup_id": int(row["target_filegroup_id"]),
                "target_case_label": f"{vehicle_display_label(row['target_year'], row['target_vehicle'])} ({row['target_test_code']})",
                "target_vehicle_label": vehicle_display_label(row["target_year"], row["target_vehicle"]),
                "target_test_code": row["target_test_code"],
                "rank": int(row["rank"]),
                "similarity_score": rounded(row["similarity_score"], 4),
                "distance_score": rounded(row["distance_score"], 4),
                "weighted_correlation": rounded(row["weighted_correlation"], 4),
                "dtw_distance": rounded(row["dtw_distance"], 4),
                "overlap_channel_count": int(row["overlap_channel_count"]) if row["overlap_channel_count"] is not None else 0,
                "multiview_score": rounded(row["multiview_score"], 4),
                "pulse_phase_score": rounded(row["pulse_phase_score"], 4),
            }
        )
    return payload


def load_representative_rows(
    connection: sqlite3.Connection,
    source_mode: str,
    feature_space: str,
    representative_algorithm: str,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    rows = connection.execute(
        """
        SELECT r.cluster_label,
               r.representative_kind,
               r.rank,
               r.score,
               fg.filegroup_id,
               fg.test_code,
               v.vehicle_year,
               v.vehicle_make_model
          FROM preprocessing_representatives r
          JOIN preprocessing_feature_sets fs ON fs.preprocessing_feature_set_id = r.preprocessing_feature_set_id
          JOIN preprocessing_cases pc ON pc.preprocessing_case_id = fs.preprocessing_case_id
          JOIN filegroups fg ON fg.filegroup_id = pc.filegroup_id
          JOIN vehicles v ON v.vehicle_id = fg.vehicle_id
         WHERE fs.source_mode = ?
           AND r.feature_space = ?
           AND r.algorithm = ?
         ORDER BY CASE r.representative_kind
                    WHEN 'cluster_centroid' THEN 0
                    WHEN 'cluster_boundary' THEN 1
                    WHEN 'cluster_stable' THEN 2
                    WHEN 'cluster_high_coverage' THEN 3
                    WHEN 'global_centroid' THEN 4
                    ELSE 9
                  END,
                  r.cluster_label,
                  r.rank
        """,
        (source_mode, feature_space, representative_algorithm),
    ).fetchall()
    cluster_rows: dict[str, list[dict[str, Any]]] = {}
    global_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = {
            "filegroup_id": int(row["filegroup_id"]),
            "case_label": f"{vehicle_display_label(row['vehicle_year'], row['vehicle_make_model'])} ({row['test_code']})",
            "representative_kind": row["representative_kind"],
            "cluster_label": int(row["cluster_label"]) if row["cluster_label"] is not None else None,
            "rank": int(row["rank"]),
            "score": rounded(row["score"], 4),
        }
        if row["cluster_label"] is None:
            global_rows.append(payload)
        else:
            cluster_rows.setdefault(str(int(row["cluster_label"])), []).append(payload)
    return cluster_rows, global_rows


def build_cluster_summary(cases: list[dict[str, Any]], cluster_rows: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = {}
    for case in cases:
        if case["cluster_label"] is None:
            continue
        bucket = grouped.setdefault(case["cluster_label"], {"cluster_label": case["cluster_label"], "case_count": 0, "outlier_count": 0, "representative_count": 0})
        bucket["case_count"] += 1
        if case["is_outlier"]:
            bucket["outlier_count"] += 1
    for label, rows in cluster_rows.items():
        if int(label) in grouped:
            grouped[int(label)]["representative_count"] = len(rows)
    return [grouped[key] for key in sorted(grouped)]


def build_outlier_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [case for case in cases if case["is_outlier"]]
    rows.sort(key=lambda row: (-(row["outlier_score"] or 0.0), row["vehicle_make_model"], row["test_code"]))
    return rows


def build_case_asset(case: dict[str, Any], asset_dir: Path, output_dir: Path, max_plot_points: int) -> str:
    frame = crop_frame_to_analysis_window(pd.read_parquet(resolve_repo_path(case["harmonized_wide_path"])))
    time_values = frame["time_s"].astype(float).tolist()
    stride = downsample_stride(len(time_values), max_plot_points)
    sampled_time = time_values[::stride]
    channel_order = [column for column in frame.columns if column != "time_s"]
    channels: dict[str, Any] = {}
    for column in channel_order:
        values = frame[column].astype(float).tolist()
        channels[column] = {
            "unit": infer_unit(column),
            "values": to_json_list(values[::stride]),
            "stats": summarize_series(time_values, values),
        }

    report_dir = REPO_ROOT / "output" / "small_overlap" / "reports" / f"{case['filegroup_id']}-{case['test_code']}__{case['mode']}"
    dashboard_dir = REPO_ROOT / "output" / "small_overlap" / "dashboard" / case["case_slug"]
    payload = {
        "filegroup_id": case["filegroup_id"],
        "case_label": case["case_label"],
        "vehicle_label": case["vehicle_label"],
        "test_code": case["test_code"],
        "time_s": to_json_list(sampled_time),
        "channel_order": channel_order,
        "default_channels": [name for name in DEFAULT_CHANNELS if name in channel_order],
        "channels": channels,
        "report_rel": link_if_exists(report_dir / "index.html", output_dir),
        "case_dashboard_rel": link_if_exists(dashboard_dir / "index.html", output_dir),
    }
    asset_path = asset_dir / f"{case['filegroup_id']}.json"
    asset_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return repo_relative(asset_path, output_dir)


def build_dashboard_data(
    connection: sqlite3.Connection,
    output_dir: Path,
    source_mode: str,
    feature_space: str,
    max_plot_points: int,
) -> dict[str, Any]:
    algorithms = resolve_feature_space_algorithms(connection, feature_space)
    cases = load_case_rows(connection, source_mode, feature_space, algorithms["cluster"])
    if not cases:
        raise ValueError(f"No preprocessing cases found for mode={source_mode}, feature_space={feature_space}")
    neighbors_by_source = load_neighbor_rows(connection, source_mode, feature_space, algorithms["neighbor"])
    cluster_representatives, global_representatives = load_representative_rows(
        connection,
        source_mode,
        feature_space,
        algorithms["representative"],
    )
    cluster_summary = build_cluster_summary(cases, cluster_representatives)
    outlier_rows = build_outlier_rows(cases)

    output_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = output_dir / "assets" / "cases"
    asset_dir.mkdir(parents=True, exist_ok=True)
    for case in cases:
        case["asset_rel"] = build_case_asset(case, asset_dir, output_dir, max_plot_points)

    return {
        "summary": {
            "case_count": len(cases),
            "cluster_count": len(cluster_summary),
            "outlier_count": len(outlier_rows),
            "neighbor_edge_count": sum(len(rows) for rows in neighbors_by_source.values()),
            "representative_count": sum(len(rows) for rows in cluster_representatives.values()) + len(global_representatives),
            "feature_space": feature_space,
            "source_mode": source_mode,
            "analysis_window_s": [ANALYSIS_WINDOW_START_S, ANALYSIS_WINDOW_END_S],
            "neighbor_algorithm": algorithms["neighbor"],
            "cluster_algorithm": algorithms["cluster"],
            "representative_algorithm": algorithms["representative"],
        },
        "cases": cases,
        "neighborsBySource": neighbors_by_source,
        "clusterRepresentativesByCluster": cluster_representatives,
        "globalRepresentatives": global_representatives,
        "clusterSummary": cluster_summary,
        "outlierRows": outlier_rows,
        "filters": {"clusters": [row["cluster_label"] for row in cluster_summary]},
        "defaultChannels": list(DEFAULT_CHANNELS),
    }


def dashboard_html(data: dict[str, Any]) -> str:
    template = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Signal Compare Dashboard</title><script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{--bg:#f5efe5;--panel:#fff9f0;--line:rgba(40,32,24,.12);--text:#201a15;--muted:#6d6257;--accent:#0f7173;--good:#2a7c46;--shadow:0 14px 32px rgba(35,25,15,.08)}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top left,#fff8ec 0%,var(--bg) 48%,#efe6d7 100%);color:var(--text);font-family:"IBM Plex Sans","Segoe UI",sans-serif}a{color:var(--accent);text-decoration:none}button,input,select{font:inherit}.page{max-width:1500px;margin:0 auto;padding:24px}.stack{display:grid;gap:18px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow)}.pad{padding:18px 20px}.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:18px;align-items:start}.title{font-size:34px;line-height:1.05;margin:0 0 8px;letter-spacing:-.03em}.subtitle{margin:0;color:var(--muted)}.summary-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.summary-card{padding:14px 16px;border-radius:18px;background:linear-gradient(180deg,#fff7ea 0%,#f4e5d1 100%);border:1px solid rgba(0,0,0,.06)}.summary-card span{display:block;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}.summary-card strong{display:block;margin-top:5px;font-size:22px}.head{display:flex;justify-content:space-between;gap:12px;align-items:end;margin-bottom:12px}.head h2,.head h3{margin:0}.head p{margin:0;color:var(--muted)}.control-grid{display:grid;grid-template-columns:1fr 1.25fr 1.25fr auto auto;gap:10px;align-items:end}.field label{display:block;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}.field input,.field select,.filters input,.filters select{width:100%;border:1px solid var(--line);border-radius:12px;padding:11px 12px;background:#fffdf8}.btn{border:none;border-radius:999px;padding:11px 14px;cursor:pointer;background:#efe3d3;color:var(--text)}.btn:hover{background:#e7d5bd}.btn.primary{background:var(--accent);color:#fff}.compare{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.comparebox{padding:16px;border-radius:18px;background:linear-gradient(180deg,#fffaf2 0%,#f7ebda 100%);border:1px solid rgba(0,0,0,.06)}.comparebox h2{margin:0 0 6px;font-size:20px}.comparebox p{margin:0;color:var(--muted)}.pills,.chips{display:flex;flex-wrap:wrap;gap:10px}.pills{margin-top:12px}.pill,.chip{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:8px 11px;background:#f2e6d8}.pill.good{background:#dff1e4;color:#215c35}.pill.bad{background:#f5d7cf;color:#7f261a}.table-wrap{max-height:360px;overflow:auto;border:1px solid var(--line);border-radius:16px;background:rgba(255,255,255,.56)}table{width:100%;border-collapse:collapse}th,td{padding:10px 12px;border-bottom:1px solid rgba(0,0,0,.07);text-align:left;vertical-align:top}th{position:sticky;top:0;background:#fbf3e6;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;z-index:1}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.metric-card{padding:14px 16px;border-radius:16px;background:#fff4e2;border:1px solid rgba(0,0,0,.05)}.metric-card span{display:block;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}.metric-card strong{display:block;margin-top:5px;font-size:20px}.plots{display:grid;gap:14px}.plot{padding:12px 12px 2px;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.72)}.plot h3{margin:0 0 6px 4px;font-size:16px}.advanced{overflow:hidden}.advanced summary{list-style:none;cursor:pointer;padding:18px 20px;font-weight:600}.advanced summary::-webkit-details-marker{display:none}.advanced summary span{color:var(--muted);font-weight:400;margin-left:10px}.advanced-body{padding:0 20px 20px}.two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.filters{display:grid;grid-template-columns:1fr 140px 160px;gap:10px;margin-bottom:12px}.note{color:var(--muted);font-size:13px}.small{color:var(--muted);font-size:12px;margin-top:8px}
@media (max-width:1100px){.hero,.compare,.two,.metrics{grid-template-columns:1fr}.control-grid{grid-template-columns:1fr}.summary-grid{grid-template-columns:1fr 1fr}}@media (max-width:720px){.page{padding:14px}.summary-grid,.filters{grid-template-columns:1fr}.title{font-size:28px}}
</style></head><body><div class="page stack">
<section class="hero"><div class="panel pad"><h1 class="title">Signal Compare Dashboard</h1><p class="subtitle">The top half is the normal workflow. Open Advanced Details only when you need cluster, representative, or outlier tools.</p></div><div class="summary-grid"><div class="summary-card"><span>Cases</span><strong id="kpi-cases"></strong></div><div class="summary-card"><span>Feature Space</span><strong id="kpi-space" style="font-size:18px"></strong></div><div class="summary-card"><span>Clusters</span><strong id="kpi-clusters"></strong></div><div class="summary-card"><span>Outliers</span><strong id="kpi-outliers"></strong></div></div></section>
<section class="panel pad stack"><div class="head"><div><h2>1. Choose Cases</h2><p>Pick a source vehicle, then keep the suggested match or choose a manual target.</p></div></div><div class="control-grid"><div class="field"><label for="source-search">Search</label><input id="source-search" type="search" placeholder="vehicle / test / filegroup" /></div><div class="field"><label for="source-select">Source vehicle</label><select id="source-select"></select></div><div class="field"><label for="target-select">Target vehicle</label><select id="target-select"></select></div><button id="use-top-neighbor" class="btn primary">Use top match</button><button id="swap-compare" class="btn">Swap</button></div></section>
<section class="compare"><div class="panel pad comparebox"><h2 id="source-title"></h2><p id="source-meta"></p><div class="pills" id="source-pills"></div><div class="small" id="source-links"></div></div><div class="panel pad comparebox"><h2 id="target-title"></h2><p id="target-meta"></p><div class="pills" id="target-pills"></div><div class="small" id="target-links"></div></div></section>
<section class="two"><div class="panel pad"><div class="head"><div><h2>2. Suggested Similar Tests</h2><p>The first row is the recommended comparison target.</p></div></div><div class="table-wrap"><table><thead><tr><th>Rank</th><th>Target</th><th>Similarity</th><th>Action</th></tr></thead><tbody id="neighbor-body"></tbody></table></div></div><div class="panel pad"><div class="head"><div><h2>3. Quick Compare Summary</h2><p>Keep only the core match metrics visible here.</p></div></div><div class="metrics" id="compare-metrics"></div></div></section>
<section class="panel pad stack"><div class="head"><div><h2>4. Waveform Overlay</h2><p>Default channels are already selected. Add more only when needed.</p></div></div><div id="channel-controls" class="chips"></div><div id="comparison-plots" class="plots"></div></section>
<details class="panel advanced"><summary>Advanced Details<span>Cluster, representative, outlier, and full catalog tools stay available here.</span></summary><div class="advanced-body stack"><div class="panel pad"><div class="head"><div><h3>Catalog Filters</h3><p>Use this only when you want to browse the full corpus manually.</p></div></div><div class="filters"><input id="case-search" type="search" placeholder="Search vehicle / test / id" /><select id="cluster-filter"></select><select id="outlier-filter"><option value="all">All cases</option><option value="only">Only outliers</option><option value="exclude">Exclude outliers</option></select></div><div class="table-wrap"><table><thead><tr><th>Case</th><th>Cluster</th><th>Status</th><th>Actions</th></tr></thead><tbody id="case-table-body"></tbody></table></div><div class="small" id="case-note"></div></div><div class="two"><div class="panel pad"><div class="head"><div><h3>Cluster Summary</h3><p>Current source cluster footprint.</p></div></div><div id="cluster-summary-cards" class="metrics"></div></div><div class="panel pad"><div class="head"><div><h3>Cluster Map</h3><p>Click a bar to filter the advanced catalog.</p></div></div><div id="cluster-plot" style="height:320px"></div></div></div><div class="two"><div class="panel pad"><div class="head"><div><h3>Cluster Representatives</h3><p>Representative cases from the current source cluster.</p></div></div><div class="table-wrap"><table><thead><tr><th>Kind</th><th>Case</th><th>Score</th><th>Action</th></tr></thead><tbody id="cluster-rep-body"></tbody></table></div></div><div class="panel pad"><div class="head"><div><h3>Global Benchmark Set</h3><p>Corpus-wide benchmark cases.</p></div></div><div class="table-wrap"><table><thead><tr><th>Rank</th><th>Case</th><th>Score</th><th>Action</th></tr></thead><tbody id="global-rep-body"></tbody></table></div></div></div><div class="panel pad"><div class="head"><div><h3>Outlier Watchlist</h3><p>Potentially unusual cases in the current feature space.</p></div></div><div class="table-wrap"><table><thead><tr><th>Case</th><th>Cluster</th><th>Score</th><th>Action</th></tr></thead><tbody id="outlier-body"></tbody></table></div></div></div></details>
</div><script id="dashboard-data" type="application/json">__DATA_JSON__</script><script>
const dashboard=JSON.parse(document.getElementById("dashboard-data").textContent);const caseIndex=new Map(dashboard.cases.map((row)=>[row.filegroup_id,row]));const assetCache=new Map();const state={search:"",cluster:"all",outlier:"all",sourceId:dashboard.cases[0]?.filegroup_id??null,targetId:null,selectedChannels:new Set(dashboard.defaultChannels)};const fmt=(v,d=3)=>v===null||v===undefined||Number.isNaN(Number(v))?"n/a":Number(v).toFixed(d);const clusterText=(v)=>v===null||v===undefined?"-":`C${v}`;const src=()=>caseIndex.get(state.sourceId)??null;const tgt=()=>caseIndex.get(state.targetId)??null;const neighbors=()=>dashboard.neighborsBySource[String(state.sourceId)]??[];const clusterReps=()=>src()&&src().cluster_label!==null?(dashboard.clusterRepresentativesByCluster[String(src().cluster_label)]??[]):[];const searchMatches=()=>dashboard.cases.filter((row)=>{const hay=`${row.vehicle_label} ${row.test_code} ${row.filegroup_id}`.toLowerCase();return hay.includes(state.search);});const filteredCases=()=>searchMatches().filter((row)=>{if(state.cluster!=="all"&&String(row.cluster_label)!==state.cluster)return false;if(state.outlier==="only"&&!row.is_outlier)return false;if(state.outlier==="exclude"&&row.is_outlier)return false;return true;});async function loadAsset(filegroupId){if(!filegroupId)return null;if(assetCache.has(filegroupId))return assetCache.get(filegroupId);const row=caseIndex.get(filegroupId);if(!row)return null;const response=await fetch(row.asset_rel,{cache:"no-store"});if(!response.ok)throw new Error(`Failed asset ${filegroupId}`);const payload=await response.json();assetCache.set(filegroupId,payload);return payload;}function ensureTarget(){if(state.targetId&&state.targetId!==state.sourceId&&caseIndex.has(state.targetId))return;const first=neighbors()[0]?.target_filegroup_id;if(first&&first!==state.sourceId){state.targetId=first;return;}const fallback=dashboard.cases.find((row)=>row.filegroup_id!==state.sourceId);state.targetId=fallback?.filegroup_id??null;}function metric(label,value){return `<div class="metric-card"><span>${label}</span><strong>${value}</strong></div>`;}function renderFilters(){document.getElementById("cluster-filter").innerHTML=`<option value="all">All clusters</option>`+dashboard.filters.clusters.map((value)=>`<option value="${value}">Cluster ${value}</option>`).join("");}function renderKpis(){document.getElementById("kpi-cases").textContent=dashboard.summary.case_count;document.getElementById("kpi-clusters").textContent=dashboard.summary.cluster_count;document.getElementById("kpi-outliers").textContent=dashboard.summary.outlier_count;document.getElementById("kpi-space").textContent=dashboard.summary.feature_space;}function renderSourcePicker(){const rows=searchMatches();const select=document.getElementById("source-select");select.innerHTML=rows.map((row)=>`<option value="${row.filegroup_id}" ${row.filegroup_id===state.sourceId?"selected":""}>${row.case_label}</option>`).join("");if(rows.length&&!rows.some((row)=>row.filegroup_id===state.sourceId)){state.sourceId=rows[0].filegroup_id;ensureTarget();}if(select.options.length&&select.value===""){select.selectedIndex=0;state.sourceId=Number(select.value);ensureTarget();}select.onchange=()=>{state.sourceId=Number(select.value);ensureTarget();renderAll();};}function renderCatalog(){const rows=filteredCases();const body=document.getElementById("case-table-body");body.innerHTML=rows.map((row)=>`<tr><td><strong>${row.vehicle_label}</strong><br /><span class="note">${row.test_code} / ${row.filegroup_id}</span></td><td>${clusterText(row.cluster_label)}</td><td>${row.is_outlier?`<span class="pill bad">outlier ${fmt(row.outlier_score)}</span>`:`<span class="pill good">inlier</span>`}</td><td><button class="btn" data-a="source" data-id="${row.filegroup_id}">Source</button> <button class="btn" data-a="target" data-id="${row.filegroup_id}">Target</button></td></tr>`).join("");document.getElementById("case-note").textContent=`Showing ${rows.length} / ${dashboard.cases.length} cases`;body.querySelectorAll("button").forEach((button)=>{button.onclick=()=>{const id=Number(button.dataset.id);if(button.dataset.a==="source"){state.sourceId=id;ensureTarget();}else state.targetId=id;renderAll();};});}function renderTargetPicker(){const select=document.getElementById("target-select");select.innerHTML=dashboard.cases.filter((row)=>row.filegroup_id!==state.sourceId).map((row)=>`<option value="${row.filegroup_id}" ${row.filegroup_id===state.targetId?"selected":""}>${row.case_label}</option>`).join("");if(!select.value&&select.options.length){select.selectedIndex=0;state.targetId=Number(select.value);}select.onchange=()=>{state.targetId=Number(select.value);renderAll();};}function linksHtml(asset){const links=[];if(asset?.report_rel)links.push(`<a href="${asset.report_rel}">Auto report</a>`);if(asset?.case_dashboard_rel)links.push(`<a href="${asset.case_dashboard_rel}">Case dashboard</a>`);return links.length?links.join(" | "):"Linked artifact unavailable";}function renderCompareCards(sourceAsset,targetAsset){const source=src();const target=tgt();document.getElementById("source-title").textContent=source?.case_label??"No source";document.getElementById("source-meta").textContent=source?`cluster=${clusterText(source.cluster_label)} | feature_count=${source.feature_count} | coverage=${fmt(source.coverage_mean)}`:"";document.getElementById("target-title").textContent=target?.case_label??"No target";document.getElementById("target-meta").textContent=target?`cluster=${clusterText(target.cluster_label)} | feature_count=${target.feature_count} | coverage=${fmt(target.coverage_mean)}`:"";document.getElementById("source-pills").innerHTML=source?`<span class="pill ${source.is_outlier?"bad":"good"}">${source.is_outlier?"outlier":"inlier"}</span><span class="pill">stability ${fmt(source.stability_score)}</span><span class="pill">coverage ${fmt(source.coverage_score)}</span>`:"";document.getElementById("target-pills").innerHTML=target?`<span class="pill ${target.is_outlier?"bad":"good"}">${target.is_outlier?"outlier":"inlier"}</span><span class="pill">stability ${fmt(target.stability_score)}</span><span class="pill">coverage ${fmt(target.coverage_score)}</span>`:"";document.getElementById("source-links").innerHTML=source?linksHtml(sourceAsset):"";document.getElementById("target-links").innerHTML=target?linksHtml(targetAsset):"";}function renderCompareMetrics(){const source=src();const target=tgt();const row=neighbors().find((item)=>item.target_filegroup_id===state.targetId)??null;const sameCluster=source&&target&&source.cluster_label!==null&&source.cluster_label===target.cluster_label;document.getElementById("compare-metrics").innerHTML=source&&target?[metric("Neighbor rank",row?`#${row.rank}`:"manual"),metric("Similarity",row?fmt(row.similarity_score,4):"n/a"),metric("Model view score",row?fmt(row.multiview_score,4):"n/a"),metric("Physics residual",row?fmt(row.pulse_phase_score,4):"n/a"),metric("Weighted corr",row?fmt(row.weighted_correlation,4):"n/a"),metric("Same cluster",sameCluster?"yes":"no"),metric("Source cluster",clusterText(source.cluster_label)),metric("Target cluster",clusterText(target.cluster_label))].join(""):"";}function renderNeighbors(){const body=document.getElementById("neighbor-body");body.innerHTML=neighbors().map((row)=>`<tr><td>${row.rank}</td><td><strong>${row.target_vehicle_label}</strong><br /><span class="note">${row.target_test_code} / ${row.target_filegroup_id}</span></td><td>${fmt(row.similarity_score,4)}</td><td><button class="btn" data-id="${row.target_filegroup_id}">Compare</button></td></tr>`).join("");body.querySelectorAll("button").forEach((button)=>{button.onclick=()=>{state.targetId=Number(button.dataset.id);renderAll();};});}function renderRepresentatives(){const clusterBody=document.getElementById("cluster-rep-body");clusterBody.innerHTML=clusterReps().map((row)=>`<tr><td>${row.representative_kind}</td><td><strong>${row.case_label}</strong><br /><span class="note">rank ${row.rank} / filegroup ${row.filegroup_id}</span></td><td>${fmt(row.score,4)}</td><td><button class="btn" data-id="${row.filegroup_id}">Compare</button></td></tr>`).join("");clusterBody.querySelectorAll("button").forEach((button)=>{button.onclick=()=>{state.targetId=Number(button.dataset.id);renderAll();};});const globalBody=document.getElementById("global-rep-body");globalBody.innerHTML=dashboard.globalRepresentatives.map((row)=>`<tr><td>${row.rank}</td><td><strong>${row.case_label}</strong><br /><span class="note">${row.representative_kind}</span></td><td>${fmt(row.score,4)}</td><td><button class="btn" data-a="source" data-id="${row.filegroup_id}">Source</button> <button class="btn" data-a="target" data-id="${row.filegroup_id}">Target</button></td></tr>`).join("");globalBody.querySelectorAll("button").forEach((button)=>{button.onclick=()=>{const id=Number(button.dataset.id);if(button.dataset.a==="source"){state.sourceId=id;ensureTarget();}else state.targetId=id;renderAll();};});}function renderOutliers(){const body=document.getElementById("outlier-body");body.innerHTML=dashboard.outlierRows.map((row)=>`<tr><td><strong>${row.vehicle_label}</strong><br /><span class="note">${row.test_code} / ${row.filegroup_id}</span></td><td>${clusterText(row.cluster_label)}</td><td>${fmt(row.outlier_score,4)}</td><td><button class="btn" data-id="${row.filegroup_id}">Source</button></td></tr>`).join("");body.querySelectorAll("button").forEach((button)=>{button.onclick=()=>{state.sourceId=Number(button.dataset.id);ensureTarget();renderAll();};});}function renderClusterCards(){const source=src();const row=source&&source.cluster_label!==null?dashboard.clusterSummary.find((item)=>item.cluster_label===source.cluster_label):null;document.getElementById("cluster-summary-cards").innerHTML=row?[metric("Cluster",clusterText(row.cluster_label)),metric("Cases",row.case_count),metric("Outliers",row.outlier_count),metric("Representatives",row.representative_count)].join(""):"";}function renderClusterPlot(){Plotly.react("cluster-plot",[{type:"bar",x:dashboard.clusterSummary.map((row)=>`Cluster ${row.cluster_label}`),y:dashboard.clusterSummary.map((row)=>row.case_count),marker:{color:"#0f7173"},name:"Cases"},{type:"scatter",mode:"lines+markers",x:dashboard.clusterSummary.map((row)=>`Cluster ${row.cluster_label}`),y:dashboard.clusterSummary.map((row)=>row.outlier_count),marker:{color:"#bc4b32",size:9},line:{color:"#bc4b32",width:2},yaxis:"y2",name:"Outliers"}],{margin:{l:52,r:52,t:12,b:48},paper_bgcolor:"#fff9f0",plot_bgcolor:"#fffdf8",font:{family:"IBM Plex Sans, sans-serif",color:"#201a15"},yaxis:{title:"Cases",gridcolor:"rgba(0,0,0,.08)"},yaxis2:{title:"Outliers",overlaying:"y",side:"right",rangemode:"tozero"},legend:{orientation:"h",y:1.15}},{responsive:true,displaylogo:false});document.getElementById("cluster-plot").on("plotly_click",(event)=>{const label=event.points?.[0]?.x??"";const match=String(label).match(/Cluster (\\d+)/);if(!match)return;state.cluster=match[1];document.getElementById("cluster-filter").value=match[1];renderAll();});}function renderChannelControls(sourceAsset,targetAsset){const available=new Set([...(sourceAsset?.channel_order??[]),...(targetAsset?.channel_order??[])]);const channels=[...available];if(!channels.length){document.getElementById("channel-controls").innerHTML="";return;}if(![...state.selectedChannels].some((name)=>available.has(name))){state.selectedChannels=new Set((sourceAsset?.default_channels??dashboard.defaultChannels).filter((name)=>available.has(name)));}document.getElementById("channel-controls").innerHTML=channels.map((name)=>`<label class="chip"><input type="checkbox" value="${name}" ${state.selectedChannels.has(name)?"checked":""} /> <span>${name}</span></label>`).join("");document.querySelectorAll("#channel-controls input").forEach((input)=>{input.onchange=()=>{if(input.checked)state.selectedChannels.add(input.value);else state.selectedChannels.delete(input.value);renderPlots(sourceAsset,targetAsset);};});}function plotLayout(title,unit){return{margin:{l:60,r:20,t:34,b:42},paper_bgcolor:"rgba(0,0,0,0)",plot_bgcolor:"#fffdf8",font:{family:"IBM Plex Sans, sans-serif",color:"#201a15"},title:{text:title,x:.01,xanchor:"left",font:{size:15}},xaxis:{title:"Time (s)",gridcolor:"rgba(0,0,0,.08)"},yaxis:{title:unit||"",gridcolor:"rgba(0,0,0,.08)"},legend:{orientation:"h",y:1.15}};}function renderPlots(sourceAsset,targetAsset){const selected=[...state.selectedChannels];const container=document.getElementById("comparison-plots");if(!sourceAsset||!selected.length){container.innerHTML=`<div class="note">No channels selected.</div>`;return;}container.innerHTML=selected.map((channel,index)=>`<div class="plot"><h3>${channel}</h3><div id="plot-${index}" style="height:300px"></div></div>`).join("");selected.forEach((channel,index)=>{const traces=[];if(sourceAsset.channels[channel])traces.push({type:"scatter",mode:"lines",name:sourceAsset.case_label,x:sourceAsset.time_s,y:sourceAsset.channels[channel].values,line:{color:"#b33c2e",width:2.2}});if(targetAsset&&targetAsset.channels[channel])traces.push({type:"scatter",mode:"lines",name:targetAsset.case_label,x:targetAsset.time_s,y:targetAsset.channels[channel].values,line:{color:"#0f7173",width:1.9}});Plotly.react(`plot-${index}`,traces,plotLayout(channel,sourceAsset.channels[channel]?.unit??targetAsset?.channels[channel]?.unit??""),{responsive:true,displaylogo:false,modeBarButtonsToRemove:["lasso2d","select2d"]});});}async function renderCompare(){ensureTarget();const sourceAsset=await loadAsset(state.sourceId);const targetAsset=state.targetId?await loadAsset(state.targetId):null;renderCompareCards(sourceAsset,targetAsset);renderCompareMetrics();renderChannelControls(sourceAsset,targetAsset);renderPlots(sourceAsset,targetAsset);}async function renderAll(){renderKpis();renderSourcePicker();renderCatalog();renderTargetPicker();renderNeighbors();renderRepresentatives();renderOutliers();renderClusterCards();renderClusterPlot();await renderCompare();}document.getElementById("source-search").addEventListener("input",(event)=>{state.search=event.target.value.trim().toLowerCase();document.getElementById("case-search").value=event.target.value;renderAll();});document.getElementById("case-search").addEventListener("input",(event)=>{state.search=event.target.value.trim().toLowerCase();document.getElementById("source-search").value=event.target.value;renderAll();});document.getElementById("cluster-filter").addEventListener("change",(event)=>{state.cluster=event.target.value;renderAll();});document.getElementById("outlier-filter").addEventListener("change",(event)=>{state.outlier=event.target.value;renderAll();});document.getElementById("use-top-neighbor").addEventListener("click",()=>{const first=neighbors()[0];if(!first)return;state.targetId=first.target_filegroup_id;renderAll();});document.getElementById("swap-compare").addEventListener("click",()=>{if(!state.targetId)return;const nextSource=state.targetId;state.targetId=state.sourceId;state.sourceId=nextSource;ensureTarget();renderAll();});renderFilters();ensureTarget();renderAll();</script></body></html>"""
    return template.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_dir = resolve_repo_path(args.output_dir)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        ensure_preprocessing_schema(connection)
        data = build_dashboard_data(connection, output_dir, args.source_mode, args.feature_space, args.max_plot_points)
    finally:
        connection.close()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"
    output_path.write_text(dashboard_html(data), encoding="utf-8")
    print(
        json.dumps(
            {
                "dashboard_html": str(output_path),
                "case_count": data["summary"]["case_count"],
                "cluster_count": data["summary"]["cluster_count"],
                "outlier_count": data["summary"]["outlier_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
