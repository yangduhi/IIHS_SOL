from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from nptdms import TdmsFile


REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_ROOT = REPO_ROOT / "data" / "derived" / "small_overlap" / "preprocessed_signals"
OUTPUT_ROOT = REPO_ROOT / "output" / "small_overlap" / "plots"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render quick-review plots for preprocessed IIHS signal data.")
    parser.add_argument("--filegroup-id", type=int, required=True)
    parser.add_argument("--test-code", default=None)
    parser.add_argument("--input-root", default=None)
    parser.add_argument("--output-root", default=None)
    return parser.parse_args()


def resolve_repo_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def find_case_root(input_root: Path, filegroup_id: int, test_code: str | None) -> Path:
    if test_code:
        candidate = input_root / f"{filegroup_id}-{test_code}"
        if candidate.exists():
            return candidate
    matches = sorted(input_root.glob(f"{filegroup_id}-*"))
    if not matches:
        raise FileNotFoundError(f"preprocessed case root not found for filegroup_id={filegroup_id}")
    return matches[0]


def load_case(case_root: Path) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    manifest = json.loads((case_root / "preprocessing_manifest.json").read_text(encoding="utf-8"))
    official = pd.read_parquet(case_root / "official_known_families_wide.parquet")
    t0_proxy = pd.read_parquet(case_root / "exploratory_vehicle_longitudinal_t0_proxy.parquet")
    return manifest, official, t0_proxy


def load_raw_longitudinal(manifest: dict[str, Any]) -> pd.DataFrame:
    tdms_path = Path(manifest["tdms_path"])
    raw_group = manifest["raw_group"]
    with TdmsFile.open(tdms_path) as tdms:
        channel = tdms[raw_group]["10VEHC0000__ACX_"]
        return pd.DataFrame(
            {
                "time_s": channel.time_track(),
                "raw_vehicle_longitudinal_accel_g": channel[:],
            }
        )


def setup_style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.facecolor": "#f7f4ec",
            "axes.facecolor": "#fffdf8",
            "savefig.facecolor": "#f7f4ec",
            "axes.edgecolor": "#5a5247",
            "axes.labelcolor": "#2d2a26",
            "xtick.color": "#2d2a26",
            "ytick.color": "#2d2a26",
            "text.color": "#2d2a26",
            "font.size": 11,
            "axes.titleweight": "bold",
        }
    )


def render_overview(manifest: dict[str, Any], official: pd.DataFrame, out_path: Path) -> None:
    time_s = official["time_s"]
    fig, axes = plt.subplots(3, 1, figsize=(15, 12), sharex=True)

    vehicle_cols = [
        ("vehicle_longitudinal_accel_g", "#b33c2e", "Longitudinal"),
        ("vehicle_lateral_accel_g", "#2660a4", "Lateral"),
        ("vehicle_vertical_accel_g", "#3b7a57", "Vertical"),
        ("vehicle_resultant_accel_g", "#6d597a", "Resultant"),
    ]
    for column, color, label in vehicle_cols:
        axes[0].plot(time_s, official[column], color=color, linewidth=1.8, label=label)
    axes[0].set_title("Vehicle Acceleration Channels")
    axes[0].set_ylabel("g")
    axes[0].legend(ncol=4, loc="upper right")

    seat_cols = [
        ("seat_mid_deflection_mm", "#c97c10", "Seat Mid"),
        ("seat_inner_deflection_mm", "#8d5a97", "Seat Inner"),
    ]
    for column, color, label in seat_cols:
        axes[1].plot(time_s, official[column], color=color, linewidth=2.0, label=label)
    axes[1].set_title("Seat Back Deflection")
    axes[1].set_ylabel("mm")
    axes[1].legend(loc="upper left")

    foot_cols = [
        ("foot_left_x_accel_g", "#0f7173", "Foot Left X"),
        ("foot_left_z_accel_g", "#6d9f71", "Foot Left Z"),
        ("foot_right_x_accel_g", "#c44536", "Foot Right X"),
        ("foot_right_z_accel_g", "#772e25", "Foot Right Z"),
    ]
    for column, color, label in foot_cols:
        axes[2].plot(time_s, official[column], color=color, linewidth=1.8, label=label)
    axes[2].set_title("Foot Acceleration Channels")
    axes[2].set_ylabel("g")
    axes[2].set_xlabel("Time (s)")
    axes[2].legend(ncol=2, loc="upper right")

    for axis in axes:
        axis.axvline(0.0, color="#444444", linestyle="--", linewidth=1.0, alpha=0.8)
        axis.axvspan(-0.05, -0.04, color="#f2cc8f", alpha=0.2)
    fig.suptitle(
        f"{manifest['test_code']} | {manifest['vehicle_make_model']} | Official Known Preprocessing Layer",
        fontsize=16,
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def render_longitudinal_detail(
    manifest: dict[str, Any],
    official: pd.DataFrame,
    raw_longitudinal: pd.DataFrame,
    t0_proxy: pd.DataFrame,
    out_path: Path,
) -> None:
    metrics = manifest["t0_proxy_assessment"]["metrics"]
    fig, axes = plt.subplots(2, 1, figsize=(15, 10), sharex=False)

    merged = raw_longitudinal.merge(
        official[["time_s", "vehicle_longitudinal_accel_g"]],
        on="time_s",
        how="inner",
    )
    zoom_mask = (merged["time_s"] >= -0.06) & (merged["time_s"] <= 0.10)
    zoom = merged.loc[zoom_mask]

    axes[0].plot(
        zoom["time_s"],
        zoom["raw_vehicle_longitudinal_accel_g"],
        color="#bcb8b1",
        linewidth=1.2,
        label="Raw ACX reference",
    )
    axes[0].plot(
        zoom["time_s"],
        zoom["vehicle_longitudinal_accel_g"],
        color="#b33c2e",
        linewidth=2.0,
        label="Official vehicle longitudinal",
    )
    axes[0].axvspan(-0.05, -0.04, color="#f2cc8f", alpha=0.25, label="Official zeroing window")
    axes[0].axvline(0.0, color="#444444", linestyle="--", linewidth=1.0, label="Official time zero")
    axes[0].axvline(metrics["t0_time_s"], color="#0f7173", linestyle=":", linewidth=1.5, label="T0 proxy")
    axes[0].set_xlim(-0.06, 0.10)
    axes[0].set_ylim(min(zoom["raw_vehicle_longitudinal_accel_g"].min(), zoom["vehicle_longitudinal_accel_g"].min()) - 3, 12)
    axes[0].set_title("Vehicle Longitudinal: Raw Reference vs Official")
    axes[0].set_ylabel("g")
    axes[0].legend(loc="lower left", ncol=2)

    zoom_t0 = t0_proxy[(t0_proxy["shifted_time_s"] >= -0.03) & (t0_proxy["shifted_time_s"] <= 0.10)]
    zoom_official = official[(official["time_s"] >= -0.03) & (official["time_s"] <= 0.10)]
    axes[1].plot(
        zoom_official["time_s"],
        zoom_official["vehicle_longitudinal_accel_g"],
        color="#b33c2e",
        linewidth=2.0,
        label="Official time basis",
    )
    axes[1].plot(
        zoom_t0["shifted_time_s"],
        zoom_t0["vehicle_longitudinal_accel_g_t0_proxy"],
        color="#0f7173",
        linewidth=2.0,
        label="Exploratory T0 proxy",
    )
    axes[1].axvline(0.0, color="#444444", linestyle="--", linewidth=1.0)
    axes[1].set_xlim(-0.03, 0.10)
    axes[1].set_title("Official Basis vs Exploratory T0 Proxy")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("g")
    axes[1].legend(loc="upper right")

    summary = "\n".join(
        [
            f"Detected bias: {metrics['detected_bias_g']:.3f} g",
            f"T0 proxy: {metrics['t0_time_s'] * 1000:.2f} ms",
            f"Anchor: {metrics['anchor_time_s'] * 1000:.2f} ms",
            f"T0 shift applied to official layer: no",
        ]
    )
    axes[1].text(
        0.015,
        0.97,
        summary,
        transform=axes[1].transAxes,
        va="top",
        ha="left",
        bbox={"facecolor": "#fff4d6", "edgecolor": "#c97c10", "boxstyle": "round,pad=0.4"},
    )

    fig.suptitle(f"{manifest['test_code']} | Longitudinal Detail Review", fontsize=16, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    input_root = resolve_repo_path(args.input_root, INPUT_ROOT)
    output_root = resolve_repo_path(args.output_root, OUTPUT_ROOT)
    case_root = find_case_root(input_root, args.filegroup_id, args.test_code)
    manifest, official, t0_proxy = load_case(case_root)
    raw_longitudinal = load_raw_longitudinal(manifest)
    setup_style()

    case_output_root = output_root / case_root.name
    case_output_root.mkdir(parents=True, exist_ok=True)
    overview_path = case_output_root / "01_official_overview.png"
    detail_path = case_output_root / "02_longitudinal_detail.png"

    render_overview(manifest, official, overview_path)
    render_longitudinal_detail(manifest, official, raw_longitudinal, t0_proxy, detail_path)

    print(
        json.dumps(
            {
                "overview_plot": str(overview_path),
                "detail_plot": str(detail_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
