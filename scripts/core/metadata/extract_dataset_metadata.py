from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET


FILEGROUP_DIR_RE = re.compile(r"^(?P<filegroup_id>\d+)-(?P<test_code>.+)$")

FILEGROUP_COLUMNS = [
    "filegroup_id",
    "test_type_code",
    "test_type_label",
    "test_code",
    "vehicle_year",
    "vehicle_make_model",
    "tested_on",
    "title",
    "download_status",
    "file_count",
    "downloaded_file_count",
    "excluded_file_count",
    "data_root",
]

FILEGROUP_ASSET_COLUMNS = [
    "filegroup_id",
    "test_code",
    "test_type_label",
    "vehicle_year",
    "vehicle_make_model",
    "downloaded_file_rows",
    "has_das",
    "has_diadem",
    "has_edr",
    "has_excel",
    "has_dadisp",
    "has_reports",
    "has_tdms",
    "has_tdm",
    "has_tdx",
    "has_dts",
    "has_tlf",
    "has_log",
    "has_csv",
    "has_pdf",
]

TDAS_CONFIG_COLUMNS = [
    "filegroup_id",
    "test_code",
    "test_type_label",
    "vehicle_year",
    "vehicle_make_model",
    "tdas_ini_path",
    "program_version",
    "customer_name",
    "firmware_versions",
    "valid_sampling_rates",
    "filter_cutoffs",
    "com_port_config",
    "rack_inventory",
    "roi_window",
    "default_data_collection_mode",
    "export_to_ascii_options",
    "diadem_header_auto_create",
    "diadem_channel_name_mode",
    "diadem_channel_comment_mode",
]

EQUIPMENT_RACK_COLUMNS = [
    "filegroup_id",
    "test_code",
    "test_type_label",
    "vehicle_year",
    "vehicle_make_model",
    "equipment_ini_path",
    "rack_id",
    "connect_info",
]

DTS_FILE_COLUMNS = [
    "filegroup_id",
    "test_code",
    "test_type_label",
    "vehicle_year",
    "vehicle_make_model",
    "dts_path",
    "dts_test_id",
    "dts_description",
    "event_number",
    "software",
    "software_version",
    "module_count",
    "channel_count",
]

DTS_MODULE_COLUMNS = [
    "filegroup_id",
    "test_code",
    "dts_path",
    "module_number",
    "module_serial_number",
    "module_base_serial_number",
    "module_sample_rate_hz",
    "module_pre_trigger_seconds",
    "module_post_trigger_seconds",
    "module_number_of_channels",
    "module_recording_mode",
    "module_aa_filter_rate_hz",
]

SENSOR_CHANNEL_COLUMNS = [
    "filegroup_id",
    "test_code",
    "test_type_label",
    "vehicle_year",
    "vehicle_make_model",
    "dts_path",
    "dts_description",
    "module_number",
    "module_sample_rate_hz",
    "module_recording_mode",
    "channel_xml_type",
    "channel_number",
    "channel_id",
    "hardware_channel_name",
    "channel_group_name",
    "channel_name2",
    "channel_description_string",
    "description",
    "iso_code",
    "iso_channel_name",
    "eu",
    "desired_range",
    "sensitivity",
    "sensitivity_units",
    "sensor_capacity",
    "sensor_polarity",
    "serial_number",
    "sensor_id",
    "software_filter",
    "excitation_voltage",
    "measured_excitation_voltage",
    "measured_shunt_deflection_mv",
    "time_of_first_sample",
    "zero_method",
    "remove_offset",
    "is_inverted",
    "bridge",
    "bridge_resistance_ohms",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract IIHS dataset metadata into CSV/JSON artifacts.")
    parser.add_argument("--manifest", default="data/index/manifest.sqlite")
    parser.add_argument("--raw-root", default="data/raw")
    parser.add_argument("--output-dir", default="data/analysis")
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def detect_extension(filename: str) -> str:
    filename = filename.lower()
    last_dot = filename.rfind(".")
    if last_dot < 0:
        return "[no_ext]"
    return filename[last_dot:]


def parse_filegroup_root(path: Path) -> tuple[int | None, str | None]:
    for part in path.parts:
        match = FILEGROUP_DIR_RE.match(part)
        if match:
            return int(match.group("filegroup_id")), match.group("test_code")
    return None, None


def load_manifest_data(manifest_path: Path) -> tuple[list[dict], list[dict]]:
    connection = sqlite3.connect(manifest_path)
    connection.row_factory = sqlite3.Row
    filegroups = [
        dict(row)
        for row in connection.execute(
            """
            SELECT filegroup_id,
                   test_type_code,
                   test_type_label,
                   test_code,
                   vehicle_year,
                   vehicle_make_model,
                   tested_on,
                   title,
                   download_status,
                   file_count,
                   downloaded_file_count,
                   excluded_file_count,
                   data_root
              FROM filegroups
             ORDER BY test_type_code, filegroup_id
            """
        )
    ]
    downloaded_files = [
        dict(row)
        for row in connection.execute(
            """
            SELECT filegroup_id,
                   folder_path,
                   filename,
                   relative_path,
                   local_path
              FROM files
             WHERE status = 'downloaded'
            """
        )
    ]
    connection.close()
    return filegroups, downloaded_files


def build_manifest_profiles(filegroups: list[dict], downloaded_files: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    extension_counter: Counter[str] = Counter()
    folder_counter: Counter[str] = Counter()
    vehicle_counter: Counter[tuple] = Counter(
        (row["vehicle_year"], row["vehicle_make_model"], row["test_type_label"]) for row in filegroups
    )
    asset_rows_by_id = {
        row["filegroup_id"]: {
            "filegroup_id": row["filegroup_id"],
            "test_code": row["test_code"],
            "test_type_label": row["test_type_label"],
            "vehicle_year": row["vehicle_year"],
            "vehicle_make_model": row["vehicle_make_model"],
            "downloaded_file_rows": 0,
            "has_das": False,
            "has_diadem": False,
            "has_edr": False,
            "has_excel": False,
            "has_dadisp": False,
            "has_reports": False,
            "has_tdms": False,
            "has_tdm": False,
            "has_tdx": False,
            "has_dts": False,
            "has_tlf": False,
            "has_log": False,
            "has_csv": False,
            "has_pdf": False,
        }
        for row in filegroups
    }

    for row in downloaded_files:
        extension = detect_extension(row["filename"])
        folder_path = row["folder_path"]
        extension_counter[extension] += 1
        folder_counter[folder_path] += 1
        asset = asset_rows_by_id[row["filegroup_id"]]
        asset["downloaded_file_rows"] += 1
        asset["has_das"] = asset["has_das"] or folder_path.startswith("DATA\\DAS")
        asset["has_diadem"] = asset["has_diadem"] or folder_path.startswith("DATA\\DIAdem") or folder_path.startswith("DATA\\DIADEM")
        asset["has_edr"] = asset["has_edr"] or folder_path.startswith("DATA\\EDR")
        asset["has_excel"] = asset["has_excel"] or folder_path.startswith("DATA\\EXCEL")
        asset["has_dadisp"] = asset["has_dadisp"] or folder_path.startswith("DATA\\DADISP")
        asset["has_reports"] = asset["has_reports"] or folder_path.startswith("REPORTS")
        asset["has_tdms"] = asset["has_tdms"] or extension == ".tdms"
        asset["has_tdm"] = asset["has_tdm"] or extension == ".tdm"
        asset["has_tdx"] = asset["has_tdx"] or extension == ".tdx"
        asset["has_dts"] = asset["has_dts"] or extension == ".dts"
        asset["has_tlf"] = asset["has_tlf"] or extension in {".tlf", ".tlf pretest backup"}
        asset["has_log"] = asset["has_log"] or extension == ".log"
        asset["has_csv"] = asset["has_csv"] or extension == ".csv"
        asset["has_pdf"] = asset["has_pdf"] or extension == ".pdf"

    asset_rows = [asset_rows_by_id[row["filegroup_id"]] for row in filegroups]
    extension_rows = [{"extension": ext, "file_count": count} for ext, count in extension_counter.most_common()]
    folder_rows = [{"folder_path": folder, "file_count": count} for folder, count in folder_counter.most_common()]
    vehicle_rows = [
        {
            "vehicle_year": year,
            "vehicle_make_model": vehicle,
            "test_type_label": test_type,
            "filegroup_count": count,
        }
        for (year, vehicle, test_type), count in sorted(vehicle_counter.items())
    ]
    return asset_rows, extension_rows, folder_rows, vehicle_rows


def parse_tdas_sections(path: Path) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("----") and stripped.endswith("----"):
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = stripped.strip("- ").strip()
            current_lines = []
            continue
        if current_key is not None:
            current_lines.append(raw_line.rstrip())
    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()
    return sections


def parse_dts_xml(path: Path) -> ET.Element:
    try:
        text = path.read_text(encoding="utf-16")
    except UnicodeError:
        text = path.read_text(encoding="utf-8", errors="replace")

    try:
        return ET.fromstring(text)
    except ET.ParseError:
        start = text.find("<?xml")
        if start < 0:
            start = text.find("<Test")
        end = text.rfind("</Test>")
        if start >= 0 and end >= 0:
            trimmed = text[start : end + len("</Test>")]
            return ET.fromstring(trimmed)
        raise


def scan_tdas_config(raw_root: Path, filegroup_map: dict[int, dict]) -> tuple[list[dict], list[dict]]:
    tdas_rows: list[dict] = []
    equipment_rows: list[dict] = []
    for ini_path in raw_root.rglob("tdas.ini"):
        filegroup_id, _ = parse_filegroup_root(ini_path)
        if filegroup_id is None or filegroup_id not in filegroup_map:
            continue
        filegroup = filegroup_map[filegroup_id]
        sections = parse_tdas_sections(ini_path)
        tdas_rows.append(
            {
                "filegroup_id": filegroup_id,
                "test_code": filegroup["test_code"],
                "test_type_label": filegroup["test_type_label"],
                "vehicle_year": filegroup["vehicle_year"],
                "vehicle_make_model": filegroup["vehicle_make_model"],
                "tdas_ini_path": str(ini_path),
                "program_version": sections.get("Program Version", ""),
                "customer_name": sections.get("Customer Name", ""),
                "firmware_versions": sections.get("Current Firmware Versions (SIM, TOM, DIM, Rack, G5)", ""),
                "valid_sampling_rates": sections.get("Valid Sampling Rates", ""),
                "filter_cutoffs": sections.get("Corresponding Variable Filter Cutoffs (0 = PRO: No Adj Filter, G5: Max Adj Filter)", ""),
                "com_port_config": sections.get("Current RS232/422 Com Port Number, Max Com Speed, Max Com Ports", ""),
                "rack_inventory": sections.get("Rack Inventory (Number, S/N No., Size, IP Address)", ""),
                "roi_window": sections.get("ROI - Region of Interest (Example -1.000, 2.500) Enter -9999.0, 9999.0 to default to time in TSF)", ""),
                "default_data_collection_mode": sections.get("Default Data Collection Mode - (CIRCULAR-BUFFER=0, RECORDER=1, or MULTIPLE-EVENT=2)", ""),
                "export_to_ascii_options": sections.get("Export to ASCII Options (DataType, Time Column, ASCII_Excel, OneorMoreFiles, HeaderOption, Items Checked)", ""),
                "diadem_header_auto_create": sections.get("DIAdem Export: Create DIAdem header automatically with data download (0 = No, 1 = Yes)", ""),
                "diadem_channel_name_mode": sections.get("DIAdem Export: Channel Name (0 = None, 1 = Channel Description, 2 = ISO Code, 3 = Sensor SN, 4 = Channel Comment)", ""),
                "diadem_channel_comment_mode": sections.get("DIAdem Export: Channel Comment (0 = None, 1 = Channel Description, 2 = ISO Code, 3 = Sensor SN, 4 = Channel Comment)", ""),
            }
        )

    for equipment_path in raw_root.rglob("Equipment.ini"):
        filegroup_id, _ = parse_filegroup_root(equipment_path)
        if filegroup_id is None or filegroup_id not in filegroup_map:
            continue
        filegroup = filegroup_map[filegroup_id]
        rack_id = None
        for line in equipment_path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("RackID"):
                rack_id = stripped.split("=", 1)[1].strip()
            elif stripped.startswith("ConnectInfo") and rack_id:
                equipment_rows.append(
                    {
                        "filegroup_id": filegroup_id,
                        "test_code": filegroup["test_code"],
                        "test_type_label": filegroup["test_type_label"],
                        "vehicle_year": filegroup["vehicle_year"],
                        "vehicle_make_model": filegroup["vehicle_make_model"],
                        "equipment_ini_path": str(equipment_path),
                        "rack_id": rack_id,
                        "connect_info": stripped.split("=", 1)[1].strip(),
                    }
                )
                rack_id = None

    tdas_rows.sort(key=lambda row: row["filegroup_id"])
    equipment_rows.sort(key=lambda row: (row["filegroup_id"], row["rack_id"]))
    return tdas_rows, equipment_rows


def parse_dts_catalog(raw_root: Path, filegroup_map: dict[int, dict]) -> tuple[list[dict], list[dict], list[dict]]:
    dts_rows: list[dict] = []
    module_rows: list[dict] = []
    sensor_rows: list[dict] = []

    for dts_path in raw_root.rglob("*.dts"):
        filegroup_id, _ = parse_filegroup_root(dts_path)
        if filegroup_id is None or filegroup_id not in filegroup_map:
            continue

        filegroup = filegroup_map[filegroup_id]
        root = parse_dts_xml(dts_path)

        modules = root.findall("./Modules/Module")
        channel_count = 0
        dts_row = {
            "filegroup_id": filegroup_id,
            "test_code": filegroup["test_code"],
            "test_type_label": filegroup["test_type_label"],
            "vehicle_year": filegroup["vehicle_year"],
            "vehicle_make_model": filegroup["vehicle_make_model"],
            "dts_path": str(dts_path),
            "dts_test_id": root.attrib.get("Id", ""),
            "dts_description": root.attrib.get("Description", ""),
            "event_number": root.attrib.get("EventNumber", ""),
            "software": root.attrib.get("Software", ""),
            "software_version": root.attrib.get("SoftwareVersion", ""),
            "module_count": len(modules),
            "channel_count": 0,
        }

        for module in modules:
            module_rows.append(
                {
                    "filegroup_id": filegroup_id,
                    "test_code": filegroup["test_code"],
                    "dts_path": str(dts_path),
                    "module_number": module.attrib.get("Number", ""),
                    "module_serial_number": module.attrib.get("SerialNumber", ""),
                    "module_base_serial_number": module.attrib.get("BaseSerialNumber", ""),
                    "module_sample_rate_hz": module.attrib.get("SampleRateHz", ""),
                    "module_pre_trigger_seconds": module.attrib.get("PreTriggerSeconds", ""),
                    "module_post_trigger_seconds": module.attrib.get("PostTriggerSeconds", ""),
                    "module_number_of_channels": module.attrib.get("NumberOfChannels", ""),
                    "module_recording_mode": module.attrib.get("RecordingMode", ""),
                    "module_aa_filter_rate_hz": module.attrib.get("AaFilterRateHz", ""),
                }
            )
            channels_parent = module.find("./Channels")
            if channels_parent is None:
                continue
            for channel in channels_parent:
                channel_count += 1
                sensor_rows.append(
                    {
                        "filegroup_id": filegroup_id,
                        "test_code": filegroup["test_code"],
                        "test_type_label": filegroup["test_type_label"],
                        "vehicle_year": filegroup["vehicle_year"],
                        "vehicle_make_model": filegroup["vehicle_make_model"],
                        "dts_path": str(dts_path),
                        "dts_description": root.attrib.get("Description", ""),
                        "module_number": module.attrib.get("Number", ""),
                        "module_sample_rate_hz": module.attrib.get("SampleRateHz", ""),
                        "module_recording_mode": module.attrib.get("RecordingMode", ""),
                        "channel_xml_type": channel.tag,
                        "channel_number": channel.attrib.get("Number", ""),
                        "channel_id": channel.attrib.get("ChannelId", ""),
                        "hardware_channel_name": channel.attrib.get("HardwareChannelName", ""),
                        "channel_group_name": channel.attrib.get("ChannelGroupName", ""),
                        "channel_name2": channel.attrib.get("ChannelName2", ""),
                        "channel_description_string": channel.attrib.get("ChannelDescriptionString", ""),
                        "description": channel.attrib.get("Description", ""),
                        "iso_code": channel.attrib.get("IsoCode", ""),
                        "iso_channel_name": channel.attrib.get("IsoChannelName", ""),
                        "eu": channel.attrib.get("Eu", ""),
                        "desired_range": channel.attrib.get("DesiredRange", ""),
                        "sensitivity": channel.attrib.get("Sensitivity", ""),
                        "sensitivity_units": channel.attrib.get("SensitivityUnits", ""),
                        "sensor_capacity": channel.attrib.get("SensorCapacity", ""),
                        "sensor_polarity": channel.attrib.get("SensorPolarity", ""),
                        "serial_number": channel.attrib.get("SerialNumber", ""),
                        "sensor_id": channel.attrib.get("SensorID", ""),
                        "software_filter": channel.attrib.get("SoftwareFilter", ""),
                        "excitation_voltage": channel.attrib.get("ExcitationVoltage", ""),
                        "measured_excitation_voltage": channel.attrib.get("MeasuredExcitationVoltage", ""),
                        "measured_shunt_deflection_mv": channel.attrib.get("MeasuredShuntDeflectionMv", ""),
                        "time_of_first_sample": channel.attrib.get("TimeOfFirstSample", ""),
                        "zero_method": channel.attrib.get("ZeroMethod", ""),
                        "remove_offset": channel.attrib.get("RemoveOffset", ""),
                        "is_inverted": channel.attrib.get("IsInverted", ""),
                        "bridge": channel.attrib.get("Bridge", ""),
                        "bridge_resistance_ohms": channel.attrib.get("BridgeResistanceOhms", ""),
                    }
                )
        dts_row["channel_count"] = channel_count
        dts_rows.append(dts_row)

    dts_rows.sort(key=lambda row: row["filegroup_id"])
    module_rows.sort(key=lambda row: (row["filegroup_id"], row["module_number"], row["module_serial_number"]))
    sensor_rows.sort(key=lambda row: (row["filegroup_id"], row["module_number"], row["channel_number"]))
    return dts_rows, module_rows, sensor_rows


def build_sensor_summaries(sensor_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    channel_group_counter: Counter[tuple[str, str]] = Counter()
    unit_counter: Counter[str] = Counter()
    for row in sensor_rows:
        channel_group_counter[(row["channel_group_name"], row["eu"])] += 1
        unit_counter[row["eu"] or "[blank]"] += 1
    channel_group_rows = [
        {"channel_group_name": group_name, "eu": eu, "channel_count": count}
        for (group_name, eu), count in channel_group_counter.most_common()
    ]
    unit_rows = [{"eu": eu, "channel_count": count} for eu, count in unit_counter.most_common()]
    return channel_group_rows, unit_rows


def build_overview(filegroups: list[dict], asset_rows: list[dict], extension_rows: list[dict], folder_rows: list[dict], dts_rows: list[dict], sensor_rows: list[dict], tdas_rows: list[dict], equipment_rows: list[dict]) -> dict:
    year_counter: Counter[int] = Counter()
    type_counter: Counter[str] = Counter()
    for row in filegroups:
        if row["vehicle_year"] is not None:
            year_counter[row["vehicle_year"]] += 1
        type_counter[row["test_type_label"]] += 1
    unique_years = sorted(year_counter)
    return {
        "generated_at": utc_now_iso(),
        "filegroup_count": len(filegroups),
        "vehicle_year_min": unique_years[0] if unique_years else None,
        "vehicle_year_max": unique_years[-1] if unique_years else None,
        "filegroups_by_test_type": [{"test_type_label": label, "filegroup_count": count} for label, count in sorted(type_counter.items())],
        "filegroups_by_year": [{"vehicle_year": year, "filegroup_count": count} for year, count in sorted(year_counter.items())],
        "downloaded_filegroups": sum(1 for row in filegroups if row["download_status"] == "downloaded"),
        "error_filegroups": sum(1 for row in filegroups if row["download_status"] == "error"),
        "downloaded_file_rows": sum(row["downloaded_file_count"] or 0 for row in filegroups),
        "excluded_file_rows": sum(row["excluded_file_count"] or 0 for row in filegroups),
        "filegroups_with_dts": len({row["filegroup_id"] for row in dts_rows}),
        "dts_file_count": len(dts_rows),
        "sensor_channel_count": len(sensor_rows),
        "tdas_ini_count": len(tdas_rows),
        "equipment_ini_count": len(equipment_rows),
        "top_extensions": extension_rows[:20],
        "top_folders": folder_rows[:20],
        "asset_presence": {
            "has_das": sum(1 for row in asset_rows if row["has_das"]),
            "has_diadem": sum(1 for row in asset_rows if row["has_diadem"]),
            "has_edr": sum(1 for row in asset_rows if row["has_edr"]),
            "has_excel": sum(1 for row in asset_rows if row["has_excel"]),
            "has_dadisp": sum(1 for row in asset_rows if row["has_dadisp"]),
            "has_tdms": sum(1 for row in asset_rows if row["has_tdms"]),
            "has_tdm": sum(1 for row in asset_rows if row["has_tdm"]),
            "has_tdx": sum(1 for row in asset_rows if row["has_tdx"]),
        },
    }


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest)
    raw_root = Path(args.raw_root)
    output_dir = Path(args.output_dir)
    filegroups, downloaded_files = load_manifest_data(manifest_path)
    filegroup_map = {row["filegroup_id"]: row for row in filegroups}
    asset_rows, extension_rows, folder_rows, vehicle_rows = build_manifest_profiles(filegroups, downloaded_files)
    tdas_rows, equipment_rows = scan_tdas_config(raw_root, filegroup_map)
    dts_rows, module_rows, sensor_rows = parse_dts_catalog(raw_root, filegroup_map)
    channel_group_rows, unit_rows = build_sensor_summaries(sensor_rows)
    overview = build_overview(filegroups, asset_rows, extension_rows, folder_rows, dts_rows, sensor_rows, tdas_rows, equipment_rows)

    write_json(output_dir / "dataset_overview.json", overview)
    write_csv(output_dir / "filegroups.csv", FILEGROUP_COLUMNS, filegroups)
    write_csv(output_dir / "filegroup_assets.csv", FILEGROUP_ASSET_COLUMNS, asset_rows)
    write_csv(output_dir / "vehicle_catalog.csv", ["vehicle_year", "vehicle_make_model", "test_type_label", "filegroup_count"], vehicle_rows)
    write_csv(output_dir / "file_extensions.csv", ["extension", "file_count"], extension_rows)
    write_csv(output_dir / "folder_profile.csv", ["folder_path", "file_count"], folder_rows)
    write_csv(output_dir / "tdas_configs.csv", TDAS_CONFIG_COLUMNS, tdas_rows)
    write_csv(output_dir / "equipment_racks.csv", EQUIPMENT_RACK_COLUMNS, equipment_rows)
    write_csv(output_dir / "dts_files.csv", DTS_FILE_COLUMNS, dts_rows)
    write_csv(output_dir / "dts_modules.csv", DTS_MODULE_COLUMNS, module_rows)
    write_csv(output_dir / "sensor_channels.csv", SENSOR_CHANNEL_COLUMNS, sensor_rows)
    write_csv(output_dir / "channel_groups.csv", ["channel_group_name", "eu", "channel_count"], channel_group_rows)
    write_csv(output_dir / "channel_units.csv", ["eu", "channel_count"], unit_rows)
    print(json.dumps(overview, indent=2))


if __name__ == "__main__":
    main()
