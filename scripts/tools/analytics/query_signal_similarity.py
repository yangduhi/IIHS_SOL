from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from scripts.core.signals.preprocess_known_signal_families import resolve_repo_path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FEATURE_SPACE = "official_known_harmonized_v5"
DEFAULT_SOURCE_MODE = "standard_baseline"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query top similar signal cases from preprocessing neighbor tables.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--filegroup-id", type=int, required=True)
    parser.add_argument("--feature-space", default=DEFAULT_FEATURE_SPACE)
    parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE)
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def load_neighbors(
    connection: sqlite3.Connection,
    filegroup_id: int,
    source_mode: str,
    feature_space: str,
    top_k: int,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT src.filegroup_id AS source_filegroup_id,
               fg1.test_code AS source_test_code,
               v1.vehicle_year AS source_year,
               v1.vehicle_make_model AS source_vehicle,
               tgt.filegroup_id AS target_filegroup_id,
               fg2.test_code AS target_test_code,
               v2.vehicle_year AS target_year,
               v2.vehicle_make_model AS target_vehicle,
               n.rank,
               n.similarity_score,
               n.distance_score,
               n.weighted_correlation,
               n.dtw_distance,
               n.overlap_channel_count,
               n.multiview_score,
               n.pulse_view_score,
               n.occupant_view_score,
               n.lower_extremity_view_score,
               n.pulse_phase_score,
               n.occupant_phase_score,
               n.lower_extremity_phase_score,
               n.algorithm
          FROM preprocessing_neighbors n
          JOIN preprocessing_feature_sets sfs
            ON sfs.preprocessing_feature_set_id = n.source_feature_set_id
          JOIN preprocessing_feature_sets tfs
            ON tfs.preprocessing_feature_set_id = n.target_feature_set_id
          JOIN preprocessing_cases src
            ON src.preprocessing_case_id = sfs.preprocessing_case_id
          JOIN preprocessing_cases tgt
            ON tgt.preprocessing_case_id = tfs.preprocessing_case_id
          JOIN filegroups fg1
            ON fg1.filegroup_id = src.filegroup_id
          JOIN filegroups fg2
            ON fg2.filegroup_id = tgt.filegroup_id
          JOIN vehicles v1
            ON v1.vehicle_id = fg1.vehicle_id
          JOIN vehicles v2
            ON v2.vehicle_id = fg2.vehicle_id
         WHERE src.filegroup_id = ?
           AND sfs.source_mode = ?
           AND sfs.feature_space = ?
         ORDER BY n.rank
         LIMIT ?
        """,
        (filegroup_id, source_mode, feature_space, top_k),
    ).fetchall()


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = load_neighbors(
            connection=connection,
            filegroup_id=args.filegroup_id,
            source_mode=args.source_mode,
            feature_space=args.feature_space,
            top_k=args.top_k,
        )
        if not rows:
            raise SystemExit(
                f"No neighbor rows found for filegroup_id={args.filegroup_id}, "
                f"source_mode={args.source_mode}, feature_space={args.feature_space}."
            )
        print(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
