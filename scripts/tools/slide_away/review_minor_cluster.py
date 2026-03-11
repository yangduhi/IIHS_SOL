from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_FIGURES,
    ARTIFACT_TABLES,
    CASE_MASTER_DEFAULT,
    MODE_ASSIGNMENTS_DEFAULT,
    OUTCOMES_DEFAULT,
    REVIEW_ANALYSIS_ROOT,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review the minor slide_away mode cluster and confounding profile.")
    parser.add_argument("--mode-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--case-master", default=str(CASE_MASTER_DEFAULT))
    parser.add_argument("--outcomes", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--out-minor", default=str(ARTIFACT_TABLES / "minor_cluster_6case_review.csv"))
    parser.add_argument("--out-confounding", default=str(ARTIFACT_TABLES / "mode_confounding_summary.csv"))
    parser.add_argument("--out-fig", default=str(ARTIFACT_FIGURES / "minor_cluster_profile.png"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "04_minor_cluster_review.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/minor_cluster_review.log")
    return parser.parse_args()


def build_minor_review(assignments: pd.DataFrame, case_master: pd.DataFrame, outcomes: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    counts = assignments["cluster_id"].value_counts()
    minor_cluster_id = int(counts.idxmin())
    minor = assignments.loc[assignments["cluster_id"].eq(minor_cluster_id)].copy()
    detail = minor.merge(
        case_master[
            [
                "filegroup_id",
                "report_test_weight_kg_measured",
                "report_curb_weight_kg_measured",
                "report_speed_target_kmh",
                "report_speed_actual_kmh",
                "detail_url",
            ]
        ],
        on="filegroup_id",
        how="left",
    ).merge(
        outcomes[
            [
                "filegroup_id",
                "intrusion_max_resultant_cm",
                "head_hic15",
                "leg_foot_index_left",
                "leg_foot_index_right",
                "outcome_quality_score",
            ]
        ],
        on="filegroup_id",
        how="left",
    )
    detail["minor_cluster_flag"] = 1

    conf_rows: list[dict[str, object]] = []
    for field in ("test_side", "era", "make_model_family"):
        frame = (
            assignments.groupby(["working_mode_label", field])["filegroup_id"]
            .count()
            .reset_index(name="row_count")
            .sort_values(["working_mode_label", "row_count"], ascending=[True, False])
        )
        frame["dimension"] = field
        conf_rows.extend(frame.to_dict("records"))
    confounding = pd.DataFrame(conf_rows)
    return detail.sort_values("filegroup_id").reset_index(drop=True), confounding


def render_figure(detail: pd.DataFrame, output_path: Path) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.scatter(detail["max_abs_ay_g"], detail["max_abs_az_g"], s=55, color="#c04b2f")
    for row in detail.itertuples(index=False):
        axis.annotate(str(row.test_code), (row.max_abs_ay_g, row.max_abs_az_g), fontsize=8, xytext=(4, 4), textcoords="offset points")
    axis.set_xlabel("Max |a_y away| (g)")
    axis.set_ylabel("Max |a_z| (g)")
    axis.set_title("Minor Cluster 6-Case XYZ Pulse Profile")
    axis.grid(alpha=0.2)
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def write_review(detail: pd.DataFrame, confounding: pd.DataFrame, output_path: Path) -> None:
    side_counts = detail["test_side"].value_counts().to_dict()
    year_min = int(detail["vehicle_year"].min()) if not detail.empty else None
    year_max = int(detail["vehicle_year"].max()) if not detail.empty else None
    top_families = detail["make_model_family"].value_counts().to_dict()
    lines = [
        "# Minor Cluster Review",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- minor cluster size: `{len(detail)}`",
        "",
        "## Headline Findings",
        "",
        f"- side distribution: `{side_counts}`",
        f"- year span: `{year_min} - {year_max}`",
        f"- make-model concentration: `{top_families}`",
        "- This cluster is small enough that confounding remains a serious concern.",
        "",
        "## Current Read",
        "",
    ]
    for row in detail.itertuples(index=False):
        lines.append(
            f"- `{row.test_code}` `{row.vehicle_make_model}`: "
            f"`DeltaVx {row.delta_vx_mps:.3f}`, `DeltaVy_away {row.delta_vy_away_mps:.3f}`, `RI {row.ri:.3f}`, "
            f"`ax {row.max_abs_ax_g:.2f}`, `ay {row.max_abs_ay_g:.2f}`, `az {row.max_abs_az_g:.2f}`, "
            f"intrusion `{row.intrusion_max_resultant_cm}`, HIC15 `{row.head_hic15}`"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "- Keep this cluster as review-only.",
            "- Read it as a high-lateral pocket until side, era, and weight confounding are closed.",
            "- Do not promote it to a final mode until manual case reading and confounding review are complete.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_dirs()
    assignments = pd.read_csv(resolve_path(args.mode_assignments))
    case_master = pd.read_parquet(resolve_path(args.case_master))
    outcomes = pd.read_parquet(resolve_path(args.outcomes))
    detail, confounding = build_minor_review(assignments, case_master, outcomes)

    minor_path = resolve_path(args.out_minor)
    conf_path = resolve_path(args.out_confounding)
    fig_path = resolve_path(args.out_fig)
    review_path = resolve_path(args.review)
    log_path = resolve_path(args.log)

    minor_path.parent.mkdir(parents=True, exist_ok=True)
    detail.to_csv(minor_path, index=False)
    confounding.to_csv(conf_path, index=False)
    render_figure(detail, fig_path)
    write_review(detail, confounding, review_path)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"minor_csv={repo_relative(minor_path)}",
            f"confounding_csv={repo_relative(conf_path)}",
            f"figure={repo_relative(fig_path)}",
            f"review_md={repo_relative(review_path)}",
            f"minor_cluster_size={len(detail)}",
        ],
    )


if __name__ == "__main__":
    main()
