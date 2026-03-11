from __future__ import annotations

import argparse

import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_TABLES,
    MODE_ASSIGNMENTS_DEFAULT,
    REVIEW_ANALYSIS_ROOT,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)


CENTROID_COLUMNS = [
    "window_100_delta_vx_mps",
    "window_100_delta_vy_away_mps",
    "window_100_ri",
    "window_100_max_abs_ax_g",
    "window_100_max_abs_ay_g",
    "window_100_max_abs_az_g",
    "window_100_max_abs_resultant_g",
    "window_100_seat_twist_peak_mm",
    "window_100_foot_resultant_asymmetry_g",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review observation-flavored naming for the current slide_away mode study.")
    parser.add_argument("--mode-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--out-summary", default=str(ARTIFACT_TABLES / "observation_flavored_naming_summary.csv"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "14_observation_flavored_naming_review.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/observation_flavored_naming_review.log")
    return parser.parse_args()


def build_summary(assignments_path) -> pd.DataFrame:
    assignments = pd.read_csv(assignments_path)
    available_columns = [column for column in CENTROID_COLUMNS if column in assignments.columns]
    centroids = assignments.groupby(["cluster_id", "working_mode_label"])[available_columns].mean().reset_index()
    counts = assignments.groupby(["cluster_id", "working_mode_label"])["filegroup_id"].count().reset_index(name="case_count")
    summary = centroids.merge(counts, on=["cluster_id", "working_mode_label"], how="left")
    summary["safe_working_name"] = summary["working_mode_label"]
    largest_cluster = int(counts.sort_values("case_count", ascending=False).iloc[0]["cluster_id"])
    summary.loc[summary["cluster_id"].eq(largest_cluster), "safe_working_name"] = "bulk moderate / unresolved"
    summary.loc[~summary["cluster_id"].eq(largest_cluster), "safe_working_name"] = "high-lateral review pocket"
    return summary.sort_values(["case_count", "cluster_id"], ascending=[False, True]).reset_index(drop=True)


def write_review(summary: pd.DataFrame, output_path) -> None:
    lines = [
        "# Observation-Flavored Naming Review",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        "- scope: safe working names for the currently selected mode structure only",
        "",
        "## Current Safe Names",
        "",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"- `cluster {int(row.cluster_id)}` `{row.safe_working_name}`: "
            f"`n={int(row.case_count)}`, `DeltaVy_away={row.window_100_delta_vy_away_mps:.3f}`, `RI={row.window_100_ri:.3f}`, "
            f"`ax={row.window_100_max_abs_ax_g:.2f}`, `ay={row.window_100_max_abs_ay_g:.2f}`, `az={row.window_100_max_abs_az_g:.2f}`, "
            f"`seat={row.window_100_seat_twist_peak_mm:.2f}`, `foot_asym={row.window_100_foot_resultant_asymmetry_g:.2f}`"
        )
    lines.extend(
        [
            "",
            "## Naming Rule",
            "",
            "- Keep current names observational and reversible.",
            "- Do not promote `redirection-dominant` or `crush-dominant` beyond exploratory notes.",
            "- If a future taxonomy expands, prefer labels such as `kinematics-shifted`, `harsh-pulse dominant`, `seat-response dominant`, and `mixed / unresolved`.",
            "",
            "## Recommendation",
            "",
            "- Use `bulk moderate / unresolved` for the main cluster.",
            "- Use `high-lateral review pocket` for the current minor cluster until confounding and manual reading are closed.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_dirs()
    summary = build_summary(resolve_path(args.mode_assignments))

    summary_path = resolve_path(args.out_summary)
    review_path = resolve_path(args.review)
    log_path = resolve_path(args.log)

    summary.to_csv(summary_path, index=False)
    write_review(summary, review_path)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"summary_csv={repo_relative(summary_path)}",
            f"review_md={repo_relative(review_path)}",
            f"row_count={len(summary)}",
        ],
    )


if __name__ == "__main__":
    main()
