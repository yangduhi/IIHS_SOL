from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_FIGURES,
    ARTIFACT_TABLES,
    FEATURES_DEFAULT,
    OUTCOMES_DEFAULT,
    WINDOW_GRID_MS,
    build_safety_score,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)
from scripts.tools.slide_away.modeling import cluster_summary, run_kmeans


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the slide_away window sensitivity sweep.")
    parser.add_argument("--features", default=str(FEATURES_DEFAULT))
    parser.add_argument("--outcomes", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--out", default=str(ARTIFACT_TABLES / "window_sweep_summary.csv"))
    parser.add_argument("--fig", default=str(ARTIFACT_FIGURES / "window_sweep_comparison.png"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/window_sweep.log")
    return parser.parse_args()


def eta_squared(labels: pd.Series, values: pd.Series) -> float:
    frame = pd.DataFrame({"label": labels, "value": values}).dropna()
    if frame.empty or frame["label"].nunique() <= 1:
        return float("nan")
    grand_mean = frame["value"].mean()
    between = 0.0
    total = float(((frame["value"] - grand_mean) ** 2).sum())
    if total <= 0:
        return float("nan")
    for _, group in frame.groupby("label"):
        between += float(len(group) * (group["value"].mean() - grand_mean) ** 2)
    return between / total


def build_window_sweep(features_path: Path, outcomes_path: Path) -> pd.DataFrame:
    features = pd.read_parquet(features_path)
    outcomes = pd.read_parquet(outcomes_path)
    merged = features.merge(outcomes[["filegroup_id"]], on="filegroup_id", how="left")
    merged["safety_severity_score"] = build_safety_score(outcomes.set_index("filegroup_id").reindex(merged["filegroup_id"]).reset_index(drop=True))

    rows: list[dict[str, object]] = []
    for window_ms in WINDOW_GRID_MS:
        candidate_rows: list[dict[str, object]] = []
        for k in (2, 3, 4):
            run = run_kmeans(merged, window_ms, k)
            summary = cluster_summary(run, k)
            safety_eta = eta_squared(run.dataframe["cluster_id"], merged.loc[run.dataframe.index, "safety_severity_score"]) if not run.dataframe.empty else float("nan")
            imbalance_penalty = math.log(summary["size_ratio"]) if summary["size_ratio"] and summary["size_ratio"] > 0 else 0.0
            composite_score = (
                (summary["silhouette"] if math.isfinite(summary["silhouette"]) else -1.0)
                + (0.20 * safety_eta if math.isfinite(safety_eta) else 0.0)
                - (0.03 * imbalance_penalty)
            )
            candidate_rows.append(
                {
                    **summary,
                    "outcome_eta_sq": safety_eta,
                    "composite_score": composite_score,
                }
            )
        best = max(candidate_rows, key=lambda row: row["composite_score"])
        rows.append(
            {
                "window_ms": window_ms,
                "best_k": best["k"],
                "sample_count": best["sample_count"],
                "silhouette": best["silhouette"],
                "size_ratio": best["size_ratio"],
                "outcome_eta_sq": best["outcome_eta_sq"],
                "composite_score": best["composite_score"],
                "candidate_scores_json": json.dumps(candidate_rows, ensure_ascii=False),
            }
        )
    summary = pd.DataFrame(rows).sort_values("window_ms").reset_index(drop=True)
    if not summary.empty:
        summary["selected_operating_window"] = 0
        operating_index = summary.loc[summary["window_ms"].le(150), "composite_score"].idxmax()
        summary.loc[operating_index, "selected_operating_window"] = 1
        summary["selected_robustness_window"] = (summary["window_ms"] == 250).astype(int)
    return summary


def render_figure(summary: pd.DataFrame, output_path: Path) -> None:
    figure, axis_left = plt.subplots(figsize=(10, 6))
    axis_right = axis_left.twinx()
    axis_left.plot(summary["window_ms"], summary["silhouette"], marker="o", color="#1f4e79", label="silhouette")
    axis_left.plot(summary["window_ms"], summary["outcome_eta_sq"], marker="s", color="#c04b2f", label="outcome eta^2")
    axis_right.plot(summary["window_ms"], summary["composite_score"], marker="^", color="#2f6b2f", label="composite")
    axis_left.set_xlabel("Window (ms)")
    axis_left.set_ylabel("Separation / outcome")
    axis_right.set_ylabel("Composite score")
    axis_left.set_title("slide_away Window Sweep")
    axis_left.grid(alpha=0.25)
    handles_left, labels_left = axis_left.get_legend_handles_labels()
    handles_right, labels_right = axis_right.get_legend_handles_labels()
    axis_left.legend(handles_left + handles_right, labels_left + labels_right, loc="lower right")
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def main() -> None:
    args = parse_args()
    ensure_dirs()
    out_path = resolve_path(args.out)
    fig_path = resolve_path(args.fig)
    log_path = resolve_path(args.log)
    summary = build_window_sweep(resolve_path(args.features), resolve_path(args.outcomes))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out_path, index=False)
    render_figure(summary, fig_path)
    operating_row = summary.loc[summary["selected_operating_window"].eq(1)].iloc[0]
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"summary_csv={repo_relative(out_path)}",
            f"figure={repo_relative(fig_path)}",
            f"selected_operating_window_ms={int(operating_row['window_ms'])}",
            f"selected_operating_best_k={int(operating_row['best_k'])}",
        ],
    )


if __name__ == "__main__":
    main()
