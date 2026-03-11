from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from momentfm import MOMENTPipeline
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import silhouette_score
from sklearn.neighbors import LocalOutlierFactor

from scripts.tools.analytics.build_signal_feature_batch import (
    ANALYSIS_WINDOW_END_S,
    ANALYSIS_WINDOW_START_S,
    CHANNEL_ORDER,
    CHANNEL_WEIGHTS,
    CaseRow,
    banded_dtw_distance,
    compute_channel_features,
    compute_cross_channel_lag_features,
    crop_frame_to_analysis_window,
    json_clean,
    load_cases,
    sanitize_slug,
    unit_for_feature,
)
from scripts.core.signals.preprocess_known_signal_families import ensure_preprocessing_schema, resolve_repo_path


REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = REPO_ROOT / "output" / "small_overlap" / "tables"
DEFAULT_DB = REPO_ROOT / "data" / "research" / "research.sqlite"
DEFAULT_SOURCE_MODE = "standard_baseline"
DEFAULT_FEATURE_SPACE = "official_known_harmonized_v5"
PARSER_VERSION = "signal-feature-batch:moment-v2-window015"
NEIGHBOR_ALGORITHM = "moment_hybrid_similarity_v2_window015"
CLUSTER_ALGORITHM = "kmeans_moment_embedding_v2_window015"
REPRESENTATIVE_ALGORITHM = CLUSTER_ALGORITHM
MOMENT_MODEL = "AutonLab/MOMENT-1-small"
MOMENT_SEQ_LEN = 512
SELECTED_CHANNEL_FEATURES = (
    "coverage_ratio",
    "peak_abs",
    "peak_abs_time_s",
    "onset_time_abs",
    "rebound_time_s",
    "settle_time_abs",
    "area_abs",
    "energy_proxy",
)
VIEW_SPECS = {
    "global": {"indices": tuple(range(len(CHANNEL_ORDER))), "n_components": 24, "weight": 0.10},
    "pulse": {"indices": (0, 1, 2, 3), "n_components": 32, "weight": 0.55},
    "occupant": {"indices": (4, 5), "n_components": 12, "weight": 0.05},
    "lower_extremity": {"indices": (6, 7, 8, 9), "n_components": 24, "weight": 0.30},
}
PULSE_PHASE_FEATURES = ("onset_time_abs", "peak_abs_time_s", "rebound_time_s", "settle_time_abs")
PULSE_PHASE_SCALES = {"onset_time_abs": 0.015, "peak_abs_time_s": 0.02, "rebound_time_s": 0.03, "settle_time_abs": 0.04}
LAG_SIMILARITY_SCALE = 0.025


@dataclass
class MomentCaseFeature:
    case: CaseRow
    time_s: np.ndarray
    signal_bank: dict[str, np.ndarray]
    resampled: np.ndarray
    channel_features: dict[str, dict[str, float]]
    lag_features: dict[str, float]
    coverage_map: dict[str, float]
    feature_values: list[dict[str, Any]]
    vector_map: dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build MOMENT-based signal neighbors/clusters for harmonized IIHS signals.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--source-mode", default=DEFAULT_SOURCE_MODE)
    parser.add_argument("--feature-space", default=DEFAULT_FEATURE_SPACE)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--candidate-k", type=int, default=80)
    parser.add_argument("--min-clusters", type=int, default=3)
    parser.add_argument("--max-clusters", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--outlier-contamination", type=float, default=0.04)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def infer_case_slug(case: CaseRow) -> str:
    return f"{case.filegroup_id}-{case.test_code}"


def build_feature_row(standard_name: str, feature_name: str, value: float) -> dict[str, Any]:
    unit = "embedding" if standard_name.startswith("moment_") else unit_for_feature(standard_name, feature_name)
    return {
        "standard_name": standard_name,
        "feature_name": feature_name,
        "feature_value_number": value,
        "feature_unit": unit,
    }


def resample_signal(values: np.ndarray, target_length: int = MOMENT_SEQ_LEN) -> np.ndarray:
    src_x = np.linspace(0.0, 1.0, values.size, dtype=np.float32)
    dst_x = np.linspace(0.0, 1.0, target_length, dtype=np.float32)
    finite = np.isfinite(values)
    if finite.sum() < 2:
        return np.zeros(target_length, dtype=np.float32)
    source = values.astype(np.float32)
    if not finite.all():
        source = np.interp(src_x, src_x[finite], source[finite]).astype(np.float32)
    return np.interp(dst_x, src_x, source).astype(np.float32)


def load_case_feature(case: CaseRow) -> MomentCaseFeature:
    dataframe = pd.read_parquet(case.harmonized_wide_path)
    dataframe = crop_frame_to_analysis_window(dataframe)
    time_s = pd.to_numeric(dataframe["time_s"], errors="coerce").to_numpy(dtype=float)
    signal_bank: dict[str, np.ndarray] = {}
    resampled_rows: list[np.ndarray] = []
    channel_features: dict[str, dict[str, float]] = {}
    coverage_map: dict[str, float] = {}
    feature_values: list[dict[str, Any]] = []
    vector_map: dict[str, float] = {}

    for channel_name in CHANNEL_ORDER:
        if channel_name in dataframe.columns:
            values = pd.to_numeric(dataframe[channel_name], errors="coerce").to_numpy(dtype=float)
        else:
            values = np.full(time_s.shape, np.nan, dtype=float)
        signal_bank[channel_name] = values
        resampled_rows.append(resample_signal(values))
        features = compute_channel_features(time_s, values)
        channel_features[channel_name] = features
        coverage_map[channel_name] = float(features.get("coverage_ratio", 0.0))
        for feature_name in SELECTED_CHANNEL_FEATURES:
            value = float(features.get(feature_name, float("nan")))
            if math.isfinite(value):
                feature_values.append(build_feature_row(channel_name, feature_name, value))

    lag_features = compute_cross_channel_lag_features(channel_features)
    for feature_name, value in lag_features.items():
        if math.isfinite(value):
            feature_values.append(build_feature_row("cross_channel_lag", feature_name, float(value)))

    return MomentCaseFeature(
        case=case,
        time_s=time_s,
        signal_bank=signal_bank,
        resampled=np.stack(resampled_rows, axis=0),
        channel_features=channel_features,
        lag_features=lag_features,
        coverage_map=coverage_map,
        feature_values=feature_values,
        vector_map=vector_map,
    )


def cosine_similarity_matrix(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    normalized = matrix / np.maximum(norms, 1e-8)
    return normalized @ normalized.T


def compute_moment_views(case_features: list[MomentCaseFeature], batch_size: int, seed: int) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, Any]]:
    stacked = np.stack([case_feature.resampled for case_feature in case_features], axis=0)
    model = MOMENTPipeline.from_pretrained(MOMENT_MODEL, model_kwargs={"task_name": "embedding"})
    model.init()
    model.eval()

    outputs: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, stacked.shape[0], batch_size):
            batch = torch.tensor(stacked[start : start + batch_size], dtype=torch.float32)
            result = model(x_enc=batch, reduction="none")
            outputs.append(result.embeddings.cpu().numpy())
    embeddings = np.concatenate(outputs, axis=0)

    reduced_views: dict[str, np.ndarray] = {}
    summary: dict[str, Any] = {"model_name": MOMENT_MODEL, "seq_len": MOMENT_SEQ_LEN, "views": {}}
    for view_name, spec in VIEW_SPECS.items():
        flat = embeddings[:, spec["indices"], :, :].reshape(embeddings.shape[0], -1)
        reducer = TruncatedSVD(n_components=spec["n_components"], random_state=seed)
        reduced = reducer.fit_transform(flat)
        reduced_views[view_name] = reduced.astype(np.float32)
        summary["views"][view_name] = {
            "components": int(spec["n_components"]),
            "weight": float(spec["weight"]),
            "explained_variance_ratio": float(np.sum(reducer.explained_variance_ratio_)),
        }
    final_embedding = np.concatenate(
        [math.sqrt(float(VIEW_SPECS[view_name]["weight"])) * reduced_views[view_name] for view_name in VIEW_SPECS],
        axis=1,
    )
    return reduced_views, final_embedding.astype(np.float32), summary


def weighted_waveform_correlation(source: MomentCaseFeature, target: MomentCaseFeature) -> float:
    weighted_sum = 0.0
    weight_total = 0.0
    for channel_name in CHANNEL_ORDER:
        x = source.resampled[CHANNEL_ORDER.index(channel_name)]
        y = target.resampled[CHANNEL_ORDER.index(channel_name)]
        if np.std(x) < 1e-6 or np.std(y) < 1e-6:
            continue
        corr = float(np.corrcoef(x, y)[0, 1])
        weight = CHANNEL_WEIGHTS.get(channel_name, 1.0)
        weighted_sum += weight * ((corr + 1.0) / 2.0)
        weight_total += weight
    return weighted_sum / max(weight_total, 1e-8)


def pulse_phase_similarity(source: MomentCaseFeature, target: MomentCaseFeature) -> float:
    scores: list[float] = []
    source_pulse = source.channel_features.get("vehicle_longitudinal_accel_g", {})
    target_pulse = target.channel_features.get("vehicle_longitudinal_accel_g", {})
    for feature_name in PULSE_PHASE_FEATURES:
        x = float(source_pulse.get(feature_name, float("nan")))
        y = float(target_pulse.get(feature_name, float("nan")))
        if math.isfinite(x) and math.isfinite(y):
            diff = abs(x - y)
            scores.append(math.exp(-diff / PULSE_PHASE_SCALES[feature_name]))
    for feature_name, x in source.lag_features.items():
        y = float(target.lag_features.get(feature_name, float("nan")))
        if math.isfinite(x) and math.isfinite(y):
            scores.append(math.exp(-abs(float(x) - y) / LAG_SIMILARITY_SCALE))
    if not scores:
        return float("nan")
    return float(sum(scores) / len(scores))


def longitudinal_dtw(source: MomentCaseFeature, target: MomentCaseFeature) -> float:
    source_values = source.resampled[0][::4]
    target_values = target.resampled[0][::4]
    source_values = source_values - float(np.mean(source_values))
    target_values = target_values - float(np.mean(target_values))
    source_std = float(np.std(source_values))
    target_std = float(np.std(target_values))
    if source_std > 1e-6:
        source_values = source_values / source_std
    if target_std > 1e-6:
        target_values = target_values / target_std
    return banded_dtw_distance(source_values, target_values, window=18)


def build_neighbor_rows(
    case_features: list[MomentCaseFeature],
    view_vectors: dict[str, np.ndarray],
    top_k: int,
    candidate_k: int,
) -> list[dict[str, Any]]:
    score_matrices = {view_name: cosine_similarity_matrix(matrix) for view_name, matrix in view_vectors.items()}
    moment_score = sum(float(VIEW_SPECS[view_name]["weight"]) * score_matrices[view_name] for view_name in VIEW_SPECS)
    neighbor_rows: list[dict[str, Any]] = []
    for row_index, source_feature in enumerate(case_features):
        order = np.argsort(-moment_score[row_index])
        candidates = [int(index) for index in order if int(index) != row_index][:candidate_k]
        payloads: list[dict[str, Any]] = []
        for candidate_index in candidates:
            target_feature = case_features[candidate_index]
            waveform_corr = weighted_waveform_correlation(source_feature, target_feature)
            phase_score = pulse_phase_similarity(source_feature, target_feature)
            dtw_distance = longitudinal_dtw(source_feature, target_feature)
            final_score = 0.82 * float(moment_score[row_index, candidate_index]) + 0.10 * waveform_corr
            if math.isfinite(phase_score):
                final_score += 0.08 * phase_score
            payloads.append(
                {
                    "source_preprocessing_case_id": source_feature.case.preprocessing_case_id,
                    "target_preprocessing_case_id": target_feature.case.preprocessing_case_id,
                    "similarity_score": final_score,
                    "distance_score": 1.0 - final_score,
                    "weighted_correlation": waveform_corr,
                    "dtw_distance": dtw_distance,
                    "overlap_channel_count": sum(int(source_feature.coverage_map[name] > 0 and target_feature.coverage_map[name] > 0) for name in CHANNEL_ORDER),
                    "multiview_score": float(
                        0.55 * score_matrices["pulse"][row_index, candidate_index]
                        + 0.05 * score_matrices["occupant"][row_index, candidate_index]
                        + 0.30 * score_matrices["lower_extremity"][row_index, candidate_index]
                    ),
                    "pulse_view_score": float(score_matrices["pulse"][row_index, candidate_index]),
                    "occupant_view_score": float(score_matrices["occupant"][row_index, candidate_index]),
                    "lower_extremity_view_score": float(score_matrices["lower_extremity"][row_index, candidate_index]),
                    "pulse_phase_score": phase_score,
                    "occupant_phase_score": float("nan"),
                    "lower_extremity_phase_score": float("nan"),
                }
            )
        payloads.sort(key=lambda item: item["similarity_score"], reverse=True)
        for rank, row in enumerate(payloads[:top_k], start=1):
            row["rank"] = rank
            neighbor_rows.append(row)
    return neighbor_rows


def choose_clusters(embedding_matrix: np.ndarray, min_clusters: int, max_clusters: int, seed: int) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    centered = embedding_matrix - embedding_matrix.mean(axis=0, keepdims=True)
    scale = embedding_matrix.std(axis=0, keepdims=True)
    standardized = centered / np.maximum(scale, 1e-6)
    best_payload: tuple[float, int, np.ndarray, np.ndarray] | None = None
    candidates: list[dict[str, Any]] = []
    min_cluster_size = max(8, int(math.ceil(embedding_matrix.shape[0] * 0.02)))
    for k in range(min_clusters, max_clusters + 1):
        model = KMeans(n_clusters=k, n_init=20, random_state=seed)
        labels = model.fit_predict(standardized)
        sizes = np.bincount(labels, minlength=k)
        score = float(silhouette_score(standardized, labels))
        valid = bool(sizes.min() >= min_cluster_size)
        candidates.append({"k": k, "silhouette_score": score, "min_cluster_size": int(sizes.min()), "max_cluster_size": int(sizes.max()), "valid": valid})
        if valid and (best_payload is None or score > best_payload[0]):
            best_payload = (score, k, labels.astype(int), model.cluster_centers_.astype(np.float32))
    if best_payload is None:
        model = KMeans(n_clusters=min_clusters, n_init=20, random_state=seed)
        labels = model.fit_predict(standardized)
        best_payload = (float(silhouette_score(standardized, labels)), min_clusters, labels.astype(int), model.cluster_centers_.astype(np.float32))
    best_score, best_k, labels, centers = best_payload
    return standardized.astype(np.float32), labels, {"selected_k": int(best_k), "silhouette_score": best_score, "candidates": candidates, "cluster_centers": centers}


def build_cluster_rows(
    case_features: list[MomentCaseFeature],
    standardized_embedding: np.ndarray,
    labels: np.ndarray,
    cluster_centers: np.ndarray,
    contamination: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    lof = LocalOutlierFactor(n_neighbors=min(20, max(5, standardized_embedding.shape[0] // 20)), contamination=contamination)
    outlier_flags = lof.fit_predict(standardized_embedding)
    local_density = -lof.negative_outlier_factor_
    distances = np.linalg.norm(standardized_embedding - cluster_centers[labels], axis=1)
    coverage_scores = np.array([float(np.mean(list(case_feature.coverage_map.values()))) for case_feature in case_features], dtype=float)
    cluster_rows: list[dict[str, Any]] = []
    representative_rows: list[dict[str, Any]] = []
    outliers: list[dict[str, Any]] = []

    for cluster_label in np.unique(labels):
        member_indices = np.flatnonzero(labels == cluster_label)
        member_distances = distances[member_indices]
        median_distance = float(np.median(member_distances))
        mad = float(np.median(np.abs(member_distances - median_distance)) * 1.4826)
        scale = max(mad, 1e-6)
        centroid_order = member_indices[np.argsort(member_distances)]
        boundary_order = member_indices[np.argsort(member_distances)[::-1]]
        stable_order = member_indices[np.argsort(local_density[member_indices])]
        coverage_order = member_indices[np.argsort(-coverage_scores[member_indices])]
        for representative_kind, ordered in (
            ("cluster_centroid", centroid_order[:3]),
            ("cluster_boundary", boundary_order[:3]),
            ("cluster_stable", stable_order[:3]),
            ("cluster_high_coverage", coverage_order[:3]),
        ):
            for rank, member_index in enumerate(ordered, start=1):
                score = float(distances[int(member_index)]) if representative_kind != "cluster_high_coverage" else float(coverage_scores[int(member_index)])
                representative_rows.append(
                    {
                        "preprocessing_case_id": case_features[int(member_index)].case.preprocessing_case_id,
                        "cluster_label": int(cluster_label),
                        "representative_kind": representative_kind,
                        "rank": rank,
                        "score": score,
                    }
                )
        for member_index in member_indices:
            robust_distance_score = float((distances[int(member_index)] - median_distance) / scale)
            local_density_score = float(local_density[int(member_index)])
            is_outlier = int(outlier_flags[int(member_index)] == -1 or robust_distance_score >= 3.5)
            outlier_score = max(robust_distance_score, max(0.0, (local_density_score - 1.0) * 4.0))
            row = {
                "preprocessing_case_id": case_features[int(member_index)].case.preprocessing_case_id,
                "cluster_label": int(cluster_label),
                "centroid_distance": float(distances[int(member_index)]),
                "outlier_score": outlier_score,
                "robust_distance_score": robust_distance_score,
                "local_density_outlier_score": local_density_score,
                "stability_score": float(1.0 / max(local_density_score, 1e-6)),
                "coverage_score": float(coverage_scores[int(member_index)]),
                "is_outlier": is_outlier,
            }
            cluster_rows.append(row)
            if is_outlier:
                outliers.append({"filegroup_id": case_features[int(member_index)].case.filegroup_id, "vehicle_make_model": case_features[int(member_index)].case.vehicle_make_model, "cluster_label": int(cluster_label), "outlier_score": outlier_score})

    global_center = standardized_embedding.mean(axis=0)
    global_distances = np.linalg.norm(standardized_embedding - global_center, axis=1)
    for rank, member_index in enumerate(np.argsort(global_distances)[:10], start=1):
        representative_rows.append(
            {
                "preprocessing_case_id": case_features[int(member_index)].case.preprocessing_case_id,
                "cluster_label": None,
                "representative_kind": "global_centroid",
                "rank": rank,
                "score": float(global_distances[int(member_index)]),
            }
        )
    return cluster_rows, representative_rows, outliers


def create_feature_run(connection: sqlite3.Connection, source_mode: str, feature_space: str, notes: dict[str, Any]) -> int:
    cursor = connection.execute(
        """
        INSERT INTO preprocessing_feature_runs (
          started_at, parser_version, source_mode, feature_space, notes
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (utc_now_iso(), PARSER_VERSION, source_mode, feature_space, json.dumps(json_clean(notes), ensure_ascii=False)),
    )
    connection.commit()
    return int(cursor.lastrowid)


def finish_feature_run(connection: sqlite3.Connection, preprocessing_feature_run_id: int, notes: dict[str, Any]) -> None:
    connection.execute(
        "UPDATE preprocessing_feature_runs SET finished_at = ?, notes = ? WHERE preprocessing_feature_run_id = ?",
        (utc_now_iso(), json.dumps(json_clean(notes), ensure_ascii=False), preprocessing_feature_run_id),
    )
    connection.commit()


def replace_feature_sets(
    connection: sqlite3.Connection,
    preprocessing_feature_run_id: int,
    source_mode: str,
    feature_space: str,
    case_features: list[MomentCaseFeature],
) -> dict[int, int]:
    connection.execute("PRAGMA foreign_keys = ON")
    case_ids = [case_feature.case.preprocessing_case_id for case_feature in case_features]
    placeholders = ",".join("?" for _ in case_ids)
    params = [source_mode, feature_space, *case_ids]
    for table_name, column_name in (
        ("preprocessing_neighbors", "source_feature_set_id"),
        ("preprocessing_clusters", "preprocessing_feature_set_id"),
        ("preprocessing_representatives", "preprocessing_feature_set_id"),
        ("preprocessing_feature_values", "preprocessing_feature_set_id"),
    ):
        connection.execute(
            f"""
            DELETE FROM {table_name}
             WHERE {column_name} IN (
                    SELECT preprocessing_feature_set_id
                      FROM preprocessing_feature_sets
                     WHERE source_mode = ?
                       AND feature_space = ?
                       AND preprocessing_case_id IN ({placeholders})
                  )
            """,
            params,
        )
    connection.execute(
        f"""
        DELETE FROM preprocessing_feature_sets
         WHERE source_mode = ?
           AND feature_space = ?
           AND preprocessing_case_id IN ({placeholders})
        """,
        params,
    )
    connection.commit()

    now = utc_now_iso()
    feature_set_ids: dict[int, int] = {}
    for case_feature in case_features:
        cursor = connection.execute(
            """
            INSERT INTO preprocessing_feature_sets (
              preprocessing_feature_run_id, preprocessing_case_id, filegroup_id, source_mode, feature_space,
              status, feature_count, vector_json, coverage_json, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preprocessing_feature_run_id,
                case_feature.case.preprocessing_case_id,
                case_feature.case.filegroup_id,
                source_mode,
                feature_space,
                "done",
                len(case_feature.feature_values),
                json.dumps(json_clean(case_feature.vector_map), ensure_ascii=False),
                json.dumps(json_clean(case_feature.coverage_map), ensure_ascii=False),
                json.dumps({"representation": "MOMENT hybrid"}, ensure_ascii=False),
                now,
                now,
            ),
        )
        feature_set_id = int(cursor.lastrowid)
        feature_set_ids[case_feature.case.preprocessing_case_id] = feature_set_id
        for feature_row in case_feature.feature_values:
            connection.execute(
                """
                INSERT INTO preprocessing_feature_values (
                  preprocessing_feature_set_id, standard_name, feature_name, feature_value_number, feature_unit
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    feature_set_id,
                    feature_row["standard_name"],
                    feature_row["feature_name"],
                    feature_row["feature_value_number"],
                    feature_row["feature_unit"],
                ),
            )
    connection.commit()
    return feature_set_ids


def persist_neighbor_rows(connection: sqlite3.Connection, preprocessing_feature_run_id: int, feature_space: str, feature_set_ids: dict[int, int], neighbor_rows: list[dict[str, Any]]) -> None:
    for row in neighbor_rows:
        connection.execute(
            """
            INSERT INTO preprocessing_neighbors (
              preprocessing_feature_run_id, source_feature_set_id, target_feature_set_id, feature_space, rank,
              similarity_score, distance_score, weighted_correlation, dtw_distance, overlap_channel_count,
              multiview_score, pulse_view_score, occupant_view_score, lower_extremity_view_score,
              pulse_phase_score, occupant_phase_score, lower_extremity_phase_score, algorithm
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preprocessing_feature_run_id,
                feature_set_ids[row["source_preprocessing_case_id"]],
                feature_set_ids[row["target_preprocessing_case_id"]],
                feature_space,
                row["rank"],
                row["similarity_score"],
                row["distance_score"],
                row["weighted_correlation"],
                row["dtw_distance"],
                row["overlap_channel_count"],
                row["multiview_score"],
                row["pulse_view_score"],
                row["occupant_view_score"],
                row["lower_extremity_view_score"],
                row["pulse_phase_score"],
                row["occupant_phase_score"],
                row["lower_extremity_phase_score"],
                NEIGHBOR_ALGORITHM,
            ),
        )
    connection.commit()


def persist_cluster_rows(connection: sqlite3.Connection, preprocessing_feature_run_id: int, feature_space: str, feature_set_ids: dict[int, int], cluster_rows: list[dict[str, Any]], representative_rows: list[dict[str, Any]]) -> None:
    for row in cluster_rows:
        connection.execute(
            """
            INSERT INTO preprocessing_clusters (
              preprocessing_feature_run_id, preprocessing_feature_set_id, feature_space, algorithm,
              cluster_label, centroid_distance, outlier_score, robust_distance_score,
              local_density_outlier_score, stability_score, coverage_score, is_outlier
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preprocessing_feature_run_id,
                feature_set_ids[row["preprocessing_case_id"]],
                feature_space,
                CLUSTER_ALGORITHM,
                row["cluster_label"],
                row["centroid_distance"],
                row["outlier_score"],
                row["robust_distance_score"],
                row["local_density_outlier_score"],
                row["stability_score"],
                row["coverage_score"],
                row["is_outlier"],
            ),
        )
    for row in representative_rows:
        connection.execute(
            """
            INSERT INTO preprocessing_representatives (
              preprocessing_feature_run_id, preprocessing_feature_set_id, feature_space, algorithm,
              representative_kind, cluster_label, rank, score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preprocessing_feature_run_id,
                feature_set_ids[row["preprocessing_case_id"]],
                feature_space,
                REPRESENTATIVE_ALGORITHM,
                row["representative_kind"],
                row["cluster_label"],
                row["rank"],
                row["score"],
            ),
        )
    connection.commit()


def write_reports(output_dir: Path, source_mode: str, feature_space: str, case_features: list[MomentCaseFeature], neighbor_rows: list[dict[str, Any]], cluster_rows: list[dict[str, Any]], representative_rows: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = f"{sanitize_slug(source_mode)}__{sanitize_slug(feature_space)}"
    case_lookup = {case_feature.case.preprocessing_case_id: case_feature.case for case_feature in case_features}
    neighbors_csv = output_dir / f"signal_feature_neighbors__{slug}.csv"
    clusters_csv = output_dir / f"signal_feature_clusters__{slug}.csv"
    representatives_csv = output_dir / f"signal_feature_representatives__{slug}.csv"
    summary_json = output_dir / f"signal_feature_summary__{slug}.json"

    pd.DataFrame(
        [
            {
                "source_filegroup_id": case_lookup[row["source_preprocessing_case_id"]].filegroup_id,
                "source_vehicle": case_lookup[row["source_preprocessing_case_id"]].vehicle_make_model,
                "target_filegroup_id": case_lookup[row["target_preprocessing_case_id"]].filegroup_id,
                "target_vehicle": case_lookup[row["target_preprocessing_case_id"]].vehicle_make_model,
                "target_test_code": case_lookup[row["target_preprocessing_case_id"]].test_code,
                "rank": row["rank"],
                "similarity_score": row["similarity_score"],
                "weighted_correlation": row["weighted_correlation"],
                "multiview_score": row["multiview_score"],
                "pulse_view_score": row["pulse_view_score"],
                "pulse_phase_score": row["pulse_phase_score"],
            }
            for row in neighbor_rows
        ]
    ).to_csv(neighbors_csv, index=False)
    pd.DataFrame(
        [
            {
                "filegroup_id": case_lookup[row["preprocessing_case_id"]].filegroup_id,
                "vehicle": case_lookup[row["preprocessing_case_id"]].vehicle_make_model,
                "test_code": case_lookup[row["preprocessing_case_id"]].test_code,
                "cluster_label": row["cluster_label"],
                "centroid_distance": row["centroid_distance"],
                "outlier_score": row["outlier_score"],
                "local_density_outlier_score": row["local_density_outlier_score"],
                "stability_score": row["stability_score"],
                "coverage_score": row["coverage_score"],
                "is_outlier": row["is_outlier"],
            }
            for row in cluster_rows
        ]
    ).to_csv(clusters_csv, index=False)
    pd.DataFrame(
        [
            {
                "filegroup_id": case_lookup[row["preprocessing_case_id"]].filegroup_id,
                "vehicle": case_lookup[row["preprocessing_case_id"]].vehicle_make_model,
                "test_code": case_lookup[row["preprocessing_case_id"]].test_code,
                "cluster_label": row["cluster_label"],
                "representative_kind": row["representative_kind"],
                "rank": row["rank"],
                "score": row["score"],
            }
            for row in representative_rows
        ]
    ).to_csv(representatives_csv, index=False)
    summary_json.write_text(json.dumps(json_clean(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "neighbors_csv": str(neighbors_csv.relative_to(REPO_ROOT)).replace("\\", "/"),
        "clusters_csv": str(clusters_csv.relative_to(REPO_ROOT)).replace("\\", "/"),
        "representatives_csv": str(representatives_csv.relative_to(REPO_ROOT)).replace("\\", "/"),
        "summary_json": str(summary_json.relative_to(REPO_ROOT)).replace("\\", "/"),
    }


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    output_dir = resolve_repo_path(args.output_dir) if args.output_dir else OUTPUT_ROOT
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        ensure_preprocessing_schema(connection)
        cases = load_cases(connection, source_mode=args.source_mode, limit=args.limit)
        case_features = [load_case_feature(case) for case in cases]
        view_vectors, final_embedding, moment_summary = compute_moment_views(case_features, batch_size=args.batch_size, seed=args.seed)
        for row_index, case_feature in enumerate(case_features):
            for view_name, matrix in view_vectors.items():
                for component_index, value in enumerate(matrix[row_index], start=1):
                    feature_name = f"{view_name}_component_{component_index:03d}"
                    case_feature.vector_map[feature_name] = float(value)
                    case_feature.feature_values.append(build_feature_row("moment_embedding", feature_name, float(value)))
        neighbor_rows = build_neighbor_rows(case_features, view_vectors=view_vectors, top_k=args.top_k, candidate_k=args.candidate_k)
        standardized_embedding, labels, cluster_summary = choose_clusters(final_embedding, args.min_clusters, args.max_clusters, args.seed)
        cluster_rows, representative_rows, outliers = build_cluster_rows(case_features, standardized_embedding, labels, cluster_summary["cluster_centers"], args.outlier_contamination)
        notes = {
            "parser_version": PARSER_VERSION,
            "source_mode": args.source_mode,
            "feature_space": args.feature_space,
            "analysis_window_s": [ANALYSIS_WINDOW_START_S, ANALYSIS_WINDOW_END_S],
            "case_count": len(case_features),
            "neighbor_count": len(neighbor_rows),
            "cluster_count": cluster_summary["selected_k"],
            "silhouette_score": cluster_summary["silhouette_score"],
            "outlier_count": len(outliers),
            "moment": moment_summary,
        }
        preprocessing_feature_run_id = create_feature_run(connection, args.source_mode, args.feature_space, notes)
        feature_set_ids = replace_feature_sets(connection, preprocessing_feature_run_id, args.source_mode, args.feature_space, case_features)
        persist_neighbor_rows(connection, preprocessing_feature_run_id, args.feature_space, feature_set_ids, neighbor_rows)
        persist_cluster_rows(connection, preprocessing_feature_run_id, args.feature_space, feature_set_ids, cluster_rows, representative_rows)
        reports = write_reports(output_dir, args.source_mode, args.feature_space, case_features, neighbor_rows, cluster_rows, representative_rows, {**notes, "outliers": outliers})
        finish_feature_run(connection, preprocessing_feature_run_id, {**notes, "reports": reports, "cluster_candidates": cluster_summary["candidates"], "outliers": outliers})
    finally:
        connection.close()

    print(json.dumps({**notes, "reports": reports}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
