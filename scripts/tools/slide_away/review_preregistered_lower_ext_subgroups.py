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
    CASE_MASTER_DEFAULT,
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
from scripts.tools.slide_away.review_domain_outcome_linkage import build_linkage_frame
from scripts.tools.slide_away.review_extended_linkage import fit_linear_summary


SUBGROUP_SPECS = (
    ("test_side", "passenger"),
    ("era", "2015-2017"),
)

MODEL_SPECS = {
    "ri_plus_proxies": ["ri_100_z", "harshness_proxy_z", "seat_response_proxy_z"],
    "ri_plus_interactions": ["ri_100_z", "harshness_proxy_z", "seat_response_proxy_z", "ri_x_harshness", "ri_x_seat_response"],
}

TARGET_COLUMN = "lower_extremity_score"
BOOTSTRAP_ROUNDS = 300
BOOTSTRAP_SEED = 20260311


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run preregistered lower-extremity subgroup validation for slide_away.")
    parser.add_argument("--features", default=str(FEATURES_DEFAULT))
    parser.add_argument("--outcomes", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--mode-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--case-master", default=str(CASE_MASTER_DEFAULT))
    parser.add_argument("--out-summary", default=str(ARTIFACT_TABLES / "preregistered_lower_ext_validation_summary.csv"))
    parser.add_argument("--out-fig", default=str(ARTIFACT_FIGURES / "preregistered_lower_ext_validation.png"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "11_preregistered_lower_ext_subgroup_validation.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/preregistered_lower_ext_validation.log")
    return parser.parse_args()


def build_frame(features_path: Path, outcomes_path: Path, assignments_path: Path, case_master_path: Path) -> pd.DataFrame:
    frame = build_linkage_frame(features_path, outcomes_path, assignments_path)
    case_master = pd.read_parquet(case_master_path)[
        [
            "filegroup_id",
            "vehicle_year",
            "make_model_family",
            "report_test_weight_kg_measured",
            "report_curb_weight_kg_measured",
        ]
    ].copy()
    frame = frame.merge(case_master, on="filegroup_id", how="left")
    if "make_model_family_x" in frame.columns or "make_model_family_y" in frame.columns:
        frame["make_model_family"] = frame.get("make_model_family_x", pd.Series(index=frame.index, dtype=object)).fillna(
            frame.get("make_model_family_y", pd.Series(index=frame.index, dtype=object))
        )
    if "vehicle_year_x" in frame.columns or "vehicle_year_y" in frame.columns:
        frame["vehicle_year"] = pd.to_numeric(
            frame.get("vehicle_year_x", pd.Series(index=frame.index, dtype=float)),
            errors="coerce",
        ).fillna(
            pd.to_numeric(frame.get("vehicle_year_y", pd.Series(index=frame.index, dtype=float)), errors="coerce")
        )
    frame["weight_proxy_kg"] = pd.to_numeric(frame["report_test_weight_kg_measured"], errors="coerce").fillna(
        pd.to_numeric(frame["report_curb_weight_kg_measured"], errors="coerce")
    )
    valid_weight = frame["weight_proxy_kg"].dropna()
    if len(valid_weight) >= 4:
        frame.loc[valid_weight.index, "weight_quartile"] = pd.qcut(valid_weight, 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
    else:
        frame["weight_quartile"] = pd.NA
    return frame


def bootstrap_summary(frame: pd.DataFrame, predictors: list[str], target: str, seed_offset: int) -> dict[str, float]:
    subset = frame[predictors + [target]].dropna().copy()
    n = len(subset)
    if n < max(20, len(predictors) + 5):
        return {
            "bootstrap_adj_r2_median": float("nan"),
            "bootstrap_adj_r2_p10": float("nan"),
            "bootstrap_adj_r2_p90": float("nan"),
            "coef_ri_100_z_positive_share": float("nan"),
            "coef_harshness_proxy_z_positive_share": float("nan"),
            "coef_seat_response_proxy_z_positive_share": float("nan"),
        }
    rng = np.random.default_rng(BOOTSTRAP_SEED + seed_offset)
    adj_r2_values: list[float] = []
    sign_track: dict[str, list[float]] = {
        "coef_ri_100_z_positive_share": [],
        "coef_harshness_proxy_z_positive_share": [],
        "coef_seat_response_proxy_z_positive_share": [],
    }
    for _ in range(BOOTSTRAP_ROUNDS):
        sample = subset.iloc[rng.integers(0, n, size=n)].reset_index(drop=True)
        fitted = fit_linear_summary(sample, predictors, target)
        adj = float(fitted.get("adj_r2", float("nan")))
        if math.isfinite(adj):
            adj_r2_values.append(adj)
        for coef_name, out_name in (
            ("coef_ri_100_z", "coef_ri_100_z_positive_share"),
            ("coef_harshness_proxy_z", "coef_harshness_proxy_z_positive_share"),
            ("coef_seat_response_proxy_z", "coef_seat_response_proxy_z_positive_share"),
        ):
            value = float(fitted.get(coef_name, float("nan")))
            if math.isfinite(value):
                sign_track[out_name].append(float(value > 0.0))
    if not adj_r2_values:
        return {
            "bootstrap_adj_r2_median": float("nan"),
            "bootstrap_adj_r2_p10": float("nan"),
            "bootstrap_adj_r2_p90": float("nan"),
            "coef_ri_100_z_positive_share": float("nan"),
            "coef_harshness_proxy_z_positive_share": float("nan"),
            "coef_seat_response_proxy_z_positive_share": float("nan"),
        }
    return {
        "bootstrap_adj_r2_median": float(np.nanmedian(adj_r2_values)),
        "bootstrap_adj_r2_p10": float(np.nanpercentile(adj_r2_values, 10)),
        "bootstrap_adj_r2_p90": float(np.nanpercentile(adj_r2_values, 90)),
        "coef_ri_100_z_positive_share": float(np.nanmean(sign_track["coef_ri_100_z_positive_share"])) if sign_track["coef_ri_100_z_positive_share"] else float("nan"),
        "coef_harshness_proxy_z_positive_share": float(np.nanmean(sign_track["coef_harshness_proxy_z_positive_share"])) if sign_track["coef_harshness_proxy_z_positive_share"] else float("nan"),
        "coef_seat_response_proxy_z_positive_share": float(np.nanmean(sign_track["coef_seat_response_proxy_z_positive_share"])) if sign_track["coef_seat_response_proxy_z_positive_share"] else float("nan"),
    }


def top_share(series: pd.Series) -> tuple[str, float]:
    counts = series.dropna().astype(str).value_counts()
    if counts.empty:
        return "", float("nan")
    label = str(counts.index[0])
    share = float(counts.iloc[0] / counts.sum())
    return label, share


def build_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for scope_name, scope_value in SUBGROUP_SPECS:
        subgroup = frame.loc[frame[scope_name].eq(scope_value)].copy()
        complement = frame.loc[~frame[scope_name].eq(scope_value)].copy()
        for group_kind, group in (("subgroup", subgroup), ("complement", complement)):
            family_label, family_share = top_share(group["make_model_family"])
            weight_label, weight_share = top_share(group["weight_quartile"])
            for model_name, predictors in MODEL_SPECS.items():
                row = {
                    "scope": scope_name,
                    "scope_value": scope_value,
                    "group_kind": group_kind,
                    "model_name": model_name,
                    "top_family": family_label,
                    "top_family_share": family_share,
                    "top_weight_quartile": weight_label,
                    "top_weight_quartile_share": weight_share,
                }
                row.update(fit_linear_summary(group, predictors, TARGET_COLUMN))
                row.update(bootstrap_summary(group, predictors, TARGET_COLUMN, seed_offset=len(rows) + 1))
                rows.append(row)
    return pd.DataFrame(rows)


def render_figure(summary: pd.DataFrame, output_path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    for axis, (scope_name, scope_value) in zip(axes, SUBGROUP_SPECS, strict=False):
        subset = summary.loc[summary["scope"].eq(scope_name) & summary["scope_value"].eq(scope_value)].copy()
        pivot = subset.pivot(index="model_name", columns="group_kind", values="adj_r2").reindex(index=list(MODEL_SPECS.keys()))
        positions = np.arange(len(pivot.index))
        width = 0.32
        subgroup_values = pivot["subgroup"] if "subgroup" in pivot.columns else pd.Series(0.0, index=pivot.index)
        complement_values = pivot["complement"] if "complement" in pivot.columns else pd.Series(0.0, index=pivot.index)
        axis.bar(positions - width / 2, subgroup_values.fillna(0.0), width=width, label="subgroup")
        axis.bar(positions + width / 2, complement_values.fillna(0.0), width=width, label="complement")
        axis.set_xticks(positions)
        axis.set_xticklabels(pivot.index, rotation=20, ha="right")
        axis.set_ylabel("Adjusted R^2")
        axis.set_title(f"{scope_name}={scope_value}")
        axis.grid(axis="y", alpha=0.2)
    axes[0].legend(loc="best")
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def write_review(summary: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Preregistered Lower-Extremity Subgroup Validation",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        "- target: `lower_extremity_score`",
        "- fixed subgroup list: `test_side=passenger`, `era=2015-2017`",
        "- fixed model list: `ri_plus_proxies`, `ri_plus_interactions`",
        "- fixed readout: adjusted R^2 plus bootstrap stability and composition checks",
        "",
        "## Overall Read",
        "",
    ]
    for scope_name, scope_value in SUBGROUP_SPECS:
        subgroup_proxy = summary.loc[
            summary["scope"].eq(scope_name)
            & summary["scope_value"].eq(scope_value)
            & summary["group_kind"].eq("subgroup")
            & summary["model_name"].eq("ri_plus_proxies")
        ].iloc[0]
        subgroup_interaction = summary.loc[
            summary["scope"].eq(scope_name)
            & summary["scope_value"].eq(scope_value)
            & summary["group_kind"].eq("subgroup")
            & summary["model_name"].eq("ri_plus_interactions")
        ].iloc[0]
        complement_proxy = summary.loc[
            summary["scope"].eq(scope_name)
            & summary["scope_value"].eq(scope_value)
            & summary["group_kind"].eq("complement")
            & summary["model_name"].eq("ri_plus_proxies")
        ].iloc[0]
        lines.append(
            f"- `{scope_name}={scope_value}`: proxy adj R^2 `{subgroup_proxy['adj_r2']:.4f}` "
            f"(bootstrap median `{subgroup_proxy['bootstrap_adj_r2_median']:.4f}`; p10-p90 `{subgroup_proxy['bootstrap_adj_r2_p10']:.4f} - {subgroup_proxy['bootstrap_adj_r2_p90']:.4f}`), "
            f"interaction adj R^2 `{subgroup_interaction['adj_r2']:.4f}`, complement proxy adj R^2 `{complement_proxy['adj_r2']:.4f}`"
        )

    lines.extend(["", "## Composition Watch", ""])
    for scope_name, scope_value in SUBGROUP_SPECS:
        subgroup_proxy = summary.loc[
            summary["scope"].eq(scope_name)
            & summary["scope_value"].eq(scope_value)
            & summary["group_kind"].eq("subgroup")
            & summary["model_name"].eq("ri_plus_proxies")
        ].iloc[0]
        lines.append(
            f"- `{scope_name}={scope_value}` top family `{subgroup_proxy['top_family']}` share `{subgroup_proxy['top_family_share']:.4f}`; "
            f"top weight quartile `{subgroup_proxy['top_weight_quartile']}` share `{subgroup_proxy['top_weight_quartile_share']:.4f}`"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The preregistered subgroup signal remains strongest on lower-extremity outcomes, not on pooled severity.",
            "- Passenger and `2015-2017` gains remain review-worthy, but they still require confounding caution before any operating claim.",
            "- If bootstrap support collapses or composition concentration dominates, treat the gain as opportunistic rather than as a stable subgroup rule.",
            "",
            "## Recommendation",
            "",
            "- Keep these subgroup results as structured reviewer evidence, not as approval-grade claims.",
            "- Carry the subgroup read into confounding closure and approval-logic review before any taxonomy change.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_dirs()
    frame = build_frame(
        resolve_path(args.features),
        resolve_path(args.outcomes),
        resolve_path(args.mode_assignments),
        resolve_path(args.case_master),
    )
    summary = build_summary(frame)

    summary_path = resolve_path(args.out_summary)
    figure_path = resolve_path(args.out_fig)
    review_path = resolve_path(args.review)
    log_path = resolve_path(args.log)

    summary.to_csv(summary_path, index=False)
    render_figure(summary, figure_path)
    write_review(summary, review_path)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"summary_csv={repo_relative(summary_path)}",
            f"figure={repo_relative(figure_path)}",
            f"review_md={repo_relative(review_path)}",
            f"row_count={len(frame)}",
        ],
    )


if __name__ == "__main__":
    main()
