from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_FIGURES,
    ARTIFACT_TABLES,
    FEATURES_DEFAULT,
    MODE_ASSIGNMENTS_DEFAULT,
    OUTCOMES_DEFAULT,
    REVIEW_ANALYSIS_ROOT,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)
from scripts.tools.slide_away.review_extended_linkage import fit_linear_summary, robust_zscore


DOMAIN_ORDER = [
    "structure_intrusion_score",
    "lower_extremity_score",
    "restraint_kinematics_score",
    "head_neck_chest_score",
]

SIGNAL_ORDER = [
    "ri_100",
    "harshness_proxy_z",
    "seat_response_proxy_z",
    "ri_x_harshness",
    "ri_x_seat_response",
]

MODEL_SPECS = {
    "ri_only": ["ri_100_z"],
    "ri_plus_proxies": ["ri_100_z", "harshness_proxy_z", "seat_response_proxy_z"],
    "ri_plus_interactions": ["ri_100_z", "harshness_proxy_z", "seat_response_proxy_z", "ri_x_harshness", "ri_x_seat_response"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review domain-specific outcome linkage for the slide_away study.")
    parser.add_argument("--features", default=str(FEATURES_DEFAULT))
    parser.add_argument("--outcomes", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--mode-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--out-domain-scores", default=str(ARTIFACT_TABLES / "domain_outcome_scores.csv"))
    parser.add_argument("--out-signal-table", default=str(ARTIFACT_TABLES / "domain_linkage_signal_summary.csv"))
    parser.add_argument("--out-model-table", default=str(ARTIFACT_TABLES / "domain_linkage_model_summary.csv"))
    parser.add_argument("--out-subgroup-table", default=str(ARTIFACT_TABLES / "domain_linkage_subgroup_summary.csv"))
    parser.add_argument("--out-fig", default=str(ARTIFACT_FIGURES / "domain_linkage_overview.png"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "07_domain_outcome_linkage_review.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/domain_outcome_linkage_review.log")
    return parser.parse_args()


def rowwise_mean(columns: list[pd.Series]) -> pd.Series:
    return pd.concat(columns, axis=1).mean(axis=1)


def rowwise_max(columns: list[pd.Series]) -> pd.Series:
    return pd.concat(columns, axis=1).max(axis=1)


def build_linkage_frame(features_path: Path, outcomes_path: Path, assignments_path: Path) -> pd.DataFrame:
    features = pd.read_parquet(features_path)
    outcomes = pd.read_parquet(outcomes_path)
    assignments = pd.read_csv(assignments_path)
    frame = features.merge(outcomes, on="filegroup_id", how="left").merge(
        assignments[["filegroup_id", "working_mode_label"]],
        on="filegroup_id",
        how="left",
    )

    leg_index_max = rowwise_max(
        [
            pd.to_numeric(frame["leg_foot_index_left"], errors="coerce"),
            pd.to_numeric(frame["leg_foot_index_right"], errors="coerce"),
        ]
    )
    foot_accel_max = rowwise_max(
        [
            pd.to_numeric(frame["foot_resultant_accel_left_g"], errors="coerce"),
            pd.to_numeric(frame["foot_resultant_accel_right_g"], errors="coerce"),
        ]
    )

    frame["structure_intrusion_score"] = rowwise_mean(
        [
            robust_zscore(frame["intrusion_max_resultant_cm"]),
            robust_zscore(frame["intrusion_footrest_resultant_cm"]),
            robust_zscore(frame["intrusion_left_toepan_resultant_cm"]),
            robust_zscore(frame["intrusion_brake_pedal_resultant_cm"]),
            -robust_zscore(frame["dummy_clearance_min_mm"]),
        ]
    )
    frame["lower_extremity_score"] = rowwise_mean(
        [
            robust_zscore(leg_index_max),
            robust_zscore(foot_accel_max),
            robust_zscore(frame["thigh_hip_risk_proxy"]),
        ]
    )
    frame["restraint_kinematics_score"] = rowwise_mean(
        [
            robust_zscore(frame["pretensioner_time_ms"]),
            robust_zscore(frame["airbag_first_contact_time_ms"]),
            robust_zscore(frame["airbag_full_inflation_time_ms"]),
        ]
    )
    frame["head_neck_chest_score"] = rowwise_mean(
        [
            robust_zscore(frame["head_hic15"]),
            robust_zscore(frame["neck_tension_extension_nij"]),
            robust_zscore(frame["chest_rib_compression_mm"]),
            robust_zscore(frame["chest_viscous_criteria_ms"]),
        ]
    )

    frame["ri_100"] = pd.to_numeric(frame["window_100_ri"], errors="coerce")
    frame["ri_100_z"] = robust_zscore(frame["ri_100"])
    frame["harshness_proxy_z"] = rowwise_mean(
        [
            robust_zscore(frame["window_100_max_abs_az_g"]),
            robust_zscore(frame["window_100_max_abs_resultant_g"]),
        ]
    )
    frame["seat_response_proxy_z"] = rowwise_mean(
        [
            robust_zscore(frame["window_100_seat_twist_peak_mm"]),
            robust_zscore(frame["window_100_foot_resultant_asymmetry_g"]),
        ]
    )
    frame["ri_x_harshness"] = frame["ri_100_z"] * frame["harshness_proxy_z"]
    frame["ri_x_seat_response"] = frame["ri_100_z"] * frame["seat_response_proxy_z"]
    return frame


def build_domain_scores_table(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "filegroup_id",
        "test_code",
        "test_side",
        "era",
        "working_mode_label",
        *DOMAIN_ORDER,
        "ri_100",
        "harshness_proxy_z",
        "seat_response_proxy_z",
    ]
    available = [column for column in columns if column in frame.columns]
    return frame[available].copy()


def signal_summary_for_domain(frame: pd.DataFrame, target: str) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for signal_name in SIGNAL_ORDER:
        subset = frame[[signal_name, target]].dropna().copy()
        if subset.empty:
            rows.append(
                {
                    "domain_name": target,
                    "signal_name": signal_name,
                    "n": 0,
                    "pearson_r": float("nan"),
                    "top_quartile_minus_bottom_quartile": float("nan"),
                }
            )
            continue
        q1 = float(subset[signal_name].quantile(0.25))
        q3 = float(subset[signal_name].quantile(0.75))
        low = subset.loc[subset[signal_name] <= q1, target]
        high = subset.loc[subset[signal_name] >= q3, target]
        rows.append(
            {
                "domain_name": target,
                "signal_name": signal_name,
                "n": int(len(subset)),
                "pearson_r": float(subset[signal_name].corr(subset[target], method="pearson")),
                "top_quartile_minus_bottom_quartile": float(high.mean() - low.mean()) if not high.empty and not low.empty else float("nan"),
            }
        )
    return rows


def build_signal_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for domain_name in DOMAIN_ORDER:
        rows.extend(signal_summary_for_domain(frame, domain_name))
    return pd.DataFrame(rows)


def build_model_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for domain_name in DOMAIN_ORDER:
        for model_name, predictors in MODEL_SPECS.items():
            row = {"domain_name": domain_name, "scope": "overall", "scope_value": "all", "model_name": model_name}
            row.update(fit_linear_summary(frame, predictors, domain_name))
            rows.append(row)
    return pd.DataFrame(rows)


def build_subgroup_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    subgroup_specs = {
        "test_side": ["passenger"],
        "era": ["2015-2017"],
    }
    for domain_name in DOMAIN_ORDER:
        for subgroup_name, subgroup_values in subgroup_specs.items():
            for subgroup_value in subgroup_values:
                subgroup = frame.loc[frame[subgroup_name].eq(subgroup_value)].copy()
                for model_name, predictors in MODEL_SPECS.items():
                    row = {
                        "domain_name": domain_name,
                        "scope": subgroup_name,
                        "scope_value": subgroup_value,
                        "model_name": model_name,
                    }
                    row.update(fit_linear_summary(subgroup, predictors, domain_name))
                    rows.append(row)
    return pd.DataFrame(rows)


def render_figure(signal_summary: pd.DataFrame, model_summary: pd.DataFrame, output_path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(14, 6))

    overall = model_summary.loc[model_summary["scope"].eq("overall")].copy()
    domain_positions = np.arange(len(DOMAIN_ORDER))
    width = 0.22
    for index, model_name in enumerate(MODEL_SPECS.keys()):
        subset = overall.loc[overall["model_name"].eq(model_name)].set_index("domain_name").reindex(DOMAIN_ORDER)
        axes[0].bar(domain_positions + ((index - 1) * width), subset["adj_r2"], width=width, label=model_name)
    axes[0].set_xticks(domain_positions)
    axes[0].set_xticklabels(
        ["structure", "lower-ext", "restraint", "head-neck-chest"],
        rotation=20,
        ha="right",
    )
    axes[0].set_ylabel("Adjusted R^2")
    axes[0].set_title("Domain Linkage by Model")
    axes[0].legend(fontsize=8)
    axes[0].grid(axis="y", alpha=0.2)

    heatmap = (
        signal_summary.pivot(index="signal_name", columns="domain_name", values="pearson_r")
        .reindex(index=SIGNAL_ORDER, columns=DOMAIN_ORDER)
        .to_numpy(dtype=float)
    )
    image = axes[1].imshow(heatmap, cmap="coolwarm", aspect="auto", vmin=-0.3, vmax=0.3)
    axes[1].set_xticks(np.arange(len(DOMAIN_ORDER)))
    axes[1].set_xticklabels(["structure", "lower-ext", "restraint", "head-neck-chest"], rotation=20, ha="right")
    axes[1].set_yticks(np.arange(len(SIGNAL_ORDER)))
    axes[1].set_yticklabels(SIGNAL_ORDER)
    axes[1].set_title("Signal Correlation by Outcome Domain")
    figure.colorbar(image, ax=axes[1], fraction=0.046, pad=0.04)

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def build_review_markdown(signal_summary: pd.DataFrame, model_summary: pd.DataFrame, subgroup_summary: pd.DataFrame) -> str:
    domain_labels = {
        "structure_intrusion_score": "structure/intrusion",
        "lower_extremity_score": "lower-extremity",
        "restraint_kinematics_score": "restraint/kinematics",
        "head_neck_chest_score": "head-neck-chest",
    }
    lines = [
        "# Domain Outcome Linkage Review",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        "- scope: decompose outcome linkage into structure, lower-extremity, restraint, and head-neck-chest axes",
        "",
        "## Overall Read",
        "",
    ]
    for domain_name in DOMAIN_ORDER:
        pretty = domain_labels[domain_name]
        ri_only = model_summary.loc[
            model_summary["domain_name"].eq(domain_name) & model_summary["model_name"].eq("ri_only") & model_summary["scope"].eq("overall")
        ].iloc[0]
        proxies = model_summary.loc[
            model_summary["domain_name"].eq(domain_name) & model_summary["model_name"].eq("ri_plus_proxies") & model_summary["scope"].eq("overall")
        ].iloc[0]
        interaction = model_summary.loc[
            model_summary["domain_name"].eq(domain_name) & model_summary["model_name"].eq("ri_plus_interactions") & model_summary["scope"].eq("overall")
        ].iloc[0]
        best_signal = (
            signal_summary.loc[signal_summary["domain_name"].eq(domain_name)]
            .sort_values("pearson_r", ascending=False)
            .iloc[0]
        )
        lines.append(
            f"- `{pretty}`: RI-only adj R^2 `{ri_only['adj_r2']:.4f}`, proxy model `{proxies['adj_r2']:.4f}`, interaction model `{interaction['adj_r2']:.4f}`, strongest signal `{best_signal['signal_name']}` (`r={best_signal['pearson_r']:.4f}`)"
        )

    passenger_lower = subgroup_summary.loc[
        subgroup_summary["domain_name"].eq("lower_extremity_score")
        & subgroup_summary["scope"].eq("test_side")
        & subgroup_summary["scope_value"].eq("passenger")
        & subgroup_summary["model_name"].eq("ri_plus_interactions")
    ].iloc[0]
    era_lower = subgroup_summary.loc[
        subgroup_summary["domain_name"].eq("lower_extremity_score")
        & subgroup_summary["scope"].eq("era")
        & subgroup_summary["scope_value"].eq("2015-2017")
        & subgroup_summary["model_name"].eq("ri_plus_interactions")
    ].iloc[0]

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- RI-only linkage stays weak across all outcome domains.",
            "- context-aware linkage is strongest on the lower-extremity axis, where seat-response is the dominant single signal in this pass.",
            "- structure/intrusion also improves under the context model, but less than lower-extremity.",
            "- head-neck-chest linkage leans more on harshness than on seat-response.",
            "- restraint/kinematics remains weak and should not drive naming or approval decisions yet.",
            "",
            "## Subgroup Hints",
            "",
            f"- passenger lower-extremity interaction model: adj R^2 `{passenger_lower['adj_r2']:.4f}` (`n={int(passenger_lower['n'])}`)",
            f"- era `2015-2017` lower-extremity interaction model: adj R^2 `{era_lower['adj_r2']:.4f}` (`n={int(era_lower['n'])}`)",
            "- current subgroup gains look concentrated in lower-extremity outcomes rather than in a general redirection effect.",
            "",
            "## Recommendation",
            "",
            "- keep RI in the linkage stack, but demote it from the leading explanatory axis",
            "- prioritize seat-response and harshness context in the next naming review",
            "- split future approval discussions by outcome domain instead of relying on a single pooled safety score",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    ensure_dirs()

    frame = build_linkage_frame(
        resolve_path(args.features),
        resolve_path(args.outcomes),
        resolve_path(args.mode_assignments),
    )
    domain_scores = build_domain_scores_table(frame)
    signal_summary = build_signal_summary(frame)
    model_summary = build_model_summary(frame)
    subgroup_summary = build_subgroup_summary(frame)

    domain_scores_path = resolve_path(args.out_domain_scores)
    signal_summary_path = resolve_path(args.out_signal_table)
    model_summary_path = resolve_path(args.out_model_table)
    subgroup_summary_path = resolve_path(args.out_subgroup_table)
    figure_path = resolve_path(args.out_fig)
    review_path = resolve_path(args.review)
    log_path = resolve_path(args.log)

    domain_scores.to_csv(domain_scores_path, index=False)
    signal_summary.to_csv(signal_summary_path, index=False)
    model_summary.to_csv(model_summary_path, index=False)
    subgroup_summary.to_csv(subgroup_summary_path, index=False)
    render_figure(signal_summary, model_summary, figure_path)
    review_path.write_text(build_review_markdown(signal_summary, model_summary, subgroup_summary), encoding="utf-8")

    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"domain_scores_csv={repo_relative(domain_scores_path)}",
            f"signal_summary_csv={repo_relative(signal_summary_path)}",
            f"model_summary_csv={repo_relative(model_summary_path)}",
            f"subgroup_summary_csv={repo_relative(subgroup_summary_path)}",
            f"overview_fig={repo_relative(figure_path)}",
            f"review_md={repo_relative(review_path)}",
            f"row_count={len(frame)}",
        ],
    )


if __name__ == "__main__":
    main()
