from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from nptdms import TdmsFile


PARSER_VERSION = "signal-parquet:v1"
DEFAULT_TYPES = ("tdms", "csv")
REPO_ROOT = Path(__file__).resolve().parents[3]
PARQUET_ROOT = REPO_ROOT / "data/derived/small_overlap/signal_parquet"
SUMMARY_CSV = REPO_ROOT / "output/small_overlap/tables/signal_parquet_run_summary.csv"
MANIFEST_CSV = REPO_ROOT / "output/small_overlap/tables/signal_parquet_manifest.csv"


class EmptySignalFileError(Exception):
    pass


class InvalidSignalArtifactError(Exception):
    pass


@dataclass
class SignalJob:
    signal_container_id: int
    asset_id: int
    filegroup_id: int
    test_code: str
    container_type: str
    filename: str
    local_path: str
    extraction_status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export supported signal containers to Parquet and register signal_series rows.")
    parser.add_argument("--db", default="data/research/research.sqlite")
    parser.add_argument("--signal-container-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--all", action="store_true", help="Process all supported signal containers instead of only pending/error rows.")
    parser.add_argument(
        "--include-done",
        action="store_true",
        help="Include already-done signal containers when --all is used.",
    )
    parser.add_argument(
        "--types",
        default=",".join(DEFAULT_TYPES),
        help="Comma-separated container types to process. Default: tdms,csv",
    )
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def looks_like_html_artifact(path: Path) -> bool:
    try:
        snippet = path.read_bytes()[:4096].decode("utf-8", errors="ignore").lower()
    except OSError:
        return False
    markers = ("<!doctype html", "<html", "you are not logged in", "<title>\r\n\tiihs techdata", "<title>\n\tiihs techdata", "<title>iihs techdata")
    return any(marker in snippet for marker in markers)


def slugify(value: str) -> str:
    text = normalize_text(value).replace("/", " ").replace("\\", " ")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.strip("_")


def unique_name(base: str, used: dict[str, int]) -> str:
    candidate = base or "unnamed"
    count = used.get(candidate, 0)
    used[candidate] = count + 1
    if count == 0:
        return candidate
    return f"{candidate}_{count + 1}"


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = normalize_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    if text.endswith("%"):
        text = text[:-1]
    text = re.sub(r"[^0-9.\-+eE]", "", text)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_percentish(value: Any) -> float | None:
    text = normalize_text(value)
    if not text:
        return None
    if text.endswith("%"):
        number = parse_float(text[:-1])
        return None if number is None else number / 100.0
    return parse_float(text)


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")


def supported_types(text: str) -> tuple[str, ...]:
    return tuple(sorted({chunk.strip() for chunk in text.split(",") if chunk.strip()}))


def load_jobs(connection: sqlite3.Connection, args: argparse.Namespace, types: tuple[str, ...]) -> list[SignalJob]:
    placeholders = ",".join("?" for _ in types)
    query = f"""
        SELECT sc.signal_container_id,
               sc.asset_id,
               sc.filegroup_id,
               fg.test_code,
               sc.container_type,
               a.filename,
               a.local_path,
               sc.extraction_status
          FROM signal_containers sc
          JOIN assets a ON a.asset_id = sc.asset_id
          JOIN filegroups fg ON fg.filegroup_id = sc.filegroup_id
         WHERE sc.container_type IN ({placeholders})
    """
    params: list[Any] = list(types)
    if args.signal_container_id:
        query += " AND sc.signal_container_id = ?"
        params.append(args.signal_container_id)
    elif not args.all:
        query += " AND sc.extraction_status IN ('pending', 'error')"
    elif not args.include_done:
        query += " AND sc.extraction_status <> 'done'"
    query += " ORDER BY sc.signal_container_id"
    if args.limit:
        query += " LIMIT ?"
        params.append(args.limit)
    rows = connection.execute(query, params).fetchall()
    return [SignalJob(**dict(row)) for row in rows]


def parse_tdms_column(raw_name: str) -> tuple[str, str]:
    match = re.match(r"/'(?P<group>.+)'/'(?P<channel>.+)'", raw_name)
    if match:
        return match.group("group"), match.group("channel")
    return "root", raw_name


def tdms_to_frame(path: Path) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    channel_meta: list[dict[str, Any]] = []
    with TdmsFile.open(path) as tdms:
        dataframe = tdms.as_dataframe(time_index=False)
        rename_map: dict[str, str] = {}
        used_names: dict[str, int] = {}
        for group in tdms.groups():
            for channel in group.channels():
                raw_name = f"/'{group.name}'/'{channel.name}'"
                clean_name = unique_name(slugify(f"{group.name}__{channel.name}"), used_names)
                rename_map[raw_name] = clean_name
                time_track = None
                try:
                    time_track = channel.time_track()
                except Exception:
                    time_track = None
                sample_rate = None
                wf_increment = channel.properties.get("wf_increment")
                if wf_increment:
                    try:
                        sample_rate = float(1.0 / float(wf_increment))
                    except Exception:
                        sample_rate = None
                elif time_track is not None and len(time_track) > 1:
                    delta = np.nanmedian(np.diff(time_track))
                    if delta and np.isfinite(delta):
                        sample_rate = float(1.0 / delta)
                channel_meta.append(
                    {
                        "raw_name": raw_name,
                        "clean_name": clean_name,
                        "group_name": group.name,
                        "channel_name": channel.name,
                        "unit": normalize_text(channel.properties.get("unit_string") or channel.properties.get("unit")),
                        "sample_rate_hz": sample_rate,
                        "time_start": float(time_track[0]) if time_track is not None and len(time_track) else None,
                        "time_end": float(time_track[-1]) if time_track is not None and len(time_track) else None,
                        "dtype": str(channel.data_type),
                        "properties": {key: channel.properties.get(key) for key in ("maximum", "minimum", "wf_increment")},
                    }
                )
        dataframe = dataframe.rename(columns=rename_map)
        return dataframe, channel_meta, {"group_count": len(tdms.groups()), "series_count": len(channel_meta)}


def csv_to_frame(path: Path) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, Any]]:
    dataframe = pd.read_csv(path)
    dataframe = dataframe.copy()
    if "Date" in dataframe.columns and "Time" in dataframe.columns:
        dataframe.insert(
            0,
            "timestamp",
            pd.to_datetime(dataframe["Date"].astype(str) + " " + dataframe["Time"].astype(str), errors="coerce"),
        )
    for column in list(dataframe.columns):
        if column == "Humidity":
            converted = dataframe[column].map(parse_percentish)
            if converted.notna().any():
                dataframe[column] = converted
            continue
        if dataframe[column].dtype == object:
            numeric = pd.to_numeric(dataframe[column], errors="coerce")
            if numeric.notna().sum() >= max(3, int(len(dataframe) * 0.75)):
                dataframe[column] = numeric
    channel_meta: list[dict[str, Any]] = []
    used_names: dict[str, int] = {}
    timestamps = dataframe["timestamp"] if "timestamp" in dataframe.columns else pd.Series(dtype="datetime64[ns]")
    sample_rate = None
    if timestamps.notna().sum() >= 2:
        deltas = timestamps.sort_values().diff().dropna().dt.total_seconds()
        if not deltas.empty:
            median_delta = float(deltas.median())
            if median_delta:
                sample_rate = 1.0 / median_delta
    for column in dataframe.columns:
        clean_name = unique_name(slugify(column), used_names)
        if not clean_name:
            continue
        dataframe = dataframe.rename(columns={column: clean_name})
        series = dataframe[clean_name]
        lower_clean_name = clean_name.lower()
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            if lower_clean_name in {"temperature_f", "temperature_f_"}:
                unit = "degF"
            elif "humidity" in lower_clean_name:
                unit = "ratio"
            elif lower_clean_name == "timestamp":
                unit = "datetime"
            else:
                unit = None
            channel_meta.append(
                {
                    "raw_name": column,
                    "clean_name": clean_name,
                    "group_name": "csv",
                    "channel_name": column,
                    "unit": unit,
                    "sample_rate_hz": sample_rate,
                    "time_start": None,
                    "time_end": None,
                    "dtype": str(series.dtype),
                    "properties": {},
                }
            )
    return dataframe, channel_meta, {"group_count": 1, "series_count": len(channel_meta)}


def existing_parquet_paths(connection: sqlite3.Connection, signal_container_id: int) -> list[Path]:
    rows = connection.execute(
        "SELECT DISTINCT parquet_path FROM signal_series WHERE signal_container_id = ? AND parquet_path IS NOT NULL",
        (signal_container_id,),
    ).fetchall()
    return [Path(row[0]) for row in rows if row[0]]


def delete_existing_state(connection: sqlite3.Connection, signal_container_id: int) -> None:
    for path in existing_parquet_paths(connection, signal_container_id):
        absolute = resolve_repo_path(str(path))
        if absolute.exists():
            absolute.unlink()
    connection.execute("DELETE FROM signal_series WHERE signal_container_id = ?", (signal_container_id,))


def stats_for_series(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna()
    stats: dict[str, Any] = {"non_null_count": int(non_null.shape[0]), "dtype": str(series.dtype)}
    if non_null.empty:
        return stats
    if pd.api.types.is_datetime64_any_dtype(series):
        stats["min"] = str(non_null.min())
        stats["max"] = str(non_null.max())
        return stats
    if pd.api.types.is_numeric_dtype(series):
        stats["min"] = float(non_null.min())
        stats["max"] = float(non_null.max())
        stats["mean"] = float(non_null.mean())
        stats["std"] = float(non_null.std()) if non_null.shape[0] > 1 else 0.0
        return stats
    stats["sample"] = normalize_text(non_null.iloc[0])
    return stats


def parquet_path_for(job: SignalJob) -> Path:
    safe_test = f"{job.filegroup_id}-{job.test_code}"
    safe_file = slugify(Path(job.filename).stem) or f"asset_{job.asset_id}"
    return PARQUET_ROOT / safe_test / f"{job.asset_id}-{safe_file}.parquet"


def insert_series_rows(
    connection: sqlite3.Connection,
    job: SignalJob,
    parquet_path: Path,
    dataframe: pd.DataFrame,
    channel_meta: list[dict[str, Any]],
) -> int:
    parquet_rel = repo_relative(parquet_path)
    rows = []
    meta_by_name = {row["clean_name"]: row for row in channel_meta}
    for column in dataframe.columns:
        if column not in meta_by_name:
            continue
        series = dataframe[column]
        meta = meta_by_name[column]
        if not (
            pd.api.types.is_numeric_dtype(series)
            or pd.api.types.is_datetime64_any_dtype(series)
        ):
            continue
        stats = stats_for_series(series)
        if meta["time_start"] is None and pd.api.types.is_datetime64_any_dtype(series) and series.dropna().shape[0]:
            meta["time_start"] = series.dropna().min().timestamp()
            meta["time_end"] = series.dropna().max().timestamp()
        rows.append(
            (
                job.signal_container_id,
                job.filegroup_id,
                column,
                meta["channel_name"],
                meta["unit"] or None,
                meta["sample_rate_hz"],
                int(len(series)),
                meta["time_start"],
                meta["time_end"],
                parquet_rel,
                json.dumps(
                    {
                        **stats,
                        "group_name": meta["group_name"],
                        "raw_name": meta["raw_name"],
                        "parser_version": PARSER_VERSION,
                    },
                    ensure_ascii=False,
                ),
            )
        )
    connection.executemany(
        """
        INSERT INTO signal_series (
          signal_container_id,
          filegroup_id,
          series_key,
          series_name,
          unit,
          sample_rate_hz,
          sample_count,
          time_start,
          time_end,
          parquet_path,
          stats_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def process_job(connection: sqlite3.Connection, job: SignalJob) -> dict[str, Any]:
    delete_existing_state(connection, job.signal_container_id)
    path = Path(job.local_path)
    try:
        if not path.exists():
            raise FileNotFoundError(path)
        if path.stat().st_size == 0:
            raise EmptySignalFileError("Source file is empty.")
        if looks_like_html_artifact(path):
            raise InvalidSignalArtifactError("Signal file contains login HTML instead of signal data.")
        if job.container_type == "tdms":
            dataframe, channel_meta, info = tdms_to_frame(path)
        elif job.container_type == "csv":
            dataframe, channel_meta, info = csv_to_frame(path)
        else:
            raise ValueError(f"Unsupported container type: {job.container_type}")
        parquet_path = parquet_path_for(job)
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_parquet(parquet_path, engine="pyarrow", index=False)
        series_count = insert_series_rows(connection, job, parquet_path, dataframe, channel_meta)
        sample_rate = next((row["sample_rate_hz"] for row in channel_meta if row.get("sample_rate_hz")), None)
        connection.execute(
            "UPDATE signal_containers SET parser_name = ?, extraction_status = ?, channel_count = ?, sample_rate_hz = ?, notes = ? WHERE signal_container_id = ?",
            (
                PARSER_VERSION,
                "done",
                series_count,
                sample_rate,
                json.dumps(
                    {
                        "parquet_path": repo_relative(parquet_path),
                        "group_count": info["group_count"],
                        "series_count": series_count,
                    },
                    ensure_ascii=False,
                ),
                job.signal_container_id,
            ),
        )
        return {
            "signal_container_id": job.signal_container_id,
            "filegroup_id": job.filegroup_id,
            "test_code": job.test_code,
            "container_type": job.container_type,
            "status": "done",
            "series_count": series_count,
            "parquet_path": repo_relative(parquet_path),
            "notes": "",
        }
    except (EmptySignalFileError, InvalidSignalArtifactError, pd.errors.EmptyDataError) as exc:
        connection.execute(
            "UPDATE signal_containers SET parser_name = ?, extraction_status = ?, channel_count = ?, sample_rate_hz = ?, notes = ? WHERE signal_container_id = ?",
            (PARSER_VERSION, "skipped", 0, None, f"{type(exc).__name__}: {exc}", job.signal_container_id),
        )
        return {
            "signal_container_id": job.signal_container_id,
            "filegroup_id": job.filegroup_id,
            "test_code": job.test_code,
            "container_type": job.container_type,
            "status": "skipped",
            "series_count": 0,
            "parquet_path": "",
            "notes": f"{type(exc).__name__}: {exc}",
        }
    except Exception as exc:
        connection.execute(
            "UPDATE signal_containers SET parser_name = ?, extraction_status = ?, notes = ? WHERE signal_container_id = ?",
            (PARSER_VERSION, "error", f"{type(exc).__name__}: {exc}", job.signal_container_id),
        )
        return {
            "signal_container_id": job.signal_container_id,
            "filegroup_id": job.filegroup_id,
            "test_code": job.test_code,
            "container_type": job.container_type,
            "status": "error",
            "series_count": 0,
            "parquet_path": "",
            "notes": f"{type(exc).__name__}: {exc}",
        }


def write_summaries(rows: list[dict[str, Any]]) -> None:
    dataframe = pd.DataFrame(rows)
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(SUMMARY_CSV, index=False)
    dataframe.to_csv(MANIFEST_CSV, index=False)


def main() -> None:
    args = parse_args()
    types = supported_types(args.types)
    connection = sqlite3.connect(resolve_repo_path(args.db))
    connection.row_factory = sqlite3.Row
    jobs = load_jobs(connection, args, types)
    results: list[dict[str, Any]] = []
    for job in jobs:
        results.append(process_job(connection, job))
        connection.commit()
    write_summaries(results)
    summary = {
        "processed": len(results),
        "done": sum(1 for row in results if row["status"] == "done"),
        "skipped": sum(1 for row in results if row["status"] == "skipped"),
        "error": sum(1 for row in results if row["status"] == "error"),
        "series_rows": sum(int(row["series_count"]) for row in results),
        "generated_at": utc_now_iso(),
        "parser_version": PARSER_VERSION,
        "types": list(types),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    connection.close()


if __name__ == "__main__":
    main()
