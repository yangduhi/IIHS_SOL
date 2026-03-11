from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from scripts.tools.slide_away.common import (
    CASE_MASTER_DEFAULT,
    FEATURES_DEFAULT,
    MODE_ASSIGNMENTS_DEFAULT,
    OUTCOMES_DEFAULT,
    REVIEW_CASEBOOKS_ROOT,
    build_safety_score,
    ensure_dirs,
    resolve_path,
    utc_now_iso,
    write_log,
)


CODEBOOK_ROWS = [
    {"code": "occupant compartment reinforcement", "description": "Changes intended to stiffen or preserve occupant compartment geometry.", "evidence_hint": "intrusion, dash/knee clearance, lower compartment geometry"},
    {"code": "barrier engagement structure", "description": "Changes that alter first-contact engagement or barrier load pick-up.", "evidence_hint": "early pulse, RI, overlap engagement narrative"},
    {"code": "additional load path", "description": "Added structural path for distributing frontal-small-overlap load.", "evidence_hint": "intrusion reduction with limited restraint change"},
    {"code": "wheel-motion modification", "description": "Changes that alter wheel or suspension motion during impact.", "evidence_hint": "footwell outcomes, toe-pan intrusion, lower extremity response"},
    {"code": "restraint modification", "description": "Changes in belt, airbag, or occupant management timing.", "evidence_hint": "pretensioner and airbag timing, dummy kinematics"},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the slide_away matched-pair casebook.")
    parser.add_argument("--case-master", default=str(CASE_MASTER_DEFAULT))
    parser.add_argument("--features", default=str(FEATURES_DEFAULT))
    parser.add_argument("--outcomes", default=str(OUTCOMES_DEFAULT))
    parser.add_argument("--mode-assignments", default=str(MODE_ASSIGNMENTS_DEFAULT))
    parser.add_argument("--out", default=str(REVIEW_CASEBOOKS_ROOT / "01_matched_pair_casebook.md"))
    parser.add_argument("--out-codebook", default=str(REVIEW_CASEBOOKS_ROOT / "02_structure_strategy_codebook.csv"))
    parser.add_argument("--log", default="slide_away/artifacts/logs/mode_casebook.log")
    return parser.parse_args()


def select_pairs(merged: pd.DataFrame, target_count: int = 12) -> pd.DataFrame:
    candidates: list[dict[str, object]] = []
    eligible = merged.dropna(subset=["make_model_family", "ri", "safety_severity_score"]).copy()
    for family, group in eligible.groupby("make_model_family"):
        if len(group) < 2:
            continue
        same_side_groups = [subset for _, subset in group.groupby("test_side") if len(subset) >= 2]
        search_groups = same_side_groups if same_side_groups else [group]
        for subset in search_groups:
            ordered = subset.sort_values(["safety_severity_score", "vehicle_year", "filegroup_id"]).reset_index(drop=True)
            low = ordered.iloc[0]
            high = ordered.iloc[-1]
            if int(low["filegroup_id"]) == int(high["filegroup_id"]):
                continue
            candidates.append(
                {
                    "make_model_family": family,
                    "test_side": low["test_side"] if low["test_side"] == high["test_side"] else "mixed",
                    "lower_filegroup_id": int(low["filegroup_id"]),
                    "higher_filegroup_id": int(high["filegroup_id"]),
                    "lower_test_code": low["test_code"],
                    "higher_test_code": high["test_code"],
                    "lower_working_mode": low["working_mode_label"],
                    "higher_working_mode": high["working_mode_label"],
                    "lower_ri": float(low["ri"]),
                    "higher_ri": float(high["ri"]),
                    "lower_safety_severity_score": float(low["safety_severity_score"]),
                    "higher_safety_severity_score": float(high["safety_severity_score"]),
                    "severity_gap": float(high["safety_severity_score"] - low["safety_severity_score"]),
                    "ri_gap": float(high["ri"] - low["ri"]),
                }
            )
    pairs = pd.DataFrame(candidates)
    if pairs.empty:
        return pairs
    pairs = pairs.sort_values(["severity_gap", "ri_gap"], ascending=[False, False]).drop_duplicates(subset=["make_model_family", "lower_filegroup_id", "higher_filegroup_id"])
    return pairs.head(target_count).reset_index(drop=True)


def write_casebook(pairs: pd.DataFrame, merged: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "# Matched Pair Casebook",
        "",
        f"- generated_at: `{utc_now_iso()}`",
        f"- pair_count: `{len(pairs)}`",
        "- This casebook is a review aid, not a final causal coding result.",
        "",
        "## Pair Summary",
        "",
        "| make_model_family | side | lower_case | higher_case | lower_mode | higher_mode | lower_ri | higher_ri | lower_safety | higher_safety |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in pairs.itertuples(index=False):
        lines.append(
            f"| {row.make_model_family} | {row.test_side} | {row.lower_test_code} ({row.lower_filegroup_id}) | {row.higher_test_code} ({row.higher_filegroup_id}) | {row.lower_working_mode} | {row.higher_working_mode} | {row.lower_ri:.3f} | {row.higher_ri:.3f} | {row.lower_safety_severity_score:.3f} | {row.higher_safety_severity_score:.3f} |"
        )
    lines.extend(["", "## Review Notes", ""])
    for row in pairs.itertuples(index=False):
        low = merged.loc[merged["filegroup_id"].eq(row.lower_filegroup_id)].iloc[0]
        high = merged.loc[merged["filegroup_id"].eq(row.higher_filegroup_id)].iloc[0]
        lines.extend(
            [
                f"### {row.make_model_family}: {row.lower_test_code} vs {row.higher_test_code}",
                "",
                f"- Lower-severity case: `{row.lower_test_code}` (`{row.lower_working_mode}`), RI `{row.lower_ri:.3f}`, safety `{row.lower_safety_severity_score:.3f}`",
                f"- Higher-severity case: `{row.higher_test_code}` (`{row.higher_working_mode}`), RI `{row.higher_ri:.3f}`, safety `{row.higher_safety_severity_score:.3f}`",
                f"- Intrusion contrast: `{low['intrusion_max_resultant_cm']}` vs `{high['intrusion_max_resultant_cm']}` cm",
                f"- Foot index max contrast: `{max(low['leg_foot_index_left'], low['leg_foot_index_right'])}` vs `{max(high['leg_foot_index_left'], high['leg_foot_index_right'])}`",
                f"- Head HIC15 contrast: `{low['head_hic15']}` vs `{high['head_hic15']}`",
                "- Manual reviewer should inspect structural strategy codes, restraint changes, and whether RI shift matches intrusion trend.",
                "",
            ]
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    ensure_dirs()
    case_master = pd.read_parquet(resolve_path(args.case_master))
    outcomes = pd.read_parquet(resolve_path(args.outcomes))
    assignments = pd.read_csv(resolve_path(args.mode_assignments))
    merged = assignments.merge(
        case_master[["filegroup_id", "detail_url", "download_status", "pdf_available_flag", "excel_available_flag"]],
        on="filegroup_id",
        how="left",
    ).merge(outcomes, on="filegroup_id", how="left")
    merged["safety_severity_score"] = build_safety_score(merged)
    pairs = select_pairs(merged, target_count=12)

    out_path = resolve_path(args.out)
    codebook_path = resolve_path(args.out_codebook)
    log_path = resolve_path(args.log)
    write_casebook(pairs, merged, out_path)
    pd.DataFrame(CODEBOOK_ROWS).to_csv(codebook_path, index=False)
    write_log(
        log_path,
        [
            f"generated_at={utc_now_iso()}",
            f"casebook_md={out_path}",
            f"codebook_csv={codebook_path}",
            f"pair_count={len(pairs)}",
        ],
    )


if __name__ == "__main__":
    main()
