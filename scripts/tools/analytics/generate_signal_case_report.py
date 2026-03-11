from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from scripts.core.signals.preprocess_known_signal_families import ensure_preprocessing_schema, resolve_repo_path
from scripts.tools.analytics.build_signal_feature_batch import ANALYSIS_WINDOW_END_S, ANALYSIS_WINDOW_START_S, crop_frame_to_analysis_window


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = REPO_ROOT / "output" / "small_overlap" / "reports"
DEFAULT_SOURCE_MODE = "standard_baseline"
DEFAULT_FEATURE_SPACE = "official_known_harmonized_v5"
PLOT_CHANNELS = (
    "vehicle_longitudinal_accel_g",
    "vehicle_resultant_accel_g",
    "seat_mid_deflection_mm",
    "foot_left_x_accel_g",
)
COLORS = ("#b33c2e", "#0f7173", "#785589", "#c97c10", "#2660a4", "#3b7a57")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate automated comparison report for one signal case.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--filegroup-id", type=int, required=True)
    parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE)
    parser.add_argument("--feature-space", default=DEFAULT_FEATURE_SPACE)
    parser.add_argument("--compare-filegroup-id", type=int, action="append", default=[])
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def absolute_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_case(connection: sqlite3.Connection, filegroup_id: int, source_mode: str) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT pc.preprocessing_case_id,
               pc.filegroup_id,
               pc.mode,
               pc.status,
               pc.manifest_path,
               pc.harmonized_wide_path,
               fg.test_code,
               v.vehicle_year,
               v.vehicle_make_model
          FROM preprocessing_cases pc
          JOIN filegroups fg
            ON fg.filegroup_id = pc.filegroup_id
          JOIN vehicles v
            ON v.vehicle_id = fg.vehicle_id
         WHERE pc.filegroup_id = ?
           AND pc.mode = ?
        """,
        (filegroup_id, source_mode),
    ).fetchone()
    if row is None:
        raise ValueError(f"case not found for filegroup_id={filegroup_id}, mode={source_mode}")
    return row


def load_mode_rows(connection: sqlite3.Connection, filegroup_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT mode, status, parser_version, manifest_path, wide_path, harmonized_wide_path
          FROM preprocessing_cases
         WHERE filegroup_id = ?
         ORDER BY mode
        """,
        (filegroup_id,),
    ).fetchall()


def load_neighbors(
    connection: sqlite3.Connection,
    filegroup_id: int,
    source_mode: str,
    feature_space: str,
    top_k: int,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT tgt.filegroup_id AS target_filegroup_id,
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
               n.pulse_view_score,
               n.occupant_view_score,
               n.lower_extremity_view_score,
               n.pulse_phase_score,
               n.occupant_phase_score,
               n.lower_extremity_phase_score
          FROM preprocessing_neighbors n
          JOIN preprocessing_feature_sets sfs
            ON sfs.preprocessing_feature_set_id = n.source_feature_set_id
          JOIN preprocessing_feature_sets tfs
            ON tfs.preprocessing_feature_set_id = n.target_feature_set_id
          JOIN preprocessing_cases src
            ON src.preprocessing_case_id = sfs.preprocessing_case_id
          JOIN preprocessing_cases tgt
            ON tgt.preprocessing_case_id = tfs.preprocessing_case_id
          JOIN filegroups fg2
            ON fg2.filegroup_id = tgt.filegroup_id
          JOIN vehicles v2
            ON v2.vehicle_id = fg2.vehicle_id
         WHERE src.filegroup_id = ?
           AND sfs.source_mode = ?
           AND sfs.feature_space = ?
         ORDER BY n.rank
         LIMIT ?
        """,
        (filegroup_id, source_mode, feature_space, top_k),
    ).fetchall()


def load_cluster_representatives(
    connection: sqlite3.Connection,
    filegroup_id: int,
    source_mode: str,
    feature_space: str,
) -> tuple[dict[str, Any], list[sqlite3.Row]]:
    source_cluster = connection.execute(
        """
        SELECT c.cluster_label,
               c.outlier_score,
               c.centroid_distance,
               c.robust_distance_score,
               c.local_density_outlier_score,
               c.stability_score,
               c.coverage_score
          FROM preprocessing_clusters c
          JOIN preprocessing_feature_sets fs
            ON fs.preprocessing_feature_set_id = c.preprocessing_feature_set_id
          JOIN preprocessing_cases pc
            ON pc.preprocessing_case_id = fs.preprocessing_case_id
         WHERE pc.filegroup_id = ?
           AND fs.source_mode = ?
           AND fs.feature_space = ?
        """,
        (filegroup_id, source_mode, feature_space),
    ).fetchone()
    if source_cluster is None:
        return {}, []
    reps = connection.execute(
        """
        SELECT fg.filegroup_id,
               fg.test_code,
               v.vehicle_year,
               v.vehicle_make_model,
               r.representative_kind,
               r.cluster_label,
               r.rank,
               r.score
          FROM preprocessing_representatives r
          JOIN preprocessing_feature_sets fs
            ON fs.preprocessing_feature_set_id = r.preprocessing_feature_set_id
          JOIN preprocessing_cases pc
            ON pc.preprocessing_case_id = fs.preprocessing_case_id
          JOIN filegroups fg
            ON fg.filegroup_id = pc.filegroup_id
          JOIN vehicles v
            ON v.vehicle_id = fg.vehicle_id
         WHERE r.feature_space = ?
           AND fs.source_mode = ?
           AND r.cluster_label = ?
         ORDER BY CASE r.representative_kind
                    WHEN 'cluster_centroid' THEN 0
                    WHEN 'cluster_boundary' THEN 1
                    WHEN 'cluster_stable' THEN 2
                    WHEN 'cluster_high_coverage' THEN 3
                    WHEN 'global_centroid' THEN 4
                    ELSE 9
                  END,
                  r.rank
        """,
        (feature_space, source_mode, source_cluster["cluster_label"]),
    ).fetchall()
    return dict(source_cluster), reps


def load_compare_cases(
    connection: sqlite3.Connection,
    source_mode: str,
    explicit_filegroup_ids: list[int],
    neighbor_rows: list[sqlite3.Row],
) -> list[sqlite3.Row]:
    if explicit_filegroup_ids:
        ids = explicit_filegroup_ids
    else:
        ids = [int(row["target_filegroup_id"]) for row in neighbor_rows]
    result: list[sqlite3.Row] = []
    for filegroup_id in ids:
        result.append(load_case(connection, filegroup_id, source_mode))
    return result


def case_frame(case_row: sqlite3.Row) -> pd.DataFrame:
    path = absolute_path(case_row["harmonized_wide_path"])
    if path is None or not path.exists():
        raise FileNotFoundError(f"harmonized_wide_path missing for filegroup_id={case_row['filegroup_id']}")
    return crop_frame_to_analysis_window(pd.read_parquet(path))


def channel_label(channel_name: str) -> str:
    labels = {
        "vehicle_longitudinal_accel_g": "Vehicle Longitudinal (g)",
        "vehicle_resultant_accel_g": "Vehicle Resultant (g)",
        "seat_mid_deflection_mm": "Seat Mid Deflection (mm)",
        "foot_left_x_accel_g": "Foot Left X (g)",
    }
    return labels.get(channel_name, channel_name)


def render_overlay_plot(source_case: sqlite3.Row, compare_cases: list[sqlite3.Row], out_path: Path) -> list[str]:
    frames = [(source_case, case_frame(source_case)), *[(case, case_frame(case)) for case in compare_cases]]
    available_channels = [
        channel_name
        for channel_name in PLOT_CHANNELS
        if any(channel_name in frame.columns for _, frame in frames)
    ]
    if not available_channels:
        raise ValueError("No common report channels available for comparison plot.")

    fig, axes = plt.subplots(len(available_channels), 1, figsize=(14, 3.6 * len(available_channels)), sharex=True)
    if len(available_channels) == 1:
        axes = [axes]
    used_labels: list[str] = []
    for ax, channel_name in zip(axes, available_channels, strict=True):
        for index, (case_row, frame) in enumerate(frames):
            if channel_name not in frame.columns:
                continue
            label = f"{case_row['vehicle_year']} {case_row['vehicle_make_model']} ({case_row['test_code']})"
            ax.plot(
                frame["time_s"],
                frame[channel_name],
                linewidth=2.1 if index == 0 else 1.6,
                color=COLORS[index % len(COLORS)],
                alpha=1.0 if index == 0 else 0.82,
                label=label,
            )
            if label not in used_labels:
                used_labels.append(label)
        ax.set_ylabel(channel_label(channel_name))
        ax.axvline(0.0, color="#444444", linestyle="--", linewidth=1.0, alpha=0.7)
        ax.set_xlim(ANALYSIS_WINDOW_START_S, ANALYSIS_WINDOW_END_S)
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right", fontsize=9)
    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(f"{source_case['test_code']} comparison report", fontsize=16, y=0.995)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)
    return available_channels


def render_representative_plot(
    source_case: sqlite3.Row,
    representative_cases: list[sqlite3.Row],
    out_path: Path,
) -> None:
    frames = [(source_case, case_frame(source_case)), *[(case, case_frame(case)) for case in representative_cases]]
    channels = [name for name in ("vehicle_longitudinal_accel_g", "seat_mid_deflection_mm") if any(name in frame.columns for _, frame in frames)]
    if not channels:
        channels = ["vehicle_longitudinal_accel_g"]
    fig, axes = plt.subplots(len(channels), 1, figsize=(14, 4.0 * len(channels)), sharex=True)
    if len(channels) == 1:
        axes = [axes]
    for ax, channel_name in zip(axes, channels, strict=True):
        for index, (case_row, frame) in enumerate(frames):
            if channel_name not in frame.columns:
                continue
            label = f"{case_row['vehicle_make_model']} ({case_row['test_code']})"
            ax.plot(
                frame["time_s"],
                frame[channel_name],
                linewidth=2.2 if index == 0 else 1.5,
                color=COLORS[index % len(COLORS)],
                alpha=1.0 if index == 0 else 0.78,
                label=label,
            )
        ax.set_ylabel(channel_label(channel_name))
        ax.axvline(0.0, color="#444444", linestyle="--", linewidth=1.0, alpha=0.7)
        ax.set_xlim(ANALYSIS_WINDOW_START_S, ANALYSIS_WINDOW_END_S)
        ax.grid(True, alpha=0.25)
    axes[0].legend(loc="upper right", fontsize=9)
    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(f"{source_case['test_code']} cluster representatives", fontsize=16, y=0.995)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def html_table(columns: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{column}</th>" for column in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{value}</td>" for value in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def report_html(
    source_case: sqlite3.Row,
    mode_rows: list[sqlite3.Row],
    neighbor_rows: list[sqlite3.Row],
    cluster_info: dict[str, Any],
    representative_rows: list[sqlite3.Row],
    compare_plot_name: str,
    representative_plot_name: str,
    dashboard_rel: str | None,
) -> str:
    mode_table = html_table(
        ["Mode", "Status", "Wide", "Harmonized"],
        [
            [
                row["mode"],
                row["status"],
                "yes" if row["wide_path"] else "no",
                "yes" if row["harmonized_wide_path"] else "no",
            ]
            for row in mode_rows
        ],
    )
    neighbor_table = html_table(
        ["Rank", "Vehicle", "Test", "Similarity", "Multiview", "Pulse Phase", "Weighted Corr", "DTW"],
        [
            [
                row["rank"],
                f"{row['target_year']} {row['target_vehicle']}",
                row["target_test_code"],
                f"{row['similarity_score']:.4f}",
                f"{row['multiview_score']:.4f}" if row["multiview_score"] is not None else "",
                f"{row['pulse_phase_score']:.4f}" if row["pulse_phase_score"] is not None else "",
                f"{row['weighted_correlation']:.4f}" if row["weighted_correlation"] is not None else "",
                f"{row['dtw_distance']:.4f}" if row["dtw_distance"] is not None else "",
            ]
            for row in neighbor_rows
        ],
    )
    representative_table = html_table(
        ["Kind", "Rank", "Vehicle", "Test", "Score"],
        [
            [
                row["representative_kind"],
                row["rank"],
                f"{row['vehicle_year']} {row['vehicle_make_model']}",
                row["test_code"],
                f"{row['score']:.4f}",
            ]
            for row in representative_rows
        ],
    )
    dashboard_link = f'<p><a href="{dashboard_rel}">Open existing interactive dashboard</a></p>' if dashboard_rel else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{source_case['test_code']} automated report</title>
  <style>
    body {{ font-family: "Segoe UI", sans-serif; background:#f6f2ea; color:#231d18; margin:0; }}
    .page {{ max-width: 1280px; margin:0 auto; padding:24px; }}
    .card {{ background:#fffaf3; border:1px solid rgba(0,0,0,.08); border-radius:18px; padding:18px 20px; margin-bottom:18px; box-shadow:0 8px 24px rgba(0,0,0,.05); }}
    h1,h2 {{ margin:0 0 12px 0; }}
    .meta {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:12px; }}
    .pill {{ background:#f3eadb; border-radius:14px; padding:12px 14px; }}
    .pill strong {{ display:block; font-size:18px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ text-align:left; padding:10px 12px; border-bottom:1px solid rgba(0,0,0,.08); }}
    th {{ font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:#6b6155; }}
    img {{ width:100%; border-radius:16px; border:1px solid rgba(0,0,0,.08); }}
    a {{ color:#0f7173; text-decoration:none; }}
  </style>
</head>
<body>
  <div class="page">
    <div class="card">
      <h1>{source_case['vehicle_year']} {source_case['vehicle_make_model']}</h1>
      <p>{source_case['test_code']} / filegroup_id={source_case['filegroup_id']} / mode={source_case['mode']}</p>
        <div class="meta">
        <div class="pill"><span>Cluster</span><strong>{cluster_info.get('cluster_label', '-')}</strong></div>
        <div class="pill"><span>Outlier Score</span><strong>{cluster_info.get('outlier_score', 0):.3f}</strong></div>
        <div class="pill"><span>Centroid Distance</span><strong>{cluster_info.get('centroid_distance', 0):.3f}</strong></div>
        <div class="pill"><span>Similar Cases</span><strong>{len(neighbor_rows)}</strong></div>
      </div>
      {dashboard_link}
    </div>
    <div class="card">
      <h2>Mode Status</h2>
      {mode_table}
    </div>
    <div class="card">
      <h2>Top Similar Cases</h2>
      {neighbor_table}
    </div>
    <div class="card">
      <h2>Representative Cases In Cluster</h2>
      {representative_table}
    </div>
    <div class="card">
      <h2>Cluster Diagnostics</h2>
      <div class="meta">
        <div class="pill"><span>Robust Distance</span><strong>{cluster_info.get('robust_distance_score', 0):.3f}</strong></div>
        <div class="pill"><span>Local Density</span><strong>{cluster_info.get('local_density_outlier_score', 0):.3f}</strong></div>
        <div class="pill"><span>Stability</span><strong>{cluster_info.get('stability_score', 0):.3f}</strong></div>
        <div class="pill"><span>Coverage</span><strong>{cluster_info.get('coverage_score', 0):.3f}</strong></div>
      </div>
    </div>
    <div class="card">
      <h2>Comparison Overlay</h2>
      <img src="{compare_plot_name}" alt="comparison overlay" />
    </div>
    <div class="card">
      <h2>Representative Overlay</h2>
      <img src="{representative_plot_name}" alt="representative overlay" />
    </div>
  </div>
</body>
</html>"""


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_dir = resolve_repo_path(args.output_dir) if args.output_dir else OUTPUT_ROOT
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        ensure_preprocessing_schema(connection)
        source_case = load_case(connection, args.filegroup_id, args.source_mode)
        mode_rows = load_mode_rows(connection, args.filegroup_id)
        neighbor_rows = load_neighbors(connection, args.filegroup_id, args.source_mode, args.feature_space, args.top_k)
        cluster_info, representative_meta_rows = load_cluster_representatives(
            connection, args.filegroup_id, args.source_mode, args.feature_space
        )
        compare_cases = load_compare_cases(connection, args.source_mode, args.compare_filegroup_id, neighbor_rows)
        representative_cases: list[sqlite3.Row] = []
        seen_representative_ids: set[int] = set()
        for row in representative_meta_rows:
            representative_filegroup_id = int(row["filegroup_id"])
            if representative_filegroup_id == int(args.filegroup_id):
                continue
            if representative_filegroup_id in seen_representative_ids:
                continue
            representative_cases.append(load_case(connection, representative_filegroup_id, args.source_mode))
            seen_representative_ids.add(representative_filegroup_id)
    finally:
        connection.close()

    report_root = output_dir / f"{source_case['filegroup_id']}-{source_case['test_code']}__{source_case['mode']}"
    report_root.mkdir(parents=True, exist_ok=True)
    compare_plot = report_root / "comparison_overlay.png"
    representative_plot = report_root / "cluster_representatives.png"

    plt.style.use("seaborn-v0_8-whitegrid")
    render_overlay_plot(source_case, compare_cases, compare_plot)
    render_representative_plot(source_case, representative_cases[:3], representative_plot)

    dashboard_rel = None
    if source_case["manifest_path"]:
        manifest_path = absolute_path(source_case["manifest_path"])
        if manifest_path is not None:
            dashboard_path = REPO_ROOT / "output" / "small_overlap" / "dashboard" / manifest_path.parent.name / "index.html"
            if dashboard_path.exists():
                dashboard_rel = Path(dashboard_path.name).as_posix()
                target = report_root / dashboard_path.name
                if not target.exists():
                    target.write_text(
                        f'<meta http-equiv="refresh" content="0; url=../../dashboard/{manifest_path.parent.name}/index.html">',
                        encoding="utf-8",
                    )

    html = report_html(
        source_case=source_case,
        mode_rows=mode_rows,
        neighbor_rows=neighbor_rows,
        cluster_info=cluster_info,
        representative_rows=representative_meta_rows,
        compare_plot_name=compare_plot.name,
        representative_plot_name=representative_plot.name,
        dashboard_rel=dashboard_rel,
    )
    report_path = report_root / "index.html"
    report_path.write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "report_html": str(report_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "comparison_overlay": str(compare_plot.relative_to(REPO_ROOT)).replace("\\", "/"),
                "representative_overlay": str(representative_plot.relative_to(REPO_ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
