from __future__ import annotations

import argparse

import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_TABLES,
    REVIEW_ANALYSIS_ROOT,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review approval logic for the current slide_away package.")
    parser.add_argument("--extended-models", default=str(ARTIFACT_TABLES / "extended_linkage_model_summary.csv"))
    parser.add_argument("--domain-models", default=str(ARTIFACT_TABLES / "domain_linkage_model_summary.csv"))
    parser.add_argument("--subgroup-summary", default=str(ARTIFACT_TABLES / "preregistered_lower_ext_validation_summary.csv"))
    parser.add_argument("--out-summary", default=str(ARTIFACT_TABLES / "approval_logic_summary.csv"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "13_domain_approval_logic_review.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/approval_logic_review.log")
    return parser.parse_args()


def build_summary(extended_path, domain_path, subgroup_path) -> pd.DataFrame:
    pooled = pd.read_csv(extended_path)
    domain = pd.read_csv(domain_path)
    subgroup = pd.read_csv(subgroup_path)

    rows: list[dict[str, object]] = []
    pooled_rows = pooled.loc[pooled["scope"].eq("overall")].copy().set_index("model_name")
    rows.append(
        {
            "approval_axis": "pooled_safety_severity",
            "ri_only_adj_r2": float(pooled_rows.loc["ri_only", "adj_r2"]),
            "proxy_adj_r2": float(pooled_rows.loc["ri_plus_proxies", "adj_r2"]),
            "interaction_adj_r2": float(pooled_rows.loc["ri_plus_interactions", "adj_r2"]),
            "recommended_role": "summary_only",
        }
    )
    for domain_name, role in (
        ("lower_extremity_score", "primary_domain"),
        ("head_neck_chest_score", "secondary_domain"),
        ("structure_intrusion_score", "secondary_domain"),
        ("restraint_kinematics_score", "supporting_only"),
    ):
        subset = domain.loc[domain["domain_name"].eq(domain_name) & domain["scope"].eq("overall")].set_index("model_name")
        rows.append(
            {
                "approval_axis": domain_name,
                "ri_only_adj_r2": float(subset.loc["ri_only", "adj_r2"]),
                "proxy_adj_r2": float(subset.loc["ri_plus_proxies", "adj_r2"]),
                "interaction_adj_r2": float(subset.loc["ri_plus_interactions", "adj_r2"]),
                "recommended_role": role,
            }
        )
    subgroup_rows = subgroup.loc[subgroup["group_kind"].eq("subgroup") & subgroup["model_name"].eq("ri_plus_proxies")].copy()
    for row in subgroup_rows.itertuples(index=False):
        interaction_adj_r2 = subgroup.loc[
            subgroup["scope"].eq(row.scope)
            & subgroup["scope_value"].eq(row.scope_value)
            & subgroup["group_kind"].eq("subgroup")
            & subgroup["model_name"].eq("ri_plus_interactions"),
            "adj_r2",
        ].iloc[0]
        rows.append(
            {
                "approval_axis": f"subgroup::{row.scope}={row.scope_value}",
                "ri_only_adj_r2": float("nan"),
                "proxy_adj_r2": float(row.adj_r2),
                "interaction_adj_r2": float(interaction_adj_r2),
                "recommended_role": "exploratory_hint",
            }
        )
    return pd.DataFrame(rows)


def write_review(summary: pd.DataFrame, output_path) -> None:
    pooled = summary.loc[summary["approval_axis"].eq("pooled_safety_severity")].iloc[0]
    lower_ext = summary.loc[summary["approval_axis"].eq("lower_extremity_score")].iloc[0]
    head = summary.loc[summary["approval_axis"].eq("head_neck_chest_score")].iloc[0]
    structure = summary.loc[summary["approval_axis"].eq("structure_intrusion_score")].iloc[0]
    restraint = summary.loc[summary["approval_axis"].eq("restraint_kinematics_score")].iloc[0]
    lines = [
        "# Domain Approval Logic Review",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        "- scope: compare pooled approval logic against domain-aware approval logic",
        "",
        "## Readout",
        "",
        f"- pooled severity proxy model adj R^2: `{pooled['proxy_adj_r2']:.4f}`",
        f"- lower-extremity proxy model adj R^2: `{lower_ext['proxy_adj_r2']:.4f}`",
        f"- head-neck-chest proxy model adj R^2: `{head['proxy_adj_r2']:.4f}`",
        f"- structure/intrusion proxy model adj R^2: `{structure['proxy_adj_r2']:.4f}`",
        f"- restraint/kinematics proxy model adj R^2: `{restraint['proxy_adj_r2']:.4f}`",
        "",
        "## Decision Frame",
        "",
        "- Pooled safety severity should remain a summary-only readout.",
        "- Lower-extremity is the current primary approval domain.",
        "- Head-neck-chest and structure/intrusion can support interpretation when they align with lower-extremity.",
        "- Restraint/kinematics is currently too weak to drive naming or approval.",
        "",
        "## Recommendation",
        "",
        "- Do not approve taxonomy changes from pooled severity alone.",
        "- Use domain scores as the reviewer-facing approval layer until mode standardization becomes more stable.",
        "- Keep subgroup signals as exploratory hints inside the domain frame, not as standalone approval evidence.",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_dirs()
    summary = build_summary(resolve_path(args.extended_models), resolve_path(args.domain_models), resolve_path(args.subgroup_summary))

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
