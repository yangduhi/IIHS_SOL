from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


WINDOW_FEATURE_SUFFIXES = (
    "delta_vx_mps",
    "delta_vy_away_mps",
    "lr",
    "ly",
    "ri",
    "max_abs_ax_g",
    "max_abs_ay_g",
    "max_abs_az_g",
    "max_abs_resultant_g",
    "pulse_duration_x_ms",
    "pulse_duration_y_ms",
    "pulse_duration_z_ms",
    "seat_twist_peak_mm",
    "foot_resultant_left_g",
    "foot_resultant_right_g",
    "foot_resultant_asymmetry_g",
    "foot_x_left_right_diff_g",
    "foot_z_left_right_diff_g",
)


def window_feature_columns(window_ms: int) -> list[str]:
    prefix = f"window_{int(window_ms):03d}_"
    return [f"{prefix}{suffix}" for suffix in WINDOW_FEATURE_SUFFIXES]


def prepare_window_frame(features: pd.DataFrame, window_ms: int) -> tuple[pd.DataFrame, list[str]]:
    columns = window_feature_columns(window_ms)
    eligible = features.loc[features["cluster_input_flag"].eq(1)].copy()
    if eligible.empty:
        return eligible, columns
    numeric = eligible[columns].apply(pd.to_numeric, errors="coerce")
    row_coverage = numeric.notna().mean(axis=1)
    eligible = eligible.loc[row_coverage >= 0.65].copy()
    numeric = numeric.loc[eligible.index].copy()
    for column in columns:
        series = numeric[column]
        fill_value = float(series.median()) if series.notna().any() else 0.0
        eligible[column] = series.fillna(fill_value)
    return eligible, columns


@dataclass(frozen=True)
class ClusterRun:
    dataframe: pd.DataFrame
    feature_columns: list[str]
    matrix: np.ndarray
    scaled_matrix: np.ndarray
    labels: np.ndarray
    silhouette: float
    inertia: float


def run_kmeans(features: pd.DataFrame, window_ms: int, k: int, random_state: int = 42) -> ClusterRun:
    eligible, columns = prepare_window_frame(features, window_ms)
    if eligible.empty or len(eligible) <= k:
        return ClusterRun(eligible, columns, np.empty((0, len(columns))), np.empty((0, len(columns))), np.array([], dtype=int), float("nan"), float("nan"))
    matrix = eligible[columns].to_numpy(dtype=float)
    scaled = StandardScaler().fit_transform(matrix)
    model = KMeans(n_clusters=k, random_state=random_state, n_init=20)
    labels = model.fit_predict(scaled)
    silhouette = float("nan")
    if len(np.unique(labels)) > 1 and len(labels) > k:
        silhouette = float(silhouette_score(scaled, labels))
    eligible = eligible.copy()
    eligible["cluster_id"] = labels.astype(int)
    return ClusterRun(eligible, columns, matrix, scaled, labels, silhouette, float(model.inertia_))


def cluster_summary(run: ClusterRun, k: int) -> dict[str, float | int]:
    if run.dataframe.empty:
        return {
            "k": k,
            "sample_count": 0,
            "silhouette": float("nan"),
            "inertia": float("nan"),
            "min_cluster_size": 0,
            "max_cluster_size": 0,
            "size_ratio": float("nan"),
        }
    counts = run.dataframe["cluster_id"].value_counts().sort_index()
    min_size = int(counts.min())
    max_size = int(counts.max())
    size_ratio = (max_size / min_size) if min_size else float("inf")
    return {
        "k": k,
        "sample_count": int(len(run.dataframe)),
        "silhouette": run.silhouette,
        "inertia": run.inertia,
        "min_cluster_size": min_size,
        "max_cluster_size": max_size,
        "size_ratio": float(size_ratio) if math.isfinite(size_ratio) else float("nan"),
    }


def centroid_distances(run: ClusterRun) -> pd.Series:
    if run.dataframe.empty:
        return pd.Series(dtype=float)
    frame = run.dataframe.copy()
    centroids = frame.groupby("cluster_id")[run.feature_columns].mean()
    distances: list[float] = []
    for row in frame.itertuples(index=False):
        centroid = centroids.loc[getattr(row, "cluster_id")].to_numpy(dtype=float)
        point = np.asarray([getattr(row, column) for column in run.feature_columns], dtype=float)
        distances.append(float(np.linalg.norm(point - centroid)))
    return pd.Series(distances, index=frame.index, dtype=float)
