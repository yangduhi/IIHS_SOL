from __future__ import annotations

import argparse

import pandas as pd

from scripts.tools.slide_away.common import (
    ARTIFACT_TABLES,
    CASE_MASTER_DEFAULT,
    MODE_ASSIGNMENTS_DEFAULT,
    REVIEW_ANALYSIS_ROOT,
    ensure_dirs,
    repo_relative,
    resolve_path,
    utc_now_iso,
    write_log,
)


DIMENSIONS = ("test_side", "era", "make_model_family", "weight_quartile")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review confounding in the selected slide_away mode structure.")
    parser.add_argument("--mode-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--case-master", default=str(CASE_MASTER_DEFAULT))
    parser.add_argument("--out-signoff", default=str(ARTIFACT_TABLES / "mode_confounding_signoff.csv"))
    parser.add_argument("--review", default=str(REVIEW_ANALYSIS_ROOT / "12_mode_confounding_signoff.md"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/mode_confounding_signoff.log")
    return parser.parse_args()


def build_frame(assignments_path, case_master_path) -> pd.DataFrame:
    assignments = pd.read_csv(assignments_path)
    case_master = pd.read_parquet(case_master_path)[
        [
            "filegroup_id",
            "test_side",
            "era",
            "make_model_family",
            "report_test_weight_kg_measured",
            "report_curb_weight_kg_measured",
        ]
    ].copy()
    frame = assignments.merge(case_master, on=["filegroup_id", "test_side", "era", "make_model_family"], how="left")
    frame["weight_proxy_kg"] = pd.to_numeric(frame["report_test_weight_kg_measured"], errors="coerce").fillna(
        pd.to_numeric(frame["report_curb_weight_kg_measured"], errors="coerce")
    )
    valid_weight = frame["weight_proxy_kg"].dropna()
    if len(valid_weight) >= 4:
        frame.loc[valid_weight.index, "weight_quartile"] = pd.qcut(valid_weight, 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
    else:
        frame["weight_quartile"] = pd.NA
    return frame


def build_signoff(frame: pd.DataFrame) -> pd.DataFrame:
    total_n = len(frame)
    rows: list[dict[str, object]] = []
    for cluster_id, cluster in frame.groupby("cluster_id"):
        cluster_n = len(cluster)
        for dimension in DIMENSIONS:
            overall_series = frame[dimension].astype(object).where(frame[dimension].notna(), "missing")
            cluster_series = cluster[dimension].astype(object).where(cluster[dimension].notna(), "missing")
            overall = overall_series.astype(str).value_counts()
            counts = cluster_series.astype(str).value_counts()
            for category, cluster_count in counts.items():
                overall_count = int(overall.get(category, 0))
                overall_share = overall_count / total_n if total_n else 0.0
                cluster_share = cluster_count / cluster_n if cluster_n else 0.0
                enrichment = (cluster_share / overall_share) if overall_share > 0 else float("nan")
                rows.append(
                    {
                        "cluster_id": int(cluster_id),
                        "cluster_n": int(cluster_n),
                        "dimension": dimension,
                        "category": category,
                        "cluster_count": int(cluster_count),
                        "cluster_share": float(cluster_share),
                        "overall_count": overall_count,
                        "overall_share": float(overall_share),
                        "enrichment_ratio": float(enrichment),
                    }
                )
    return pd.DataFrame(rows).sort_values(["cluster_id", "dimension", "enrichment_ratio", "cluster_count"], ascending=[True, True, False, False]).reset_index(drop=True)


def write_review(signoff: pd.DataFrame, output_path) -> None:
    cluster_sizes = signoff.groupby("cluster_id")["cluster_n"].first().sort_values()
    minor_cluster_id = int(cluster_sizes.index[0])
    minor = signoff.loc[signoff["cluster_id"].eq(minor_cluster_id)].copy()
    lines = [
        "# Mode Confounding Sign-Off Review",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        "- scope: selected mode structure only",
        "",
        "## Minor Cluster Headline",
        "",
    ]
    for dimension in ("test_side", "era", "weight_quartile"):
        top = minor.loc[minor["dimension"].eq(dimension)].sort_values(["cluster_share", "enrichment_ratio"], ascending=[False, False]).iloc[0]
        lines.append(
            f"- `{dimension}` top category `{top['category']}`: cluster share `{top['cluster_share']:.4f}`, overall share `{top['overall_share']:.4f}`, enrichment `{top['enrichment_ratio']:.4f}`"
        )
    family_rows = minor.loc[minor["dimension"].eq("make_model_family")].sort_values(["cluster_count", "enrichment_ratio"], ascending=[False, False]).head(5)
    family_summary = ", ".join(f"{row.category} ({int(row.cluster_count)})" for row in family_rows.itertuples(index=False))
    lines.extend(
        [
            f"- family mix: {family_summary}",
            "",
            "## Interpretation",
            "",
            "- The selected minor cluster remains confounded if side or era concentration is near-complete.",
            "- Weight-quartile concentration is a proxy warning, not a full causal explanation.",
            "- Family dispersion alone does not close confounding when the cluster is this small.",
            "",
            "## Recommendation",
            "",
            "- Keep the current selected mode structure on `hold` until these concentration patterns are explicitly accepted or rejected by review.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_dirs()
    frame = build_frame(resolve_path(args.mode_assignments), resolve_path(args.case_master))
    signoff = build_signoff(frame)

    signoff_path = resolve_path(args.out_signoff)
    review_path = resolve_path(args.review)
    log_path = resolve_path(args.log)

    signoff.to_csv(signoff_path, index=False)
    write_review(signoff, review_path)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"signoff_csv={repo_relative(signoff_path)}",
            f"review_md={repo_relative(review_path)}",
            f"row_count={len(signoff)}",
        ],
    )


if __name__ == "__main__":
    main()
