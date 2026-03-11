from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.core.signals.preprocess_known_signal_families import ensure_preprocessing_schema, resolve_repo_path
from scripts.tools.analytics.build_signal_feature_batch import CHANNEL_ORDER


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = REPO_ROOT / "output" / "small_overlap" / "ml"
DEFAULT_SOURCE_MODE = "standard_baseline"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export fixed-length harmonized signal tensor for ML workflows.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def load_cases(connection: sqlite3.Connection, source_mode: str, limit: int | None) -> list[sqlite3.Row]:
    rows = connection.execute(
        """
        SELECT pc.preprocessing_case_id,
               pc.filegroup_id,
               fg.test_code,
               v.vehicle_year,
               v.vehicle_make_model,
               pc.parser_version,
               pc.harmonized_wide_path,
               pc.manifest_path
          FROM preprocessing_cases pc
          JOIN filegroups fg
            ON fg.filegroup_id = pc.filegroup_id
          JOIN vehicles v
            ON v.vehicle_id = fg.vehicle_id
         WHERE pc.mode = ?
           AND pc.status = 'done'
           AND pc.harmonized_wide_path IS NOT NULL
         ORDER BY pc.filegroup_id
        """,
        (source_mode,),
    ).fetchall()
    return rows[:limit]


def absolute_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def load_tensor(rows: list[sqlite3.Row]) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    if not rows:
        raise ValueError("No harmonized cases available for ML dataset export.")

    frames = [pd.read_parquet(absolute_path(row["harmonized_wide_path"])) for row in rows]
    reference_time = pd.to_numeric(frames[0]["time_s"], errors="coerce").to_numpy(dtype=float)
    sample_count = reference_time.size
    tensor = np.zeros((len(rows), len(CHANNEL_ORDER), sample_count), dtype=np.float32)
    mask = np.zeros((len(rows), len(CHANNEL_ORDER), sample_count), dtype=np.uint8)
    metadata: list[dict[str, Any]] = []

    for case_index, (row, frame) in enumerate(zip(rows, frames, strict=True)):
        case_time = pd.to_numeric(frame["time_s"], errors="coerce").to_numpy(dtype=float)
        if case_time.size != sample_count or not np.allclose(case_time, reference_time, atol=1e-9, equal_nan=True):
            raise ValueError(f"Harmonized time grid mismatch for filegroup_id={row['filegroup_id']}")
        metadata.append(
            {
                "preprocessing_case_id": int(row["preprocessing_case_id"]),
                "filegroup_id": int(row["filegroup_id"]),
                "test_code": row["test_code"],
                "vehicle_year": int(row["vehicle_year"]) if row["vehicle_year"] is not None else None,
                "vehicle_make_model": row["vehicle_make_model"],
                "parser_version": row["parser_version"],
                "harmonized_wide_path": row["harmonized_wide_path"],
                "manifest_path": row["manifest_path"],
            }
        )
        for channel_index, channel_name in enumerate(CHANNEL_ORDER):
            if channel_name in frame.columns:
                values = pd.to_numeric(frame[channel_name], errors="coerce").to_numpy(dtype=float)
            else:
                values = np.full(sample_count, np.nan, dtype=float)
            finite_mask = np.isfinite(values)
            tensor[case_index, channel_index, :] = np.where(finite_mask, values, 0.0).astype(np.float32)
            mask[case_index, channel_index, :] = finite_mask.astype(np.uint8)
    return reference_time.astype(np.float32), tensor, mask, metadata


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_dir = resolve_repo_path(args.output_dir) if args.output_dir else OUTPUT_ROOT
    output_dir.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        ensure_preprocessing_schema(connection)
        rows = load_cases(connection, source_mode=args.source_mode, limit=args.limit)
        time_s, tensor, mask, metadata = load_tensor(rows)
    finally:
        connection.close()

    slug = args.source_mode.lower()
    dataset_npz = output_dir / f"signal_ml_dataset__{slug}.npz"
    metadata_csv = output_dir / f"signal_ml_dataset__{slug}__cases.csv"
    summary_json = output_dir / f"signal_ml_dataset__{slug}__summary.json"

    np.savez_compressed(
        dataset_npz,
        x=tensor,
        mask=mask,
        time_s=time_s,
        channel_names=np.array(CHANNEL_ORDER, dtype=object),
        filegroup_ids=np.array([item["filegroup_id"] for item in metadata], dtype=np.int32),
        preprocessing_case_ids=np.array([item["preprocessing_case_id"] for item in metadata], dtype=np.int32),
    )
    pd.DataFrame(metadata).to_csv(metadata_csv, index=False)
    summary_json.write_text(
        json.dumps(
            {
                "source_mode": args.source_mode,
                "case_count": len(metadata),
                "channel_count": len(CHANNEL_ORDER),
                "sample_count": int(time_s.size),
                "tensor_shape": list(tensor.shape),
                "mask_shape": list(mask.shape),
                "outputs": {
                    "dataset_npz": str(dataset_npz.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "metadata_csv": str(metadata_csv.relative_to(REPO_ROOT)).replace("\\", "/"),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "case_count": len(metadata),
                "tensor_shape": list(tensor.shape),
                "outputs": {
                    "dataset_npz": str(dataset_npz.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "metadata_csv": str(metadata_csv.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "summary_json": str(summary_json.relative_to(REPO_ROOT)).replace("\\", "/"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
