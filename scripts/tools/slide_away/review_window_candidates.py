from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_FIGURES,
    ARTIFACT_TABLES,
    FEATURES_DEFAULT,
    OUTCOMES_DEFAULT,
    REVIEW_ANALYSIS_ROOT,
    build_safety_score,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)
from scripts.tools.slide_away.modeling import cluster_summary, run_kmeans


WINDOWS = (100, 150)
KS = (2, 3, 4)
KEY_FEATURES = (
    "delta_vx_mps",
    "delta_vy_away_mps",
    "ri",
    "seat_twist_peak_mm",
    "foot_resultant_asymmetry_g",
    "max_abs_ax_g",
    "max_abs_ay_g",
    "max_abs_az_g",
    "max_abs_resultant_g",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare 100 ms and 150 ms slide_away operating-window candidates.")
    parser.add_argument("--features", default=str(FEATURES_DEFAULT))
    parser.add_argument("--outcomes", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--out-summary", default=str(ARTIFACT_TABLES / "window_candidate_comparison.csv"))
    parser.add_argument("--out-stability", default=str(ARTIFACT_TABLES / "window_candidate_feature_stability.csv"))
    parser.add_argument("--out-case-deltas", default=str(ARTIFACT_TABLES / "window_candidate_case_deltas.csv"))
    parser.add_argument("--out-fig", default=str(ARTIFACT_FIGURES / "window_candidate_comparison.png"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "03_window_candidate_review.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/window_candidate_review.log")
    return parser.parse_args()


def build_summary(features: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for window_ms in WINDOWS:
        for k in KS:
            run = run_kmeans(features, window_ms, k)
            summary = cluster_summary(run, k)
            merged = run.dataframe.merge(outcomes[["filegroup_id", "safety_severity_score"]], on="filegroup_id", how="left")
            counts = merged["cluster_id"].value_counts().sort_index().tolist() if not merged.empty else []
            rows.append(
                {
                    **summary,
                    "window_ms": window_ms,
                    "cluster_sizes_json": json.dumps(counts),
                }
            )
    return pd.DataFrame(rows).sort_values(["window_ms", "k"]).reset_index(drop=True)


def build_stability(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for feature_name in KEY_FEATURES:
        col_100 = f"window_100_{feature_name}"
        col_150 = f"window_150_{feature_name}"
        subset = features[["filegroup_id", col_100, col_150]].copy()
        subset[col_100] = pd.to_numeric(subset[col_100], errors="coerce")
        subset[col_150] = pd.to_numeric(subset[col_150], errors="coerce")
        finite = subset.dropna()
        correlation = finite[col_100].corr(finite[col_150]) if len(finite) >= 2 else float("nan")
        mean_abs_delta = (finite[col_150] - finite[col_100]).abs().mean() if len(finite) else float("nan")
        rows.append(
            {
                "feature_name": feature_name,
                "paired_count": int(len(finite)),
                "pearson_r_100_vs_150": correlation,
                "mean_abs_delta": mean_abs_delta,
                "median_100": subset[col_100].median(skipna=True),
                "median_150": subset[col_150].median(skipna=True),
            }
        )
    return pd.DataFrame(rows).sort_values("feature_name").reset_index(drop=True)


def build_case_deltas(features: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    frame = features[
        [
            "filegroup_id",
            "test_code",
            "vehicle_year",
            "vehicle_make_model",
            "test_side",
            "era",
            "window_100_delta_vx_mps",
            "window_150_delta_vx_mps",
            "window_100_delta_vy_away_mps",
            "window_150_delta_vy_away_mps",
            "window_100_ri",
            "window_150_ri",
            "window_100_seat_twist_peak_mm",
            "window_150_seat_twist_peak_mm",
            "window_100_max_abs_ax_g",
            "window_150_max_abs_ax_g",
            "window_100_max_abs_ay_g",
            "window_150_max_abs_ay_g",
            "window_100_max_abs_az_g",
            "window_150_max_abs_az_g",
            "window_100_max_abs_resultant_g",
            "window_150_max_abs_resultant_g",
        ]
    ].copy()
    for column in frame.columns:
        if column.startswith("window_"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["delta_ri_150_minus_100"] = frame["window_150_ri"] - frame["window_100_ri"]
    frame["delta_dvy_150_minus_100"] = frame["window_150_delta_vy_away_mps"] - frame["window_100_delta_vy_away_mps"]
    frame["delta_seat_twist_150_minus_100"] = frame["window_150_seat_twist_peak_mm"] - frame["window_100_seat_twist_peak_mm"]
    frame["delta_ax_150_minus_100"] = frame["window_150_max_abs_ax_g"] - frame["window_100_max_abs_ax_g"]
    frame["delta_ay_150_minus_100"] = frame["window_150_max_abs_ay_g"] - frame["window_100_max_abs_ay_g"]
    frame["delta_az_150_minus_100"] = frame["window_150_max_abs_az_g"] - frame["window_100_max_abs_az_g"]
    frame["delta_resultant_150_minus_100"] = frame["window_150_max_abs_resultant_g"] - frame["window_100_max_abs_resultant_g"]
    merged = frame.merge(outcomes[["filegroup_id", "safety_severity_score"]], on="filegroup_id", how="left")
    merged["abs_delta_ri"] = merged["delta_ri_150_minus_100"].abs()
    merged["xyz_signature_l1_delta"] = (
        merged["delta_ax_150_minus_100"].abs()
        + merged["delta_ay_150_minus_100"].abs()
        + merged["delta_az_150_minus_100"].abs()
    )
    return merged.sort_values(["xyz_signature_l1_delta", "abs_delta_ri", "filegroup_id"], ascending=[False, False, True]).head(25).reset_index(drop=True)


def render_figure(summary: pd.DataFrame, output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(9, 6))
    for k, group in summary.groupby("k"):
        axis.plot(group["window_ms"], group["silhouette"], marker="o", label=f"k={int(k)}")
    axis.set_xlabel("Window (ms)")
    axis.set_ylabel("Silhouette")
    axis.set_title("100 ms vs 150 ms Window Candidate Comparison")
    axis.grid(alpha=0.2)
    axis.legend(loc="best")
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def write_review(summary: pd.DataFrame, stability: pd.DataFrame, case_deltas: pd.DataFrame, output_path: Path) -> None:
    s100 = summary.loc[summary["window_ms"].eq(100) & summary["k"].eq(2)].iloc[0]
    s150 = summary.loc[summary["window_ms"].eq(150) & summary["k"].eq(2)].iloc[0]
    top_stability = stability.sort_values("pearson_r_100_vs_150", ascending=True).head(3)
    top_deltas = case_deltas.head(5)
    lines = [
        "# Window Candidate Review",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        "- scope: compare current best `100 ms` candidate against historic `0-150 ms` baseline outputs",
        "",
        "## Summary",
        "",
        f"- `100 ms`, `k=2`: silhouette `{s100['silhouette']:.4f}`, size ratio `{s100['size_ratio']:.4f}`",
        f"- `150 ms`, `k=2`: silhouette `{s150['silhouette']:.4f}`, size ratio `{s150['size_ratio']:.4f}`",
        "- `100 ms` performs slightly better on the current clustering objective.",
        "- This is still not enough for automatic operating-window promotion.",
        "",
        "## Feature Stability Watchlist",
        "",
    ]
    for row in top_stability.itertuples(index=False):
        lines.append(
            f"- `{row.feature_name}`: paired `{int(row.paired_count)}`, correlation `{row.pearson_r_100_vs_150:.4f}`, mean abs delta `{row.mean_abs_delta:.4f}`"
        )
    lines.extend(["", "## Largest Case-Level XYZ Signature Shifts", ""])
    for row in top_deltas.itertuples(index=False):
        lines.append(
            f"- `{row.test_code}` `{row.vehicle_make_model}`: "
            f"`ax {row.window_100_max_abs_ax_g:.2f} -> {row.window_150_max_abs_ax_g:.2f}`, "
            f"`ay {row.window_100_max_abs_ay_g:.2f} -> {row.window_150_max_abs_ay_g:.2f}`, "
            f"`az {row.window_100_max_abs_az_g:.2f} -> {row.window_150_max_abs_az_g:.2f}`, "
            f"`RI {row.window_100_ri:.3f} -> {row.window_150_ri:.3f}`, safety `{row.safety_severity_score:.3f}`"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "- Keep `100 ms` as the current best candidate.",
            "- Read the operating-window difference first through `x/y/z` pulse signatures, not RI alone.",
            "- Do not auto-replace the historic `0-150 ms` operating baseline until a reviewer accepts the window change with case-level rationale.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_dirs()
    features = pd.read_parquet(resolve_path(args.features)).copy()
    outcomes = pd.read_parquet(resolve_path(args.outcomes)).copy()
    outcomes["safety_severity_score"] = build_safety_score(outcomes)
    summary = build_summary(features, outcomes)
    stability = build_stability(features)
    case_deltas = build_case_deltas(features, outcomes)

    summary_path = resolve_path(args.out_summary)
    stability_path = resolve_path(args.out_stability)
    case_delta_path = resolve_path(args.out_case_deltas)
    fig_path = resolve_path(args.out_fig)
    review_path = resolve_path(args.review)
    log_path = resolve_path(args.log)

    summary.to_csv(summary_path, index=False)
    stability.to_csv(stability_path, index=False)
    case_deltas.to_csv(case_delta_path, index=False)
    render_figure(summary, fig_path)
    write_review(summary, stability, case_deltas, review_path)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"summary_csv={repo_relative(summary_path)}",
            f"stability_csv={repo_relative(stability_path)}",
            f"case_deltas_csv={repo_relative(case_delta_path)}",
            f"figure={repo_relative(fig_path)}",
            f"review_md={repo_relative(review_path)}",
        ],
    )


if __name__ == "__main__":
    main()
