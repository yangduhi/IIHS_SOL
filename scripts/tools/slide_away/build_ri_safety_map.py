from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_FIGURES,
    ARTIFACT_TABLES,
    FEATURES_DEFAULT,
    MODE_ASSIGNMENTS_DEFAULT,
    OUTCOMES_DEFAULT,
    build_safety_score,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the slide_away RI vs safety linkage map.")
    parser.add_argument("--features", default=str(FEATURES_DEFAULT))
    parser.add_argument("--outcomes", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--mode-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--out-table", default=str(ARTIFACT_TABLES / "ri_vs_safety_map.csv"))
    parser.add_argument("--out-fig", default=str(ARTIFACT_FIGURES / "ri_vs_safety_map.png"))
    parser.add_argument("--out-phase-fig", default=str(ARTIFACT_FIGURES / "delta_vx_delta_vy_phase_plot.png"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/ri_safety_map.log")
    return parser.parse_args()


def render_scatter(dataframe: pd.DataFrame, x: str, y: str, color: str, title: str, output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(9, 6))
    for label, group in dataframe.groupby(color):
        axis.scatter(group[x], group[y], s=28, alpha=0.75, label=str(label))
    axis.set_xlabel(x)
    axis.set_ylabel(y)
    axis.set_title(title)
    axis.grid(alpha=0.2)
    axis.legend(loc="best", fontsize=8)
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def main() -> None:
    args = parse_args()
    ensure_dirs()
    outcomes = pd.read_parquet(resolve_path(args.outcomes))
    assignments = pd.read_csv(resolve_path(args.mode_assignments))
    merged = assignments.merge(outcomes, on="filegroup_id", how="left")
    merged["safety_severity_score"] = build_safety_score(merged)
    merged["ri_band"] = pd.cut(merged["ri"], bins=[-1, 0.2, 0.35, 0.5, 1.0, 10.0], labels=["<=0.2", "0.2-0.35", "0.35-0.5", "0.5-1.0", ">1.0"])

    out_table = resolve_path(args.out_table)
    out_fig = resolve_path(args.out_fig)
    out_phase_fig = resolve_path(args.out_phase_fig)
    log_path = resolve_path(args.log)
    merged.to_csv(out_table, index=False)
    render_scatter(merged.dropna(subset=["ri", "safety_severity_score"]), "ri", "safety_severity_score", "working_mode_label", "RI vs Safety Severity", out_fig)
    render_scatter(merged.dropna(subset=["delta_vx_mps", "delta_vy_away_mps"]), "delta_vx_mps", "delta_vy_away_mps", "working_mode_label", "DeltaVx vs DeltaVy Away", out_phase_fig)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"table_csv={repo_relative(out_table)}",
            f"ri_map_fig={repo_relative(out_fig)}",
            f"phase_fig={repo_relative(out_phase_fig)}",
            f"row_count={len(merged)}",
        ],
    )


if __name__ == "__main__":
    main()
