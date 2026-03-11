from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_FIGURES,
    ARTIFACT_TABLES,
    FEATURES_DEFAULT,
    MODE_ASSIGNMENTS_DEFAULT,
    REVIEW_ANALYSIS_ROOT,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)
from scripts.tools.slide_away.modeling import centroid_distances, cluster_summary, run_kmeans


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run slide_away mode-study clustering over the feature mart.")
    parser.add_argument("--features", default=str(FEATURES_DEFAULT))
    parser.add_argument("--window", type=float, default=0.15)
    parser.add_argument("--clusters", nargs="+", type=int, default=[2, 3, 4])
    parser.add_argument("--out-summary", default=str(ARTIFACT_TABLES / "mode_study_summary.csv"))
    parser.add_argument("--out-cases", default=str(ARTIFACT_TABLES / "mode_representative_cases.csv"))
    parser.add_argument("--out-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--out-fig", default=str(ARTIFACT_FIGURES / "mode_study_overview.png"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "02_manual_mode_label_review.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/mode_study.log")
    return parser.parse_args()


def choose_best_run(features: pd.DataFrame, window_ms: int, ks: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    best_run = None
    best_score = -1e9
    for k in ks:
        run = run_kmeans(features, window_ms, k)
        summary = cluster_summary(run, k)
        imbalance_penalty = math.log(summary["size_ratio"]) if summary["size_ratio"] and summary["size_ratio"] > 0 else 0.0
        score = (summary["silhouette"] if math.isfinite(summary["silhouette"]) else -1.0) - (0.035 * imbalance_penalty)
        rows.append({**summary, "selection_score": score})
        if score > best_score:
            best_score = score
            best_run = run
    summary_df = pd.DataFrame(rows).sort_values("k").reset_index(drop=True)
    if not summary_df.empty:
        selected_k = int(summary_df.loc[summary_df["selection_score"].idxmax(), "k"])
        summary_df["selected_flag"] = (summary_df["k"] == selected_k).astype(int)
    return summary_df, best_run


def assign_working_labels(assignments: pd.DataFrame, window_ms: int, selected_k: int) -> pd.DataFrame:
    result = assignments.copy()
    if selected_k != 3 or result.empty:
        result["working_mode_label"] = result["cluster_id"].map(lambda value: f"mode_{int(value)}")
        result["exploratory_interpretation"] = ""
        return result

    prefix = f"window_{window_ms:03d}_"
    centroids = (
        result.groupby("cluster_id")[
            [
                f"{prefix}seat_twist_peak_mm",
                f"{prefix}foot_resultant_asymmetry_g",
                f"{prefix}max_abs_ax_g",
                f"{prefix}max_abs_ay_g",
                f"{prefix}ri",
            ]
        ]
        .mean()
    )
    occupant_cluster = int(
        (centroids[f"{prefix}seat_twist_peak_mm"] + centroids[f"{prefix}foot_resultant_asymmetry_g"]).idxmax()
    )
    remaining = [cluster for cluster in centroids.index if int(cluster) != occupant_cluster]
    harsh_cluster = int(
        (centroids.loc[remaining, f"{prefix}max_abs_ax_g"] + centroids.loc[remaining, f"{prefix}max_abs_ay_g"] + centroids.loc[remaining, f"{prefix}ri"]).idxmax()
    )
    bulk_cluster = int([cluster for cluster in centroids.index if int(cluster) not in {occupant_cluster, harsh_cluster}][0])
    label_map = {
        bulk_cluster: "bulk moderate / mixed holding bucket",
        occupant_cluster: "occupant-compartment-response dominant",
        harsh_cluster: "harsh-pulse dominant",
    }
    exploratory_map = {
        bulk_cluster: "mixed candidate",
        occupant_cluster: "crush-dominant candidate",
        harsh_cluster: "redirection-dominant candidate",
    }
    result["working_mode_label"] = result["cluster_id"].map(label_map)
    result["exploratory_interpretation"] = result["cluster_id"].map(exploratory_map)
    return result


def representative_cases(assignments: pd.DataFrame, window_ms: int) -> pd.DataFrame:
    run = type("RunProxy", (), {})()
    feature_columns = [column for column in assignments.columns if column.startswith(f"window_{window_ms:03d}_")]
    run.dataframe = assignments
    run.feature_columns = feature_columns
    distances = centroid_distances(run)
    ranked = assignments.copy()
    ranked["centroid_distance"] = distances
    ranked = ranked.sort_values(["cluster_id", "centroid_distance", "filegroup_id"]).copy()
    ranked["representative_rank"] = ranked.groupby("cluster_id").cumcount() + 1
    return ranked.loc[ranked["representative_rank"] <= 5].copy()


def render_figure(assignments: pd.DataFrame, window_ms: int, output_path: Path) -> None:
    prefix = f"window_{window_ms:03d}_"
    figure, axis = plt.subplots(figsize=(9, 6))
    for label, group in assignments.groupby("working_mode_label"):
        axis.scatter(
            group[f"{prefix}ri"],
            group[f"{prefix}seat_twist_peak_mm"],
            s=28,
            alpha=0.75,
            label=str(label),
        )
    axis.set_xlabel("RI")
    axis.set_ylabel("Seat Twist Peak (mm)")
    axis.set_title("slide_away Mode Study Overview")
    axis.grid(alpha=0.2)
    axis.legend(loc="best", fontsize=8)
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def write_review(assignments: pd.DataFrame, summary: pd.DataFrame, window_ms: int, review_path: Path) -> None:
    selected_row = summary.loc[summary["selected_flag"].eq(1)].iloc[0]
    lines = [
        "# Manual Mode Label Review",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- selected_k: `{int(selected_row['k'])}`",
        f"- window_ms: `{window_ms}`",
        f"- silhouette: `{selected_row['silhouette']:.4f}`",
        f"- size_ratio: `{selected_row['size_ratio']:.4f}`",
        "",
        "## Working Rule",
        "",
        "- Final `slide_away` mode is not declared here.",
        "- The working labels below are provisional operating names for review only.",
        "- `crush-dominant` and `redirection-dominant` remain exploratory interpretations, not current working labels.",
        "",
        "## Cluster Summary",
        "",
    ]
    counts = assignments.groupby("working_mode_label")["filegroup_id"].count().sort_values(ascending=False)
    for label, count in counts.items():
        exploratory = assignments.loc[assignments["working_mode_label"].eq(label), "exploratory_interpretation"].dropna().iloc[0]
        lines.append(f"- `{label}`: `{int(count)}` cases; exploratory note `{exploratory}`")
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_dirs()
    features = pd.read_parquet(resolve_path(args.features))
    window_ms = int(round(args.window * 1000))
    summary, best_run = choose_best_run(features, window_ms, args.clusters)
    selected_k = int(summary.loc[summary["selected_flag"].eq(1), "k"].iloc[0])
    assignments = assign_working_labels(best_run.dataframe.copy(), window_ms, selected_k)
    representatives = representative_cases(assignments, window_ms)

    summary_path = resolve_path(args.out_summary)
    cases_path = resolve_path(args.out_cases)
    assignments_path = resolve_path(args.out_assignments)
    fig_path = resolve_path(args.out_fig)
    review_path = resolve_path(args.review)
    log_path = resolve_path(args.log)

    summary.to_csv(summary_path, index=False)
    representatives.to_csv(cases_path, index=False)
    assignments.to_csv(assignments_path, index=False)
    render_figure(assignments, window_ms, fig_path)
    write_review(assignments, summary, window_ms, review_path)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"summary_csv={repo_relative(summary_path)}",
            f"representatives_csv={repo_relative(cases_path)}",
            f"assignments_csv={repo_relative(assignments_path)}",
            f"figure={repo_relative(fig_path)}",
            f"review_md={repo_relative(review_path)}",
            f"selected_k={selected_k}",
        ],
    )


if __name__ == "__main__":
    main()
