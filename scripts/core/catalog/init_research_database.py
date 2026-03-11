from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize the unified IIHS research database from current metadata artifacts.")
    parser.add_argument("--manifest", default="data/index/manifest.sqlite")
    parser.add_argument("--analysis-dir", default="data/analysis")
    parser.add_argument("--schema", default="sql/research_database.sql")
    parser.add_argument("--output-db", default="data/research/research.sqlite")
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def detect_extension(filename: str) -> str:
    filename = filename.lower()
    dot = filename.rfind(".")
    if dot < 0:
        return "[no_ext]"
    return filename[dot:]


def classify_signal_container(extension: str) -> str | None:
    mapping = {
        ".tdms": "tdms",
        ".tdms_index": "tdms_index",
        ".tdm": "tdm",
        ".tdx": "tdx",
        ".dts": "dts",
        ".chn": "chn",
        ".bin": "bin",
        ".pi": "pi",
        ".tlf": "tlf",
        ".tlf pretest backup": "tlf_backup",
        ".dat": "dat",
        ".log": "log",
        ".csv": "csv",
    }
    return mapping.get(extension)


def classify_workbook_type(filename: str) -> str:
    lowered = filename.lower()
    if "intrusion" in lowered:
        return "intrusion"
    if "umtri" in lowered:
        return "umtri"
    if "summary" in lowered:
        return "summary"
    if "environment" in lowered:
        return "environment"
    return "generic_excel"


def create_database(connection: sqlite3.Connection, schema_path: Path) -> None:
    connection.executescript(schema_path.read_text(encoding="utf-8"))


def import_manifest(connection: sqlite3.Connection, manifest_path: Path) -> None:
    source = sqlite3.connect(manifest_path)
    source.row_factory = sqlite3.Row
    target = connection

    filegroups = [dict(row) for row in source.execute("SELECT * FROM filegroups ORDER BY filegroup_id")]
    folders = [dict(row) for row in source.execute("SELECT * FROM folders ORDER BY filegroup_id, folder_path")]
    files = [dict(row) for row in source.execute("SELECT * FROM files ORDER BY file_id")]

    test_types = {
        (row["test_type_code"], row["test_type_label"])
        for row in filegroups
    }
    target.executemany(
        "INSERT OR REPLACE INTO test_types (test_type_code, test_type_label) VALUES (?, ?)",
        sorted(test_types),
    )

    vehicles = sorted({
        (row["vehicle_year"], row["vehicle_make_model"])
        for row in filegroups
        if row["vehicle_make_model"]
    })
    target.executemany(
        "INSERT OR IGNORE INTO vehicles (vehicle_year, vehicle_make_model) VALUES (?, ?)",
        vehicles,
    )

    vehicle_lookup = {
        (row["vehicle_year"], row["vehicle_make_model"]): row["vehicle_id"]
        for row in target.execute("SELECT vehicle_id, vehicle_year, vehicle_make_model FROM vehicles")
    }

    target.executemany(
        """
        INSERT OR REPLACE INTO filegroups (
          filegroup_id, vehicle_id, test_type_code, test_code, title, tested_on, detail_url,
          discovered_at, last_seen_at, source, list_page, download_status, folder_count, file_count,
          downloaded_file_count, excluded_file_count, data_root, last_error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["filegroup_id"],
                vehicle_lookup.get((row["vehicle_year"], row["vehicle_make_model"])),
                row["test_type_code"],
                row["test_code"],
                row["title"],
                row["tested_on"],
                row["detail_url"],
                row["discovered_at"],
                row["last_seen_at"],
                row["source"],
                row["list_page"],
                row["download_status"],
                row["folder_count"],
                row["file_count"],
                row["downloaded_file_count"],
                row["excluded_file_count"],
                row["data_root"],
                row["last_error"],
            )
            for row in filegroups
        ],
    )

    target.executemany(
        """
        INSERT OR REPLACE INTO folders (filegroup_id, folder_path, status, excluded_reason)
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                row["filegroup_id"],
                row["folder_path"],
                row.get("status"),
                row.get("excluded_reason"),
            )
            for row in folders
        ],
    )

    target.executemany(
        """
        INSERT OR REPLACE INTO assets (
          asset_id, filegroup_id, folder_path, filename, relative_path, local_path, listed_on_page,
          modified_label, size_label, source_url, content_type, content_disposition, size_bytes, sha256,
          status, excluded_reason, downloaded_at, last_error, file_extension
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["file_id"],
                row["filegroup_id"],
                row["folder_path"],
                row["filename"],
                row["relative_path"],
                row["local_path"],
                row["listed_on_page"],
                row["modified_label"],
                row["size_label"],
                row["source_url"],
                row["content_type"],
                row["content_disposition"],
                row["size_bytes"],
                row["sha256"],
                row["status"],
                row["excluded_reason"],
                row["downloaded_at"],
                row["last_error"],
                detect_extension(row["filename"]),
            )
            for row in files
        ],
    )

    source.close()


def import_analysis_csvs(connection: sqlite3.Connection, analysis_dir: Path) -> None:
    tdas_rows = read_csv(analysis_dir / "tdas_configs.csv")
    equipment_rows = read_csv(analysis_dir / "equipment_racks.csv")
    dts_rows = read_csv(analysis_dir / "dts_files.csv")
    module_rows = read_csv(analysis_dir / "dts_modules.csv")
    sensor_rows = read_csv(analysis_dir / "sensor_channels.csv")

    connection.executemany(
        """
        INSERT OR REPLACE INTO tdas_configs (
          filegroup_id, tdas_ini_path, program_version, customer_name, firmware_versions,
          valid_sampling_rates, filter_cutoffs, com_port_config, rack_inventory, roi_window,
          default_data_collection_mode, export_to_ascii_options, diadem_header_auto_create,
          diadem_channel_name_mode, diadem_channel_comment_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["filegroup_id"],
                row["tdas_ini_path"],
                row["program_version"],
                row["customer_name"],
                row["firmware_versions"],
                row["valid_sampling_rates"],
                row["filter_cutoffs"],
                row["com_port_config"],
                row["rack_inventory"],
                row["roi_window"],
                row["default_data_collection_mode"],
                row["export_to_ascii_options"],
                row["diadem_header_auto_create"],
                row["diadem_channel_name_mode"],
                row["diadem_channel_comment_mode"],
            )
            for row in tdas_rows
        ],
    )

    connection.executemany(
        """
        INSERT OR REPLACE INTO equipment_racks (
          filegroup_id, equipment_ini_path, rack_id, connect_info
        ) VALUES (?, ?, ?, ?)
        """,
        [
            (
                row["filegroup_id"],
                row["equipment_ini_path"],
                row["rack_id"],
                row["connect_info"],
            )
            for row in equipment_rows
        ],
    )

    asset_lookup = {
        row["local_path"]: row["asset_id"]
        for row in connection.execute("SELECT asset_id, local_path FROM assets WHERE local_path IS NOT NULL")
    }

    dts_id_lookup: dict[tuple[str, str], int] = {}
    for row in dts_rows:
        cursor = connection.execute(
            """
            INSERT OR REPLACE INTO dts_files (
              filegroup_id, asset_id, dts_path, dts_test_id, dts_description,
              event_number, software, software_version, module_count, channel_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["filegroup_id"],
                asset_lookup.get(row["dts_path"]),
                row["dts_path"],
                row["dts_test_id"],
                row["dts_description"],
                row["event_number"],
                row["software"],
                row["software_version"],
                int(row["module_count"] or 0),
                int(row["channel_count"] or 0),
            ),
        )
        dts_file_id = cursor.lastrowid
        if not dts_file_id:
            existing = connection.execute(
                "SELECT dts_file_id FROM dts_files WHERE filegroup_id = ? AND dts_path = ?",
                (row["filegroup_id"], row["dts_path"]),
            ).fetchone()
            dts_file_id = existing[0]
        dts_id_lookup[(row["filegroup_id"], row["dts_path"])] = dts_file_id

    connection.executemany(
        """
        INSERT OR REPLACE INTO dts_modules (
          dts_file_id, filegroup_id, module_number, module_serial_number, module_base_serial_number,
          module_sample_rate_hz, module_pre_trigger_seconds, module_post_trigger_seconds,
          module_number_of_channels, module_recording_mode, module_aa_filter_rate_hz
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                dts_id_lookup[(row["filegroup_id"], row["dts_path"])],
                row["filegroup_id"],
                row["module_number"],
                row["module_serial_number"],
                row["module_base_serial_number"],
                row["module_sample_rate_hz"],
                row["module_pre_trigger_seconds"],
                row["module_post_trigger_seconds"],
                row["module_number_of_channels"],
                row["module_recording_mode"],
                row["module_aa_filter_rate_hz"],
            )
            for row in module_rows
        ],
    )

    connection.executemany(
        """
        INSERT OR REPLACE INTO sensor_channels (
          dts_file_id, filegroup_id, test_code, module_number, module_sample_rate_hz, module_recording_mode,
          channel_xml_type, channel_number, channel_id, hardware_channel_name, channel_group_name, channel_name2,
          channel_description_string, description, iso_code, iso_channel_name, eu, desired_range, sensitivity,
          sensitivity_units, sensor_capacity, sensor_polarity, serial_number, sensor_id, software_filter,
          excitation_voltage, measured_excitation_voltage, measured_shunt_deflection_mv, time_of_first_sample,
          zero_method, remove_offset, is_inverted, bridge, bridge_resistance_ohms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                dts_id_lookup.get((row["filegroup_id"], row["dts_path"])),
                row["filegroup_id"],
                row["test_code"],
                row["module_number"],
                row["module_sample_rate_hz"],
                row["module_recording_mode"],
                row["channel_xml_type"],
                row["channel_number"],
                row["channel_id"],
                row["hardware_channel_name"],
                row["channel_group_name"],
                row["channel_name2"],
                row["channel_description_string"],
                row["description"],
                row["iso_code"],
                row["iso_channel_name"],
                row["eu"],
                row["desired_range"],
                row["sensitivity"],
                row["sensitivity_units"],
                row["sensor_capacity"],
                row["sensor_polarity"],
                row["serial_number"],
                row["sensor_id"],
                row["software_filter"],
                row["excitation_voltage"],
                row["measured_excitation_voltage"],
                row["measured_shunt_deflection_mv"],
                row["time_of_first_sample"],
                row["zero_method"],
                row["remove_offset"],
                row["is_inverted"],
                row["bridge"],
                row["bridge_resistance_ohms"],
            )
            for row in sensor_rows
        ],
    )


def seed_document_and_signal_tables(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        "SELECT asset_id, filegroup_id, filename, file_extension FROM assets WHERE status = 'downloaded'"
    ).fetchall()
    signal_rows = []
    excel_rows = []
    pdf_rows = []

    for asset_id, filegroup_id, filename, extension in rows:
        container_type = classify_signal_container(extension)
        if container_type:
            signal_rows.append((asset_id, filegroup_id, container_type))
        if extension in {".xls", ".xlsx", ".xlsm"}:
            excel_rows.append((asset_id, filegroup_id, classify_workbook_type(filename)))
        if extension == ".pdf":
            pdf_rows.append((asset_id, filegroup_id))

    connection.executemany(
        """
        INSERT OR IGNORE INTO signal_containers (asset_id, filegroup_id, container_type, parser_name, extraction_status)
        VALUES (?, ?, ?, 'pending', 'pending')
        """,
        signal_rows,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO excel_workbooks (asset_id, filegroup_id, workbook_type, extraction_status)
        VALUES (?, ?, ?, 'pending')
        """,
        excel_rows,
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO pdf_documents (asset_id, filegroup_id, extraction_status)
        VALUES (?, ?, 'pending')
        """,
        pdf_rows,
    )


def record_build_run(connection: sqlite3.Connection, manifest_path: Path, analysis_dir: Path) -> None:
    connection.execute(
        "INSERT INTO build_runs (built_at, manifest_path, analysis_dir, notes) VALUES (?, ?, ?, ?)",
        (
            utc_now_iso(),
            str(manifest_path),
            str(analysis_dir),
            "Initial unified research database build from manifest and analysis CSV outputs.",
        ),
    )


def summarize(connection: sqlite3.Connection) -> dict[str, int]:
    queries = {
        "filegroups": "SELECT COUNT(*) FROM filegroups",
        "assets": "SELECT COUNT(*) FROM assets",
        "tdas_configs": "SELECT COUNT(*) FROM tdas_configs",
        "equipment_racks": "SELECT COUNT(*) FROM equipment_racks",
        "dts_files": "SELECT COUNT(*) FROM dts_files",
        "dts_modules": "SELECT COUNT(*) FROM dts_modules",
        "sensor_channels": "SELECT COUNT(*) FROM sensor_channels",
        "signal_containers": "SELECT COUNT(*) FROM signal_containers",
        "excel_workbooks": "SELECT COUNT(*) FROM excel_workbooks",
        "pdf_documents": "SELECT COUNT(*) FROM pdf_documents",
    }
    return {
        key: connection.execute(sql).fetchone()[0]
        for key, sql in queries.items()
    }


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest)
    analysis_dir = Path(args.analysis_dir)
    schema_path = Path(args.schema)
    output_db = Path(args.output_db)

    output_db.parent.mkdir(parents=True, exist_ok=True)
    if output_db.exists():
        output_db.unlink()

    connection = sqlite3.connect(output_db)
    connection.row_factory = sqlite3.Row
    create_database(connection, schema_path)
    import_manifest(connection, manifest_path)
    import_analysis_csvs(connection, analysis_dir)
    seed_document_and_signal_tables(connection)
    record_build_run(connection, manifest_path, analysis_dir)
    connection.commit()
    print(summarize(connection))
    connection.close()


if __name__ == "__main__":
    main()
