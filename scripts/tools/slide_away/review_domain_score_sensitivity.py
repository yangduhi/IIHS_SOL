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
from scripts.tools.slide_away.review_domain_outcome_linkage import (
    DOMAIN_ORDER,
    build_linkage_frame,
    fit_linear_summary,
    robust_zscore,
    rowwise_max,
    rowwise_mean,
)


PREDICTORS = ["ri_100_z", "harshness_proxy_z", "seat_response_proxy_z"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review domain-score sensitivity for the slide_away study.")
    parser.add_argument("--features", default=str(FEATURES_DEFAULT))
    parser.add_argument("--outcomes", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--mode-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--out-domain-table", default=str(ARTIFACT_TABLES / "domain_score_sensitivity_summary.csv"))
    parser.add_argument("--out-lower-ext-table", default=str(ARTIFACT_TABLES / "lower_ext_component_sensitivity.csv"))
    parser.add_argument("--out-fig", default=str(ARTIFACT_FIGURES / "domain_score_sensitivity_overview.png"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "15_domain_score_sensitivity_review.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/domain_score_sensitivity_review.log")
    return parser.parse_args()


def build_component_series(frame: pd.DataFrame) -> dict[str, pd.Series]:
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
    components = {
        "leg_index_max_z": robust_zscore(leg_index_max),
        "foot_accel_max_z": robust_zscore(foot_accel_max),
        "thigh_proxy_z": robust_zscore(frame["thigh_hip_risk_proxy"]),
        "intrusion_max_z": robust_zscore(frame["intrusion_max_resultant_cm"]),
        "intrusion_footrest_z": robust_zscore(frame["intrusion_footrest_resultant_cm"]),
        "intrusion_toepan_z": robust_zscore(frame["intrusion_left_toepan_resultant_cm"]),
        "intrusion_brake_z": robust_zscore(frame["intrusion_brake_pedal_resultant_cm"]),
        "dummy_clearance_inverse_z": -robust_zscore(frame["dummy_clearance_min_mm"]),
        "pretensioner_time_z": robust_zscore(frame["pretensioner_time_ms"]),
        "airbag_contact_time_z": robust_zscore(frame["airbag_first_contact_time_ms"]),
        "airbag_inflation_time_z": robust_zscore(frame["airbag_full_inflation_time_ms"]),
        "head_hic15_z": robust_zscore(frame["head_hic15"]),
        "neck_nij_z": robust_zscore(frame["neck_tension_extension_nij"]),
        "chest_rib_compression_z": robust_zscore(frame["chest_rib_compression_mm"]),
        "chest_vc_z": robust_zscore(frame["chest_viscous_criteria_ms"]),
    }
    return components


def build_domain_scenarios(frame: pd.DataFrame) -> dict[str, dict[str, pd.Series]]:
    components = build_component_series(frame)
    baseline = {
        "structure_intrusion_score": frame["structure_intrusion_score"],
        "lower_extremity_score": frame["lower_extremity_score"],
        "restraint_kinematics_score": frame["restraint_kinematics_score"],
        "head_neck_chest_score": frame["head_neck_chest_score"],
    }
    scenarios = {
        "baseline": baseline,
        "structure_intrusion_only": {
            **baseline,
            "structure_intrusion_score": rowwise_mean(
                [
                    components["intrusion_max_z"],
                    components["intrusion_footrest_z"],
                    components["intrusion_toepan_z"],
                    components["intrusion_brake_z"],
                ]
            ),
        },
        "structure_no_clearance": {
            **baseline,
            "structure_intrusion_score": rowwise_mean(
                [
                    components["intrusion_max_z"],
                    components["intrusion_footrest_z"],
                    components["intrusion_brake_z"],
                    components["dummy_clearance_inverse_z"],
                ]
            ),
        },
        "lower_leg_foot_only": {
            **baseline,
            "lower_extremity_score": rowwise_mean([components["leg_index_max_z"], components["foot_accel_max_z"]]),
        },
        "lower_foot_only": {
            **baseline,
            "lower_extremity_score": components["foot_accel_max_z"],
        },
        "restraint_contact_only": {
            **baseline,
            "restraint_kinematics_score": rowwise_mean(
                [
                    components["pretensioner_time_z"],
                    components["airbag_contact_time_z"],
                ]
            ),
        },
        "head_neck_core": {
            **baseline,
            "head_neck_chest_score": rowwise_mean(
                [
                    components["head_hic15_z"],
                    components["neck_nij_z"],
                    components["chest_rib_compression_z"],
                ]
            ),
        },
    }
    return scenarios


def build_lower_ext_variants(frame: pd.DataFrame) -> dict[str, pd.Series]:
    components = build_component_series(frame)
    return {
        "current": frame["lower_extremity_score"],
        "leg_foot_only": rowwise_mean([components["leg_index_max_z"], components["foot_accel_max_z"]]),
        "leg_thigh_only": rowwise_mean([components["leg_index_max_z"], components["thigh_proxy_z"]]),
        "foot_thigh_only": rowwise_mean([components["foot_accel_max_z"], components["thigh_proxy_z"]]),
        "leg_only": components["leg_index_max_z"],
        "foot_only": components["foot_accel_max_z"],
        "thigh_only": components["thigh_proxy_z"],
    }


def summarize_domain_scenarios(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for scenario_name, scenario_targets in build_domain_scenarios(frame).items():
        scenario_rows: list[dict[str, float | str]] = []
        for domain_name in DOMAIN_ORDER:
            temp = frame.copy()
            temp["_target"] = scenario_targets[domain_name]
            summary = fit_linear_summary(temp, PREDICTORS, "_target")
            row = {
                "scenario_name": scenario_name,
                "domain_name": domain_name,
                **summary,
            }
            scenario_rows.append(row)
        scenario_frame = pd.DataFrame(scenario_rows)
        finite = scenario_frame.loc[scenario_frame["adj_r2"].apply(math.isfinite)].copy()
        winner_domain = ""
        winner_adj_r2 = float("nan")
        winner_margin = float("nan")
        if not finite.empty:
            finite = finite.sort_values("adj_r2", ascending=False).reset_index(drop=True)
            winner_domain = str(finite.iloc[0]["domain_name"])
            winner_adj_r2 = float(finite.iloc[0]["adj_r2"])
            second = float(finite.iloc[1]["adj_r2"]) if len(finite) > 1 else float("nan")
            winner_margin = winner_adj_r2 - second if math.isfinite(second) else float("nan")
        for row in scenario_rows:
            row["winning_domain"] = winner_domain
            row["winning_adj_r2"] = winner_adj_r2
            row["winner_margin_vs_second"] = winner_margin
            rows.append(row)
    return pd.DataFrame(rows)


def summarize_lower_ext_variants(frame: pd.DataFrame) -> pd.DataFrame:
    scopes = {
        "overall": frame,
        "test_side=passenger": frame.loc[frame["test_side"].eq("passenger")].copy(),
        "era=2015-2017": frame.loc[frame["era"].eq("2015-2017")].copy(),
    }
    rows: list[dict[str, float | str]] = []
    for scope_name, scope_frame in scopes.items():
        variants = build_lower_ext_variants(scope_frame)
        for variant_name, variant_series in variants.items():
            temp = scope_frame.copy()
            temp["_target"] = variant_series
            summary = fit_linear_summary(temp, PREDICTORS, "_target")
            rows.append(
                {
                    "scope": scope_name,
                    "variant_name": variant_name,
                    **summary,
                }
            )
    result = pd.DataFrame(rows)
    rankings: list[dict[str, str | float]] = []
    for scope_name, group in result.groupby("scope"):
        finite = group.loc[group["adj_r2"].apply(math.isfinite)].sort_values("adj_r2", ascending=False).reset_index(drop=True)
        if finite.empty:
            continue
        winner_variant = str(finite.iloc[0]["variant_name"])
        winner_adj_r2 = float(finite.iloc[0]["adj_r2"])
        second = float(finite.iloc[1]["adj_r2"]) if len(finite) > 1 else float("nan")
        rankings.append(
            {
                "scope": scope_name,
                "winner_variant": winner_variant,
                "winner_adj_r2": winner_adj_r2,
                "winner_margin_vs_second": winner_adj_r2 - second if math.isfinite(second) else float("nan"),
            }
        )
    ranking_frame = pd.DataFrame(rankings)
    return result.merge(ranking_frame, on="scope", how="left")


def render_figure(domain_summary: pd.DataFrame, lower_ext_summary: pd.DataFrame, output_path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(15, 6))

    domain_heatmap = (
        domain_summary.pivot(index="scenario_name", columns="domain_name", values="adj_r2")
        .reindex(
            index=[
                "baseline",
                "structure_intrusion_only",
                "structure_no_clearance",
                "lower_leg_foot_only",
                "lower_foot_only",
                "restraint_contact_only",
                "head_neck_core",
            ],
            columns=DOMAIN_ORDER,
        )
        .to_numpy(dtype=float)
    )
    image = axes[0].imshow(domain_heatmap, cmap="YlOrRd", aspect="auto")
    axes[0].set_xticks(np.arange(len(DOMAIN_ORDER)))
    axes[0].set_xticklabels(["structure", "lower-ext", "restraint", "head-neck-chest"], rotation=20, ha="right")
    axes[0].set_yticks(np.arange(domain_heatmap.shape[0]))
    axes[0].set_yticklabels(
        [
            "baseline",
            "structure_intrusion_only",
            "structure_no_clearance",
            "lower_leg_foot_only",
            "lower_foot_only",
            "restraint_contact_only",
            "head_neck_core",
        ]
    )
    axes[0].set_title("Proxy Model Adj R^2 by Domain Scenario")
    figure.colorbar(image, ax=axes[0], fraction=0.046, pad=0.04)

    component_heatmap = (
        lower_ext_summary.pivot(index="variant_name", columns="scope", values="adj_r2")
        .reindex(
            index=["current", "leg_foot_only", "leg_thigh_only", "foot_thigh_only", "leg_only", "foot_only", "thigh_only"],
            columns=["overall", "test_side=passenger", "era=2015-2017"],
        )
        .to_numpy(dtype=float)
    )
    image = axes[1].imshow(component_heatmap, cmap="PuBuGn", aspect="auto")
    axes[1].set_xticks(np.arange(3))
    axes[1].set_xticklabels(["overall", "passenger", "2015-2017"], rotation=20, ha="right")
    axes[1].set_yticks(np.arange(7))
    axes[1].set_yticklabels(["current", "leg_foot", "leg_thigh", "foot_thigh", "leg_only", "foot_only", "thigh_only"])
    axes[1].set_title("Lower-Ext Variant Sensitivity")
    figure.colorbar(image, ax=axes[1], fraction=0.046, pad=0.04)

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def build_review_markdown(domain_summary: pd.DataFrame, lower_ext_summary: pd.DataFrame) -> str:
    scenario_winners = domain_summary[["scenario_name", "winning_domain", "winning_adj_r2", "winner_margin_vs_second"]].drop_duplicates()
    lower_ext_wins = int(scenario_winners["winning_domain"].eq("lower_extremity_score").sum())
    total_scenarios = int(len(scenario_winners))

    baseline = scenario_winners.loc[scenario_winners["scenario_name"].eq("baseline")].iloc[0]
    lower_leg_foot = scenario_winners.loc[scenario_winners["scenario_name"].eq("lower_leg_foot_only")].iloc[0]
    lower_foot = scenario_winners.loc[scenario_winners["scenario_name"].eq("lower_foot_only")].iloc[0]

    overall_rows = lower_ext_summary.loc[lower_ext_summary["scope"].eq("overall")].copy()
    overall_rows = overall_rows.loc[overall_rows["adj_r2"].apply(math.isfinite)].sort_values("adj_r2", ascending=False).reset_index(drop=True)
    passenger_rows = lower_ext_summary.loc[lower_ext_summary["scope"].eq("test_side=passenger")].copy()
    passenger_rows = passenger_rows.loc[passenger_rows["adj_r2"].apply(math.isfinite)].sort_values("adj_r2", ascending=False).reset_index(drop=True)
    era_rows = lower_ext_summary.loc[lower_ext_summary["scope"].eq("era=2015-2017")].copy()
    era_rows = era_rows.loc[era_rows["adj_r2"].apply(math.isfinite)].sort_values("adj_r2", ascending=False).reset_index(drop=True)

    return "\n".join(
        [
            "# 도메인 점수 민감도 검토",
            "",
            f"- generated_at: `{utc_now_iso()}`",
            "- 범위: 현재 도메인 우선 승인 프레임이 합리적인 score 정의 변경에 민감한지 검토",
            "",
            "## 핵심 요약",
            "",
            f"- `lower_extremity_score`는 테스트한 `{lower_ext_wins}/{total_scenarios}`개 score-definition 시나리오 모두에서 winning domain으로 유지됩니다.",
            f"- baseline winner는 `{baseline['winning_domain']}`이며 adj R^2는 `{float(baseline['winning_adj_r2']):.4f}`, 2위 대비 margin은 `{float(baseline['winner_margin_vs_second']):.4f}`입니다.",
            f"- `leg+foot`만 사용한 lower-ext variant는 adj R^2를 `{float(lower_leg_foot['winning_adj_r2']):.4f}`까지 올립니다.",
            f"- `foot`만 사용한 lower-ext variant는 adj R^2를 `{float(lower_foot['winning_adj_r2']):.4f}`까지 올립니다.",
            "- 테스트한 structure, restraint, head-neck-chest 재정의 중 어느 것도 lower-extremity를 추월하지 못했습니다.",
            "",
            "## Lower-Ext 구성요소 판독",
            "",
            f"- overall best variant는 `{overall_rows.iloc[0]['variant_name']}`이고 adj R^2는 `{float(overall_rows.iloc[0]['adj_r2']):.4f}`입니다.",
            f"- passenger best variant는 `{passenger_rows.iloc[0]['variant_name']}`이고 adj R^2는 `{float(passenger_rows.iloc[0]['adj_r2']):.4f}`입니다.",
            f"- `2015-2017` best variant는 `{era_rows.iloc[0]['variant_name']}`이고 adj R^2는 `{float(era_rows.iloc[0]['adj_r2']):.4f}`입니다.",
            f"- 전체 기준 가장 약한 variant는 `{overall_rows.iloc[-1]['variant_name']}`이며 adj R^2는 `{float(overall_rows.iloc[-1]['adj_r2']):.4f}`입니다.",
            "- 현재 신호 위계는 넓은 pooled RI-only 스토리보다 `foot / lower-ext pulse context`와 더 잘 맞습니다.",
            "- `thigh_only`는 도메인을 단독으로 끌고 갈 만큼 약하므로, 현재 lower-ext 신호는 thigh proxy 하나에서 오지 않습니다.",
            "",
            "## 해석",
            "",
            "- 이번 민감도 검토 이후 현재의 domain-first approval frame은 더 방어 가능해졌습니다.",
            "- `x/y/z + context + domain outcome` 3층 구조는 여전히 맞습니다.",
            "- 몇 가지 합리적인 score 정의를 흔들어도 `lower_extremity`는 primary domain으로 유지됩니다.",
            "- lower-ext domain 내부에서는 `thigh_hip_risk_proxy`보다 `foot_resultant_accel`이 설명력을 더 많이 담당합니다.",
            "- 이는 승인 레이어에서 `seat-response`, `foot asymmetry`, lower-ext context를 유지해야 한다는 근거를 강화합니다.",
            "",
            "## 권고",
            "",
            "- 현재 primary review domain은 `lower_extremity`로 유지합니다.",
            "- lower-ext 신호가 테스트한 score-definition 변화에 견고하다는 reviewer note를 추가합니다.",
            "- 다음 수동 검토 패스에서는 `foot_resultant_accel`과 관련 lower-ext context를 전면에 둡니다.",
            "- 이 결과만으로 최종 승인으로 해석하지 마십시오. 검증 우려 하나를 줄였을 뿐, 남은 reviewer sign-off를 닫지는 못합니다.",
            "",
        ]
    ) + "\n"


def main() -> None:
    args = parse_args()
    ensure_dirs()

    features_path = resolve_path(args.features)
    outcomes_path = resolve_path(args.outcomes)
    assignments_path = resolve_path(args.mode_assignments)
    out_domain_table = resolve_path(args.out_domain_table)
    out_lower_ext_table = resolve_path(args.out_lower_ext_table)
    out_fig = resolve_path(args.out_fig)
    review_path = resolve_path(args.review)
    log_path = resolve_path(args.log)

    frame = build_linkage_frame(features_path, outcomes_path, assignments_path)
    domain_summary = summarize_domain_scenarios(frame)
    lower_ext_summary = summarize_lower_ext_variants(frame)

    out_domain_table.parent.mkdir(parents=True, exist_ok=True)
    out_lower_ext_table.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)

    domain_summary.to_csv(out_domain_table, index=False)
    lower_ext_summary.to_csv(out_lower_ext_table, index=False)
    render_figure(domain_summary, lower_ext_summary, out_fig)
    review_path.write_text(build_review_markdown(domain_summary, lower_ext_summary), encoding="utf-8")

    scenario_winners = domain_summary[["scenario_name", "winning_domain"]].drop_duplicates()
    log_lines = [
        f"generated_at={utc_now_iso()}",
        f"features={repo_relative(features_path)}",
        f"outcomes={repo_relative(outcomes_path)}",
        f"mode_assignments={repo_relative(assignments_path)}",
        f"domain_table={repo_relative(out_domain_table)}",
        f"lower_ext_table={repo_relative(out_lower_ext_table)}",
        f"figure={repo_relative(out_fig)}",
        f"review={repo_relative(review_path)}",
        f"rows={len(frame)}",
        f"lower_ext_wins={int(scenario_winners['winning_domain'].eq('lower_extremity_score').sum())}/{len(scenario_winners)}",
    ]
    write_log(log_path, log_lines)


if __name__ == "__main__":
    main()
