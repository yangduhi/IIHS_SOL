from __future__ import annotations

import argparse
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from momentfm import MOMENTPipeline

from scripts.tools.analytics import build_signal_feature_batch as feature_batch


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = REPO_ROOT / "output" / "small_overlap" / "tables"
PARSER_VERSION = "signal-feature-batch:moment_v1"
DEFAULT_SOURCE_MODE = "standard_baseline"
DEFAULT_FEATURE_SPACE = "official_known_harmonized_moment_v1"
NEIGHBOR_ALGORITHM = "moment_hybrid_similarity_v1"
CLUSTER_ALGORITHM = "kmedoids_moment_v1"
REPRESENTATIVE_ALGORITHM = CLUSTER_ALGORITHM
MODEL_NAME = "AutonLab/MOMENT-1-small"
MODEL_GLOBAL_WEIGHT = 0.55
MODEL_VIEW_WEIGHTS = {"pulse": 0.20, "occupant": 0.13, "lower_extremity": 0.12}
PHYSICS_WEIGHT = 0.10
PCA_COMPONENTS = {"global": 128, "pulse": 48, "occupant": 32, "lower_extremity": 48}
CLUSTER_K_RANGE = (4, 12)
MOMENT_VIEW_CHANNELS = {
    "pulse": (
        "vehicle_longitudinal_accel_g",
        "vehicle_lateral_accel_g",
        "vehicle_vertical_accel_g",
        "vehicle_resultant_accel_g",
    ),
    "occupant": ("seat_mid_deflection_mm", "seat_inner_deflection_mm"),
    "lower_extremity": (
        "foot_left_x_accel_g",
        "foot_left_z_accel_g",
        "foot_right_x_accel_g",
        "foot_right_z_accel_g",
    ),
}


@dataclass
class MomentCaseFeature:
    case: feature_batch.CaseRow
    signal_bank: dict[str, np.ndarray]
    feature_values: list[dict[str, Any]]
    vector_map: dict[str, float]
    coverage_map: dict[str, float]
    moment_embeddings: dict[str, np.ndarray]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build MOMENT-based signal similarity, clustering, and representatives.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE)
    parser.add_argument("--feature-space", default=DEFAULT_FEATURE_SPACE)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--candidate-k", type=int, default=36)
    parser.add_argument("--dtw-step", type=int, default=10)
    parser.add_argument("--dtw-window", type=int, default=16)
    parser.add_argument("--min-clusters", type=int, default=CLUSTER_K_RANGE[0])
    parser.add_argument("--max-clusters", type=int, default=CLUSTER_K_RANGE[1])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = max(float(np.linalg.norm(a) * np.linalg.norm(b)), 1e-9)
    return float(np.dot(a, b) / denom)


def cosine_distance_matrix(matrix: np.ndarray) -> np.ndarray:
    normalized = matrix / np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-9)
    cosine = normalized @ normalized.T
    return np.sqrt(np.maximum(2.0 - 2.0 * cosine, 0.0))


def pca_project(matrix: np.ndarray, components: int) -> tuple[np.ndarray, np.ndarray]:
    centered = matrix - np.mean(matrix, axis=0, keepdims=True)
    u, s, vt = np.linalg.svd(centered, full_matrices=False)
    k = max(1, min(components, vt.shape[0], centered.shape[0] - 1))
    projected = centered @ vt[:k].T
    return projected, vt[:k]


def normalize_embedding_matrix(matrix: np.ndarray) -> np.ndarray:
    centered = matrix - np.mean(matrix, axis=0, keepdims=True)
    scaled = centered / (np.std(centered, axis=0, keepdims=True) + 1e-6)
    return scaled / np.maximum(np.linalg.norm(scaled, axis=1, keepdims=True), 1e-9)


def load_scale_map(connection: sqlite3.Connection) -> dict[str, float]:
    rows = connection.execute(
        """
        SELECT fv.standard_name, fv.feature_value_number
          FROM preprocessing_feature_values fv
          JOIN preprocessing_feature_sets fs
            ON fs.preprocessing_feature_set_id = fv.preprocessing_feature_set_id
         WHERE fs.source_mode = 'standard_baseline'
           AND fs.feature_space = 'official_known_harmonized_v3'
           AND fv.feature_name = 'peak_abs'
        """
    ).fetchall()
    scale_map: dict[str, float] = {}
    for channel_name in feature_batch.CHANNEL_ORDER:
        values = [float(row["feature_value_number"]) for row in rows if row["standard_name"] == channel_name and row["feature_value_number"] is not None]
        scale_map[channel_name] = float(np.percentile(values, 95)) if values else 1.0
    return scale_map


def resample_channel(time_s: np.ndarray, values: np.ndarray, target_time: np.ndarray) -> tuple[np.ndarray, bool]:
    finite = np.isfinite(values)
    if finite.sum() < 25:
        return np.zeros(target_time.shape, dtype=np.float32), False
    filled = np.interp(time_s, time_s[finite], values[finite]) if not finite.all() else values
    return np.interp(target_time, time_s, filled).astype(np.float32), True


def encode_case(
    case: feature_batch.CaseRow,
    model: MOMENTPipeline,
    scale_map: dict[str, float],
) -> MomentCaseFeature:
    dataframe = pd.read_parquet(case.harmonized_wide_path)
    time_s = pd.to_numeric(dataframe["time_s"], errors="coerce").to_numpy(dtype=float)
    target_time = np.linspace(float(time_s[0]), float(time_s[-1]), model.config.seq_len)
    signal_bank: dict[str, np.ndarray] = {}
    model_inputs: list[np.ndarray] = []
    availability: list[bool] = []
    coverage_map: dict[str, float] = {}

    for channel_name in feature_batch.CHANNEL_ORDER:
        if channel_name in dataframe.columns:
            values = pd.to_numeric(dataframe[channel_name], errors="coerce").to_numpy(dtype=float)
        else:
            values = np.full(time_s.shape, np.nan, dtype=float)
        signal_bank[channel_name] = values
        coverage_map[channel_name] = float(np.isfinite(values).sum() / values.size) if values.size else 0.0
        resampled, available = resample_channel(time_s, values, target_time)
        model_inputs.append((resampled / max(scale_map.get(channel_name, 1.0), 1e-6)).astype(np.float32))
        availability.append(available)

    x_enc = torch.tensor(np.stack(model_inputs)[None, :, :], dtype=torch.float32)
    input_mask = torch.ones((1, model.config.seq_len), dtype=torch.float32)
    with torch.no_grad():
        outputs = model.embed(x_enc=x_enc, input_mask=input_mask, reduction="none")
    channel_embeddings = outputs.embeddings[0].mean(dim=1).cpu().numpy()
    channel_embeddings[np.logical_not(np.array(availability, dtype=bool))] = 0.0

    moment_embeddings: dict[str, np.ndarray] = {}
    moment_embeddings["global"] = channel_embeddings.reshape(-1)
    for view_name, channel_names in MOMENT_VIEW_CHANNELS.items():
        indices = [feature_batch.CHANNEL_ORDER.index(channel_name) for channel_name in channel_names]
        available_indices = [index for index in indices if availability[index]]
        if available_indices:
            moment_embeddings[view_name] = channel_embeddings[available_indices].mean(axis=0)
        else:
            moment_embeddings[view_name] = np.zeros(channel_embeddings.shape[-1], dtype=np.float32)

    return MomentCaseFeature(
        case=case,
        signal_bank=signal_bank,
        feature_values=[],
        vector_map={},
        coverage_map=coverage_map,
        moment_embeddings=moment_embeddings,
    )


def attach_projected_vectors(case_features: list[MomentCaseFeature]) -> dict[str, np.ndarray]:
    payload: dict[str, np.ndarray] = {}
    for name, components in PCA_COMPONENTS.items():
        matrix = np.stack([case_feature.moment_embeddings[name] for case_feature in case_features])
        projected, _ = pca_project(matrix, components)
        normalized = normalize_embedding_matrix(projected)
        payload[name] = normalized
        for row_index, case_feature in enumerate(case_features):
            for col_index, value in enumerate(normalized[row_index]):
                feature_name = f"{name}_pc_{col_index:03d}"
                case_feature.vector_map[f"moment::{feature_name}"] = float(value)
                case_feature.feature_values.append(
                    {
                        "standard_name": "moment",
                        "feature_name": feature_name,
                        "feature_value_number": float(value),
                        "feature_unit": "",
                    }
                )
    for case_feature in case_features:
        for view_name, channel_names in MOMENT_VIEW_CHANNELS.items():
            available = [case_feature.coverage_map[channel_name] >= 0.05 for channel_name in channel_names]
            feature_name = f"{view_name}_availability_ratio"
            value = float(sum(available) / len(available))
            case_feature.vector_map[f"moment::{feature_name}"] = value
            case_feature.feature_values.append(
                {
                    "standard_name": "moment",
                    "feature_name": feature_name,
                    "feature_value_number": value,
                    "feature_unit": "",
                }
            )
            case_feature.coverage_map[f"moment_{view_name}"] = value
    return payload


def choose_clusters(
    embedding_payload: dict[str, np.ndarray],
    min_clusters: int,
    max_clusters: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    global_distance = cosine_distance_matrix(embedding_payload["global"])
    distance_matrix = (
        MODEL_GLOBAL_WEIGHT * global_distance
        + MODEL_VIEW_WEIGHTS["pulse"] * cosine_distance_matrix(embedding_payload["pulse"])
        + MODEL_VIEW_WEIGHTS["occupant"] * cosine_distance_matrix(embedding_payload["occupant"])
        + MODEL_VIEW_WEIGHTS["lower_extremity"] * cosine_distance_matrix(embedding_payload["lower_extremity"])
    )
    best_payload: tuple[np.ndarray, np.ndarray, float, int, float] | None = None
    candidates: list[dict[str, Any]] = []
    for k in range(min_clusters, max_clusters + 1):
        labels, medoids, total_cost = feature_batch.fit_kmedoids(distance_matrix, k, seed + k)
        score = feature_batch.silhouette_score(distance_matrix, labels)
        cluster_sizes = np.bincount(labels, minlength=k)
        candidates.append({"k": k, "silhouette_score": score, "min_cluster_size": int(cluster_sizes.min()), "max_cluster_size": int(cluster_sizes.max())})
        if best_payload is None or score > best_payload[2]:
            best_payload = (labels, medoids, score, k, total_cost)
    assert best_payload is not None
    labels, medoids, score, selected_k, total_cost = best_payload
    return labels, medoids, distance_matrix, {"selected_k": selected_k, "silhouette_score": score, "total_cost": total_cost, "candidates": candidates}


def physics_similarity(source: MomentCaseFeature, target: MomentCaseFeature, dtw_step: int, dtw_window: int) -> tuple[float, float, float]:
    weighted_correlation, _ = feature_batch.weighted_signal_correlation(source, target)
    signal_rmse, _ = feature_batch.weighted_signal_rmse(source, target)
    dtw_distance = feature_batch.approximate_dtw_distance(source, target, step=dtw_step, window=dtw_window)
    parts: list[tuple[float, float]] = []
    if math.isfinite(weighted_correlation):
        parts.append((((weighted_correlation + 1.0) / 2.0), 0.50))
    if math.isfinite(signal_rmse):
        parts.append(((1.0 / (1.0 + signal_rmse)), 0.30))
    if math.isfinite(dtw_distance):
        parts.append(((1.0 / (1.0 + dtw_distance)), 0.20))
    if not parts:
        return float("nan"), weighted_correlation, dtw_distance
    score = sum(value * weight for value, weight in parts) / sum(weight for _, weight in parts)
    return score, weighted_correlation, dtw_distance


def build_neighbor_rows(
    case_features: list[MomentCaseFeature],
    embedding_payload: dict[str, np.ndarray],
    top_k: int,
    candidate_k: int,
    dtw_step: int,
    dtw_window: int,
) -> list[dict[str, Any]]:
    global_cos = embedding_payload["global"] @ embedding_payload["global"].T
    pulse_cos = embedding_payload["pulse"] @ embedding_payload["pulse"].T
    occupant_cos = embedding_payload["occupant"] @ embedding_payload["occupant"].T
    lower_cos = embedding_payload["lower_extremity"] @ embedding_payload["lower_extremity"].T
    neighbor_rows: list[dict[str, Any]] = []

    for row_index, source_feature in enumerate(case_features):
        candidate_indices = np.argsort(-global_cos[row_index])[: candidate_k + 1]
        payloads: list[dict[str, Any]] = []
        for candidate_index in candidate_indices:
            candidate_index = int(candidate_index)
            if candidate_index == row_index:
                continue
            overlap_count, union_count = feature_batch.availability_stats(source_feature, case_features[candidate_index])
            overlap_ratio = feature_batch.safe_ratio(float(overlap_count), float(union_count)) if union_count else 0.0
            view_score = (
                MODEL_VIEW_WEIGHTS["pulse"] * ((float(pulse_cos[row_index, candidate_index]) + 1.0) / 2.0)
                + MODEL_VIEW_WEIGHTS["occupant"] * ((float(occupant_cos[row_index, candidate_index]) + 1.0) / 2.0)
                + MODEL_VIEW_WEIGHTS["lower_extremity"] * ((float(lower_cos[row_index, candidate_index]) + 1.0) / 2.0)
            ) / sum(MODEL_VIEW_WEIGHTS.values())
            physics_score, weighted_correlation, dtw_distance = physics_similarity(
                source_feature,
                case_features[candidate_index],
                dtw_step=dtw_step,
                dtw_window=dtw_window,
            )
            components = [(((float(global_cos[row_index, candidate_index]) + 1.0) / 2.0), MODEL_GLOBAL_WEIGHT), (view_score, sum(MODEL_VIEW_WEIGHTS.values()))]
            if math.isfinite(physics_score):
                components.append((physics_score, PHYSICS_WEIGHT))
            similarity_score = sum(value * weight for value, weight in components) / sum(weight for _, weight in components)
            similarity_score *= 0.90 + (0.10 * overlap_ratio)
            payloads.append(
                {
                    "source_preprocessing_case_id": source_feature.case.preprocessing_case_id,
                    "target_preprocessing_case_id": case_features[candidate_index].case.preprocessing_case_id,
                    "similarity_score": similarity_score,
                    "distance_score": 1.0 - similarity_score,
                    "weighted_correlation": weighted_correlation,
                    "dtw_distance": dtw_distance,
                    "overlap_channel_count": overlap_count,
                    "multiview_score": view_score,
                    "pulse_view_score": (float(pulse_cos[row_index, candidate_index]) + 1.0) / 2.0,
                    "occupant_view_score": (float(occupant_cos[row_index, candidate_index]) + 1.0) / 2.0,
                    "lower_extremity_view_score": (float(lower_cos[row_index, candidate_index]) + 1.0) / 2.0,
                    "pulse_phase_score": physics_score,
                    "occupant_phase_score": float("nan"),
                    "lower_extremity_phase_score": float("nan"),
                }
            )
        payloads.sort(key=lambda item: item["similarity_score"], reverse=True)
        for rank, payload in enumerate(payloads[:top_k], start=1):
            payload["rank"] = rank
            neighbor_rows.append(payload)
    return neighbor_rows


def main() -> None:
    args = parse_args()
    db_path = feature_batch.resolve_repo_path(args.db)
    output_dir = feature_batch.resolve_repo_path(args.output_dir) if args.output_dir else OUTPUT_ROOT

    feature_batch.PARSER_VERSION = PARSER_VERSION
    feature_batch.NEIGHBOR_ALGORITHM = NEIGHBOR_ALGORITHM
    feature_batch.CLUSTER_ALGORITHM = CLUSTER_ALGORITHM
    feature_batch.REPRESENTATIVE_ALGORITHM = REPRESENTATIVE_ALGORITHM

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        feature_batch.ensure_preprocessing_schema(connection)
        scale_map = load_scale_map(connection)
        cases = feature_batch.load_cases(connection, source_mode=args.source_mode, limit=args.limit)
        model = MOMENTPipeline.from_pretrained(MODEL_NAME, model_kwargs={"task_name": "embedding"})
        model.eval()
        case_features = [encode_case(case, model=model, scale_map=scale_map) for case in cases]
        embedding_payload = attach_projected_vectors(case_features)
        labels, medoids, cluster_distance_matrix, cluster_summary = choose_clusters(
            embedding_payload=embedding_payload,
            min_clusters=args.min_clusters,
            max_clusters=args.max_clusters,
            seed=args.seed,
        )
        cluster_rows, representative_rows, outliers = feature_batch.build_cluster_rows(
            case_features=case_features,
            cluster_distance_matrix=cluster_distance_matrix,
            labels=labels,
            medoid_indices=medoids,
        )
        neighbor_rows = build_neighbor_rows(
            case_features=case_features,
            embedding_payload=embedding_payload,
            top_k=args.top_k,
            candidate_k=args.candidate_k,
            dtw_step=args.dtw_step,
            dtw_window=args.dtw_window,
        )

        preprocessing_feature_run_id = feature_batch.create_feature_run(connection, args.source_mode, args.feature_space)
        feature_set_ids = feature_batch.replace_feature_sets(
            connection=connection,
            preprocessing_feature_run_id=preprocessing_feature_run_id,
            source_mode=args.source_mode,
            feature_space=args.feature_space,
            case_features=case_features,
        )
        feature_batch.persist_neighbor_rows(connection, preprocessing_feature_run_id, args.feature_space, feature_set_ids, neighbor_rows)
        feature_batch.persist_cluster_rows(connection, preprocessing_feature_run_id, args.feature_space, feature_set_ids, cluster_rows, representative_rows)
        reports = feature_batch.write_reports(
            output_dir=output_dir,
            source_mode=args.source_mode,
            feature_space=args.feature_space,
            case_features=case_features,
            neighbor_rows=neighbor_rows,
            cluster_rows=cluster_rows,
            representative_rows=representative_rows,
            cluster_summary=cluster_summary,
            outliers=outliers,
        )
        feature_batch.finish_feature_run(
            connection,
            preprocessing_feature_run_id,
            {
                "model_name": MODEL_NAME,
                "parser_version": PARSER_VERSION,
                "feature_space": args.feature_space,
                "case_count": len(case_features),
                "neighbor_count": len(neighbor_rows),
                "cluster_count": cluster_summary.get("selected_k"),
                "silhouette_score": cluster_summary.get("silhouette_score"),
                "outlier_count": len(outliers),
                "reports": reports,
                "fusion_weights": {
                    "global_embedding": MODEL_GLOBAL_WEIGHT,
                    "view_embeddings": MODEL_VIEW_WEIGHTS,
                    "physics_residual": PHYSICS_WEIGHT,
                },
                "pca_components": PCA_COMPONENTS,
            },
        )
    finally:
        connection.close()

    print(
        feature_batch.json.dumps(
            {
                "feature_space": args.feature_space,
                "case_count": len(case_features),
                "neighbor_count": len(neighbor_rows),
                "cluster_count": cluster_summary.get("selected_k"),
                "silhouette_score": cluster_summary.get("silhouette_score"),
                "outlier_count": len(outliers),
                "reports": reports,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
