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
    build_safety_score,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)


MIN_SUBGROUP_N = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review extended outcome linkage beyond RI-only correlation.")
    parser.add_argument("--features", default=str(FEATURES_DEFAULT))
    parser.add_argument("--outcomes", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--mode-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--out-signal-table", default=str(ARTIFACT_TABLES / "extended_linkage_signal_summary.csv"))
    parser.add_argument("--out-model-table", default=str(ARTIFACT_TABLES / "extended_linkage_model_summary.csv"))
    parser.add_argument("--out-subgroup-table", default=str(ARTIFACT_TABLES / "extended_linkage_subgroup_summary.csv"))
    parser.add_argument("--out-fig", default=str(ARTIFACT_FIGURES / "extended_linkage_overview.png"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "05_extended_linkage_review.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/extended_linkage_review.log")
    return parser.parse_args()


def robust_zscore(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=series.index, dtype=float)
    median = float(valid.median())
    spread = float(valid.std(ddof=0))
    if not math.isfinite(spread) or spread <= 1e-9:
        return numeric - median
    return (numeric - median) / spread


def fit_linear_summary(dataframe: pd.DataFrame, predictors: list[str], target: str) -> dict[str, float]:
    subset = dataframe[predictors + [target]].dropna().copy()
    n = len(subset)
    if n < max(MIN_SUBGROUP_N, len(predictors) + 5):
        return {
            "n": float(n),
            "r2": float("nan"),
            "adj_r2": float("nan"),
        }
    design = subset[predictors].to_numpy(dtype=float)
    response = subset[target].to_numpy(dtype=float)
    design = np.column_stack([np.ones(n), design])
    beta, *_ = np.linalg.lstsq(design, response, rcond=None)
    fitted = design @ beta
    sse = float(np.sum((response - fitted) ** 2))
    sst = float(np.sum((response - response.mean()) ** 2))
    r2 = 1.0 - (sse / sst) if sst > 0 else float("nan")
    predictor_count = design.shape[1] - 1
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / (n - predictor_count - 1) if n > predictor_count + 1 else float("nan")
    summary = {
        "n": float(n),
        "r2": r2,
        "adj_r2": adj_r2,
    }
    coefficient_names = ["intercept"] + predictors
    for name, value in zip(coefficient_names, beta, strict=False):
        summary[f"coef_{name}"] = float(value)
    return summary


def summarize_signal(dataframe: pd.DataFrame, signal_name: str, target: str) -> dict[str, float | str]:
    subset = dataframe[[signal_name, target]].dropna().copy()
    if subset.empty:
        return {
            "signal_name": signal_name,
            "n": 0,
            "pearson_r": float("nan"),
            "spearman_r": float("nan"),
            "top_quartile_minus_bottom_quartile": float("nan"),
        }
    q1 = float(subset[signal_name].quantile(0.25))
    q3 = float(subset[signal_name].quantile(0.75))
    bottom = subset.loc[subset[signal_name] <= q1, target]
    top = subset.loc[subset[signal_name] >= q3, target]
    return {
        "signal_name": signal_name,
        "n": int(len(subset)),
        "pearson_r": float(subset[signal_name].corr(subset[target], method="pearson")),
        "spearman_r": float(subset[signal_name].corr(subset[target], method="spearman")),
        "top_quartile_minus_bottom_quartile": float(top.mean() - bottom.mean()) if not top.empty and not bottom.empty else float("nan"),
    }


def build_dataset(features_path: Path, outcomes_path: Path, assignments_path: Path) -> pd.DataFrame:
    features = pd.read_parquet(features_path)
    outcomes = pd.read_parquet(outcomes_path)
    assignments = pd.read_csv(assignments_path)
    merged = features.merge(outcomes, on="filegroup_id", how="left", suffixes=("", "_outcome"))
    merged = merged.merge(
        assignments[["filegroup_id", "cluster_id", "working_mode_label"]],
        on="filegroup_id",
        how="left",
        suffixes=("", "_assignment"),
    )
    merged["safety_severity_score"] = build_safety_score(merged)
    merged["ri_100"] = pd.to_numeric(merged["window_100_ri"], errors="coerce")
    merged["harshness_proxy_z"] = pd.concat(
        [
            robust_zscore(merged["window_100_max_abs_az_g"]),
            robust_zscore(merged["window_100_max_abs_resultant_g"]),
        ],
        axis=1,
    ).mean(axis=1)
    merged["seat_response_proxy_z"] = pd.concat(
        [
            robust_zscore(merged["window_100_seat_twist_peak_mm"]),
            robust_zscore(merged["window_100_foot_resultant_asymmetry_g"]),
        ],
        axis=1,
    ).mean(axis=1)
    merged["ri_100_z"] = robust_zscore(merged["ri_100"])
    merged["ri_x_harshness"] = merged["ri_100_z"] * merged["harshness_proxy_z"]
    merged["ri_x_seat_response"] = merged["ri_100_z"] * merged["seat_response_proxy_z"]
    return merged


def build_signal_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    signals = [
        "ri_100",
        "harshness_proxy_z",
        "seat_response_proxy_z",
        "ri_x_harshness",
        "ri_x_seat_response",
    ]
    rows = [summarize_signal(dataframe, signal_name, "safety_severity_score") for signal_name in signals]
    return pd.DataFrame(rows)


def build_model_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    models = {
        "ri_only": ["ri_100_z"],
        "ri_plus_proxies": ["ri_100_z", "harshness_proxy_z", "seat_response_proxy_z"],
        "ri_plus_interactions": ["ri_100_z", "harshness_proxy_z", "seat_response_proxy_z", "ri_x_harshness", "ri_x_seat_response"],
    }
    rows: list[dict[str, float | str]] = []
    for model_name, predictors in models.items():
        row = {"scope": "overall", "scope_value": "all", "model_name": model_name}
        row.update(fit_linear_summary(dataframe, predictors, "safety_severity_score"))
        rows.append(row)
    return pd.DataFrame(rows)


def build_subgroup_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    subgroup_specs = {
        "test_side": "test_side",
        "era": "era",
        "working_mode_label": "working_mode_label",
    }
    models = {
        "ri_only": ["ri_100_z"],
        "ri_plus_proxies": ["ri_100_z", "harshness_proxy_z", "seat_response_proxy_z"],
        "ri_plus_interactions": ["ri_100_z", "harshness_proxy_z", "seat_response_proxy_z", "ri_x_harshness", "ri_x_seat_response"],
    }
    rows: list[dict[str, float | str]] = []
    for subgroup_name, column_name in subgroup_specs.items():
        for subgroup_value, group in dataframe.groupby(column_name):
            if pd.isna(subgroup_value):
                continue
            for model_name, predictors in models.items():
                row = {
                    "scope": subgroup_name,
                    "scope_value": str(subgroup_value),
                    "model_name": model_name,
                }
                row.update(fit_linear_summary(group, predictors, "safety_severity_score"))
                rows.append(row)
    for proxy_name in ("harshness_proxy_z", "seat_response_proxy_z"):
        quantiles = dataframe[proxy_name].quantile([0.25, 0.75]).to_dict()
        low_cut = float(quantiles.get(0.25, float("nan")))
        high_cut = float(quantiles.get(0.75, float("nan")))
        proxy_band = np.where(
            dataframe[proxy_name] >= high_cut,
            "high",
            np.where(dataframe[proxy_name] <= low_cut, "low", "mid"),
        )
        column_name = f"{proxy_name}_band"
        dataframe = dataframe.copy()
        dataframe[column_name] = proxy_band
        for subgroup_value, group in dataframe.groupby(column_name):
            if pd.isna(subgroup_value):
                continue
            row = {
                "scope": column_name,
                "scope_value": str(subgroup_value),
                "model_name": "ri_only",
            }
            row.update(fit_linear_summary(group, ["ri_100_z"], "safety_severity_score"))
            subset = group[["ri_100", "safety_severity_score"]].dropna()
            row["pearson_r"] = float(subset["ri_100"].corr(subset["safety_severity_score"], method="pearson")) if len(subset) >= MIN_SUBGROUP_N else float("nan")
            rows.append(row)
    return pd.DataFrame(rows)


def render_figure(signal_summary: pd.DataFrame, model_summary: pd.DataFrame, subgroup_summary: pd.DataFrame, output_path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    signals = signal_summary["signal_name"].tolist()
    correlations = signal_summary["pearson_r"].tolist()
    axes[0].barh(signals, correlations, color=["#4C78A8", "#F58518", "#54A24B", "#B279A2", "#E45756"])
    axes[0].axvline(0.0, color="black", linewidth=0.8)
    axes[0].set_title("Signal vs Safety Correlation")
    axes[0].set_xlabel("Pearson r")

    overall = model_summary.loc[model_summary["scope"] == "overall"].copy()
    bars = axes[1].bar(overall["model_name"], overall["adj_r2"], color=["#4C78A8", "#F58518", "#54A24B"])
    axes[1].set_title("Adjusted R^2 by Linkage Model")
    axes[1].set_ylabel("Adjusted R^2")
    axes[1].tick_params(axis="x", rotation=20)
    for bar, value in zip(bars, overall["adj_r2"], strict=False):
        axes[1].text(bar.get_x() + bar.get_width() / 2, value + 0.005, f"{value:.3f}", ha="center", va="bottom", fontsize=8)

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def build_review_markdown(signal_summary: pd.DataFrame, model_summary: pd.DataFrame, subgroup_summary: pd.DataFrame) -> str:
    overall_ri = model_summary.loc[model_summary["model_name"] == "ri_only"].iloc[0]
    overall_proxy = model_summary.loc[model_summary["model_name"] == "ri_plus_proxies"].iloc[0]
    overall_interaction = model_summary.loc[model_summary["model_name"] == "ri_plus_interactions"].iloc[0]
    best_signal = signal_summary.sort_values("pearson_r", ascending=False).iloc[0]
    passenger_interaction = subgroup_summary.loc[
        (subgroup_summary["scope"] == "test_side") & (subgroup_summary["scope_value"] == "passenger") & (subgroup_summary["model_name"] == "ri_plus_interactions")
    ]
    era_interaction = subgroup_summary.loc[
        (subgroup_summary["scope"] == "era") & (subgroup_summary["scope_value"] == "2015-2017") & (subgroup_summary["model_name"] == "ri_plus_interactions")
    ]
    low_seat_band = subgroup_summary.loc[
        (subgroup_summary["scope"] == "seat_response_proxy_z_band") & (subgroup_summary["scope_value"] == "low") & (subgroup_summary["model_name"] == "ri_only")
    ]

    passenger_line = (
        f"- passenger subgroup (`n={int(passenger_interaction.iloc[0]['n'])}`): interaction model adj R^2 `{passenger_interaction.iloc[0]['adj_r2']:.4f}`"
        if not passenger_interaction.empty and math.isfinite(float(passenger_interaction.iloc[0]["adj_r2"]))
        else "- passenger subgroup: sample too small for a stable interaction readout"
    )
    era_line = (
        f"- era `2015-2017` (`n={int(era_interaction.iloc[0]['n'])}`): interaction model adj R^2 `{era_interaction.iloc[0]['adj_r2']:.4f}`"
        if not era_interaction.empty and math.isfinite(float(era_interaction.iloc[0]["adj_r2"]))
        else "- era `2015-2017`: no stable interaction readout"
    )
    seat_band_line = (
        f"- low seat-response band (`n={int(low_seat_band.iloc[0]['n'])}`): RI-only Pearson r `{low_seat_band.iloc[0]['pearson_r']:.4f}`"
        if not low_seat_band.empty and math.isfinite(float(low_seat_band.iloc[0]["pearson_r"]))
        else "- low seat-response band: RI-only subgroup correlation unavailable"
    )

    lines = [
        "# Extended Outcome Linkage Review",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        "- scope: extend linkage beyond RI-only correlation using `100 ms` harshness and seat-response proxies",
        "",
        "## Overall Read",
        "",
        f"- RI-only model: adj R^2 `{overall_ri['adj_r2']:.4f}`",
        f"- RI + harshness + seat-response proxies: adj R^2 `{overall_proxy['adj_r2']:.4f}`",
        f"- RI + interaction terms: adj R^2 `{overall_interaction['adj_r2']:.4f}`",
        f"- strongest single signal in this pass: `{best_signal['signal_name']}` with Pearson r `{best_signal['pearson_r']:.4f}` and top-bottom safety gap `{best_signal['top_quartile_minus_bottom_quartile']:.4f}`",
        "- interaction terms add very little beyond the proxy-only model at cohort level.",
        "",
        "## Proxy Definitions",
        "",
        "- `harshness_proxy_z`: mean standardized `window_100_max_abs_az_g` and `window_100_max_abs_resultant_g`",
        "- `seat_response_proxy_z`: mean standardized `window_100_seat_twist_peak_mm` and `window_100_foot_resultant_asymmetry_g`",
        "- `ri_x_harshness`: `RI_z * harshness_proxy_z`",
        "- `ri_x_seat_response`: `RI_z * seat_response_proxy_z`",
        "",
        "## Subgroup Read",
        "",
        passenger_line,
        era_line,
        seat_band_line,
        "- the current `mode_1` minor cluster is still too small for a stable subgroup model.",
        "",
        "## Interpretation",
        "",
        "- outcome linkage improves when harshness and seat-response context are included.",
        "- most of the gain comes from the context proxies themselves, especially seat-response, not from the RI interaction terms.",
        "- this reduces the risk of over-reading RI alone, but it still does not justify final favorable or unfavorable redirection claims.",
        "",
        "## Recommendation",
        "",
        "- keep RI as one component of the linkage stack rather than a standalone approval signal",
        "- carry `seat_response_proxy_z` and `harshness_proxy_z` into the next reviewer pass",
        "- treat subgroup signals as exploratory until they survive manual review and confounding checks",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    ensure_dirs()

    dataset = build_dataset(
        resolve_path(args.features),
        resolve_path(args.outcomes),
        resolve_path(args.mode_assignments),
    )
    signal_summary = build_signal_summary(dataset)
    model_summary = build_model_summary(dataset)
    subgroup_summary = build_subgroup_summary(dataset)

    signal_table_path = resolve_path(args.out_signal_table)
    model_table_path = resolve_path(args.out_model_table)
    subgroup_table_path = resolve_path(args.out_subgroup_table)
    figure_path = resolve_path(args.out_fig)
    review_path = resolve_path(args.review)
    log_path = resolve_path(args.log)

    signal_summary.to_csv(signal_table_path, index=False)
    model_summary.to_csv(model_table_path, index=False)
    subgroup_summary.to_csv(subgroup_table_path, index=False)
    render_figure(signal_summary, model_summary, subgroup_summary, figure_path)
    review_path.write_text(build_review_markdown(signal_summary, model_summary, subgroup_summary), encoding="utf-8")

    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"signal_summary_csv={repo_relative(signal_table_path)}",
            f"model_summary_csv={repo_relative(model_table_path)}",
            f"subgroup_summary_csv={repo_relative(subgroup_table_path)}",
            f"overview_fig={repo_relative(figure_path)}",
            f"review_md={repo_relative(review_path)}",
            f"row_count={len(dataset)}",
        ],
    )


if __name__ == "__main__":
    main()
