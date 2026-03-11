PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS build_runs (
  build_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  built_at TEXT NOT NULL,
  manifest_path TEXT NOT NULL,
  analysis_dir TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS test_types (
  test_type_code INTEGER PRIMARY KEY,
  test_type_label TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS vehicles (
  vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
  vehicle_year INTEGER,
  vehicle_make_model TEXT NOT NULL,
  UNIQUE(vehicle_year, vehicle_make_model)
);

CREATE TABLE IF NOT EXISTS filegroups (
  filegroup_id INTEGER PRIMARY KEY,
  vehicle_id INTEGER,
  test_type_code INTEGER NOT NULL,
  test_code TEXT,
  title TEXT NOT NULL,
  tested_on TEXT,
  detail_url TEXT,
  discovered_at TEXT,
  last_seen_at TEXT,
  source TEXT,
  list_page INTEGER,
  download_status TEXT NOT NULL,
  folder_count INTEGER NOT NULL DEFAULT 0,
  file_count INTEGER NOT NULL DEFAULT 0,
  downloaded_file_count INTEGER NOT NULL DEFAULT 0,
  excluded_file_count INTEGER NOT NULL DEFAULT 0,
  data_root TEXT,
  last_error TEXT,
  FOREIGN KEY(vehicle_id) REFERENCES vehicles(vehicle_id),
  FOREIGN KEY(test_type_code) REFERENCES test_types(test_type_code)
);

CREATE TABLE IF NOT EXISTS folders (
  folder_id INTEGER PRIMARY KEY AUTOINCREMENT,
  filegroup_id INTEGER NOT NULL,
  folder_path TEXT NOT NULL,
  status TEXT,
  excluded_reason TEXT,
  UNIQUE(filegroup_id, folder_path),
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assets (
  asset_id INTEGER PRIMARY KEY,
  filegroup_id INTEGER NOT NULL,
  folder_path TEXT NOT NULL,
  filename TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  local_path TEXT,
  listed_on_page INTEGER,
  modified_label TEXT,
  size_label TEXT,
  source_url TEXT,
  content_type TEXT,
  content_disposition TEXT,
  size_bytes INTEGER,
  sha256 TEXT,
  status TEXT NOT NULL,
  excluded_reason TEXT,
  downloaded_at TEXT,
  last_error TEXT,
  file_extension TEXT,
  parser_status TEXT DEFAULT 'pending',
  UNIQUE(filegroup_id, relative_path),
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tdas_configs (
  tdas_config_id INTEGER PRIMARY KEY AUTOINCREMENT,
  filegroup_id INTEGER NOT NULL,
  tdas_ini_path TEXT NOT NULL,
  program_version TEXT,
  customer_name TEXT,
  firmware_versions TEXT,
  valid_sampling_rates TEXT,
  filter_cutoffs TEXT,
  com_port_config TEXT,
  rack_inventory TEXT,
  roi_window TEXT,
  default_data_collection_mode TEXT,
  export_to_ascii_options TEXT,
  diadem_header_auto_create TEXT,
  diadem_channel_name_mode TEXT,
  diadem_channel_comment_mode TEXT,
  UNIQUE(filegroup_id, tdas_ini_path),
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS equipment_racks (
  equipment_rack_id INTEGER PRIMARY KEY AUTOINCREMENT,
  filegroup_id INTEGER NOT NULL,
  equipment_ini_path TEXT NOT NULL,
  rack_id TEXT NOT NULL,
  connect_info TEXT,
  UNIQUE(filegroup_id, equipment_ini_path, rack_id),
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dts_files (
  dts_file_id INTEGER PRIMARY KEY AUTOINCREMENT,
  filegroup_id INTEGER NOT NULL,
  asset_id INTEGER,
  dts_path TEXT NOT NULL,
  dts_test_id TEXT,
  dts_description TEXT,
  event_number TEXT,
  software TEXT,
  software_version TEXT,
  module_count INTEGER,
  channel_count INTEGER,
  UNIQUE(filegroup_id, dts_path),
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE,
  FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
);

CREATE TABLE IF NOT EXISTS dts_modules (
  dts_module_id INTEGER PRIMARY KEY AUTOINCREMENT,
  dts_file_id INTEGER NOT NULL,
  filegroup_id INTEGER NOT NULL,
  module_number TEXT,
  module_serial_number TEXT,
  module_base_serial_number TEXT,
  module_sample_rate_hz TEXT,
  module_pre_trigger_seconds TEXT,
  module_post_trigger_seconds TEXT,
  module_number_of_channels TEXT,
  module_recording_mode TEXT,
  module_aa_filter_rate_hz TEXT,
  UNIQUE(dts_file_id, module_number, module_serial_number),
  FOREIGN KEY(dts_file_id) REFERENCES dts_files(dts_file_id) ON DELETE CASCADE,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sensor_channels (
  sensor_channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
  dts_file_id INTEGER,
  filegroup_id INTEGER NOT NULL,
  test_code TEXT,
  module_number TEXT,
  module_sample_rate_hz TEXT,
  module_recording_mode TEXT,
  channel_xml_type TEXT,
  channel_number TEXT,
  channel_id TEXT,
  hardware_channel_name TEXT,
  channel_group_name TEXT,
  channel_name2 TEXT,
  channel_description_string TEXT,
  description TEXT,
  iso_code TEXT,
  iso_channel_name TEXT,
  eu TEXT,
  desired_range TEXT,
  sensitivity TEXT,
  sensitivity_units TEXT,
  sensor_capacity TEXT,
  sensor_polarity TEXT,
  serial_number TEXT,
  sensor_id TEXT,
  software_filter TEXT,
  excitation_voltage TEXT,
  measured_excitation_voltage TEXT,
  measured_shunt_deflection_mv TEXT,
  time_of_first_sample TEXT,
  zero_method TEXT,
  remove_offset TEXT,
  is_inverted TEXT,
  bridge TEXT,
  bridge_resistance_ohms TEXT,
  FOREIGN KEY(dts_file_id) REFERENCES dts_files(dts_file_id) ON DELETE SET NULL,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS signal_containers (
  signal_container_id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL UNIQUE,
  filegroup_id INTEGER NOT NULL,
  container_type TEXT NOT NULL,
  parser_name TEXT,
  extraction_status TEXT NOT NULL DEFAULT 'pending',
  channel_count INTEGER,
  sample_rate_hz REAL,
  notes TEXT,
  FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS signal_series (
  signal_series_id INTEGER PRIMARY KEY AUTOINCREMENT,
  signal_container_id INTEGER NOT NULL,
  filegroup_id INTEGER NOT NULL,
  series_key TEXT NOT NULL,
  series_name TEXT,
  unit TEXT,
  sample_rate_hz REAL,
  sample_count INTEGER,
  time_start REAL,
  time_end REAL,
  parquet_path TEXT,
  stats_json TEXT,
  UNIQUE(signal_container_id, series_key),
  FOREIGN KEY(signal_container_id) REFERENCES signal_containers(signal_container_id) ON DELETE CASCADE,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS preprocessing_runs (
  preprocessing_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  parser_version TEXT NOT NULL,
  scope TEXT,
  modes_json TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS preprocessing_cases (
  preprocessing_case_id INTEGER PRIMARY KEY AUTOINCREMENT,
  preprocessing_run_id INTEGER,
  filegroup_id INTEGER NOT NULL,
  tdms_asset_id INTEGER,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  case_root TEXT NOT NULL,
  manifest_path TEXT NOT NULL,
  wide_path TEXT,
  long_path TEXT,
  harmonized_wide_path TEXT,
  harmonized_long_path TEXT,
  reference_method TEXT,
  reference_time_s REAL,
  reference_index INTEGER,
  native_time_start_s REAL,
  native_time_end_s REAL,
  native_sample_rate_hz REAL,
  native_sample_count INTEGER,
  harmonized_time_start_s REAL,
  harmonized_time_end_s REAL,
  harmonized_sample_rate_hz REAL,
  harmonized_sample_count INTEGER,
  metrics_json TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(filegroup_id, mode),
  FOREIGN KEY(preprocessing_run_id) REFERENCES preprocessing_runs(preprocessing_run_id) ON DELETE SET NULL,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE,
  FOREIGN KEY(tdms_asset_id) REFERENCES assets(asset_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS preprocessing_series (
  preprocessing_series_id INTEGER PRIMARY KEY AUTOINCREMENT,
  preprocessing_case_id INTEGER NOT NULL,
  standard_name TEXT NOT NULL,
  channel_family TEXT,
  unit TEXT,
  cfc_class INTEGER,
  source_group TEXT,
  source_channel TEXT,
  raw_reference_group TEXT,
  raw_reference_channel TEXT,
  native_sample_count INTEGER,
  harmonized_non_null_count INTEGER,
  stats_json TEXT,
  UNIQUE(preprocessing_case_id, standard_name),
  FOREIGN KEY(preprocessing_case_id) REFERENCES preprocessing_cases(preprocessing_case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS preprocessing_feature_runs (
  preprocessing_feature_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  parser_version TEXT NOT NULL,
  source_mode TEXT NOT NULL,
  feature_space TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS preprocessing_feature_sets (
  preprocessing_feature_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
  preprocessing_feature_run_id INTEGER,
  preprocessing_case_id INTEGER NOT NULL,
  filegroup_id INTEGER NOT NULL,
  source_mode TEXT NOT NULL,
  feature_space TEXT NOT NULL,
  status TEXT NOT NULL,
  feature_count INTEGER,
  vector_json TEXT,
  coverage_json TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(preprocessing_case_id, feature_space),
  FOREIGN KEY(preprocessing_feature_run_id) REFERENCES preprocessing_feature_runs(preprocessing_feature_run_id) ON DELETE SET NULL,
  FOREIGN KEY(preprocessing_case_id) REFERENCES preprocessing_cases(preprocessing_case_id) ON DELETE CASCADE,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS preprocessing_feature_values (
  preprocessing_feature_value_id INTEGER PRIMARY KEY AUTOINCREMENT,
  preprocessing_feature_set_id INTEGER NOT NULL,
  standard_name TEXT NOT NULL,
  feature_name TEXT NOT NULL,
  feature_value_number REAL,
  feature_unit TEXT,
  UNIQUE(preprocessing_feature_set_id, standard_name, feature_name),
  FOREIGN KEY(preprocessing_feature_set_id) REFERENCES preprocessing_feature_sets(preprocessing_feature_set_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS preprocessing_neighbors (
  preprocessing_neighbor_id INTEGER PRIMARY KEY AUTOINCREMENT,
  preprocessing_feature_run_id INTEGER,
  source_feature_set_id INTEGER NOT NULL,
  target_feature_set_id INTEGER NOT NULL,
  feature_space TEXT NOT NULL,
  rank INTEGER NOT NULL,
  similarity_score REAL,
  distance_score REAL,
  weighted_correlation REAL,
  dtw_distance REAL,
  overlap_channel_count INTEGER,
  multiview_score REAL,
  pulse_view_score REAL,
  occupant_view_score REAL,
  lower_extremity_view_score REAL,
  pulse_phase_score REAL,
  occupant_phase_score REAL,
  lower_extremity_phase_score REAL,
  algorithm TEXT NOT NULL,
  UNIQUE(source_feature_set_id, target_feature_set_id, feature_space, algorithm),
  FOREIGN KEY(preprocessing_feature_run_id) REFERENCES preprocessing_feature_runs(preprocessing_feature_run_id) ON DELETE SET NULL,
  FOREIGN KEY(source_feature_set_id) REFERENCES preprocessing_feature_sets(preprocessing_feature_set_id) ON DELETE CASCADE,
  FOREIGN KEY(target_feature_set_id) REFERENCES preprocessing_feature_sets(preprocessing_feature_set_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS preprocessing_clusters (
  preprocessing_cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
  preprocessing_feature_run_id INTEGER,
  preprocessing_feature_set_id INTEGER NOT NULL,
  feature_space TEXT NOT NULL,
  algorithm TEXT NOT NULL,
  cluster_label INTEGER NOT NULL,
  centroid_distance REAL,
  outlier_score REAL,
  robust_distance_score REAL,
  local_density_outlier_score REAL,
  stability_score REAL,
  coverage_score REAL,
  is_outlier INTEGER NOT NULL DEFAULT 0,
  UNIQUE(preprocessing_feature_set_id, feature_space, algorithm),
  FOREIGN KEY(preprocessing_feature_run_id) REFERENCES preprocessing_feature_runs(preprocessing_feature_run_id) ON DELETE SET NULL,
  FOREIGN KEY(preprocessing_feature_set_id) REFERENCES preprocessing_feature_sets(preprocessing_feature_set_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS preprocessing_representatives (
  preprocessing_representative_id INTEGER PRIMARY KEY AUTOINCREMENT,
  preprocessing_feature_run_id INTEGER,
  preprocessing_feature_set_id INTEGER NOT NULL,
  feature_space TEXT NOT NULL,
  algorithm TEXT NOT NULL,
  representative_kind TEXT NOT NULL,
  cluster_label INTEGER,
  rank INTEGER NOT NULL,
  score REAL,
  UNIQUE(preprocessing_feature_set_id, feature_space, algorithm, representative_kind),
  FOREIGN KEY(preprocessing_feature_run_id) REFERENCES preprocessing_feature_runs(preprocessing_feature_run_id) ON DELETE SET NULL,
  FOREIGN KEY(preprocessing_feature_set_id) REFERENCES preprocessing_feature_sets(preprocessing_feature_set_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS excel_workbooks (
  excel_workbook_id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL UNIQUE,
  filegroup_id INTEGER NOT NULL,
  workbook_type TEXT,
  extraction_status TEXT NOT NULL DEFAULT 'pending',
  notes TEXT,
  FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS excel_sheets (
  excel_sheet_id INTEGER PRIMARY KEY AUTOINCREMENT,
  excel_workbook_id INTEGER NOT NULL,
  asset_id INTEGER NOT NULL,
  sheet_name TEXT NOT NULL,
  row_count INTEGER,
  column_count INTEGER,
  extraction_status TEXT NOT NULL DEFAULT 'pending',
  UNIQUE(excel_workbook_id, sheet_name),
  FOREIGN KEY(excel_workbook_id) REFERENCES excel_workbooks(excel_workbook_id) ON DELETE CASCADE,
  FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_documents (
  pdf_document_id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL UNIQUE,
  filegroup_id INTEGER NOT NULL,
  extraction_status TEXT NOT NULL DEFAULT 'pending',
  page_count INTEGER,
  parser_name TEXT,
  notes TEXT,
  FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_pages (
  pdf_page_id INTEGER PRIMARY KEY AUTOINCREMENT,
  pdf_document_id INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  text_content TEXT,
  table_json TEXT,
  UNIQUE(pdf_document_id, page_number),
  FOREIGN KEY(pdf_document_id) REFERENCES pdf_documents(pdf_document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_extraction_runs (
  pdf_extraction_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  parser_version TEXT NOT NULL,
  scope TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS pdf_layout_families (
  family_key TEXT PRIMARY KEY,
  family_label TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS pdf_layout_assignments (
  pdf_layout_assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
  pdf_document_id INTEGER NOT NULL,
  pdf_extraction_run_id INTEGER,
  family_key TEXT NOT NULL,
  confidence REAL,
  classification_method TEXT,
  signature_hash TEXT,
  preview_png_path TEXT,
  fingerprint_json TEXT,
  classified_at TEXT NOT NULL,
  notes TEXT,
  UNIQUE(pdf_document_id, pdf_extraction_run_id),
  FOREIGN KEY(pdf_document_id) REFERENCES pdf_documents(pdf_document_id) ON DELETE CASCADE,
  FOREIGN KEY(pdf_extraction_run_id) REFERENCES pdf_extraction_runs(pdf_extraction_run_id) ON DELETE SET NULL,
  FOREIGN KEY(family_key) REFERENCES pdf_layout_families(family_key)
);

CREATE TABLE IF NOT EXISTS pdf_page_features (
  pdf_document_id INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  page_width REAL,
  page_height REAL,
  word_count INTEGER,
  char_count INTEGER,
  table_count INTEGER,
  first_line TEXT,
  last_line TEXT,
  heading_lines_json TEXT,
  layout_signature TEXT,
  PRIMARY KEY(pdf_document_id, page_number),
  FOREIGN KEY(pdf_document_id) REFERENCES pdf_documents(pdf_document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_document_inventory (
  pdf_document_id INTEGER PRIMARY KEY,
  asset_id INTEGER NOT NULL UNIQUE,
  filegroup_id INTEGER NOT NULL,
  test_code TEXT,
  title TEXT,
  filegroup_tested_on TEXT,
  test_type_label TEXT,
  vehicle_year INTEGER,
  vehicle_make_model TEXT,
  dataset_partition TEXT,
  pdf_role TEXT NOT NULL,
  family_key TEXT,
  family_label TEXT,
  family_source_kind TEXT,
  extraction_status TEXT NOT NULL,
  local_exists INTEGER NOT NULL DEFAULT 1,
  local_path TEXT,
  relative_path TEXT,
  folder_path TEXT,
  filename TEXT,
  page_count INTEGER,
  total_table_count INTEGER,
  pages_with_tables INTEGER,
  total_word_count INTEGER,
  avg_words_per_page REAL,
  first_page_heading TEXT,
  second_page_heading TEXT,
  report_vehicle_title TEXT,
  report_tested_on TEXT,
  report_test_side TEXT,
  report_body_type TEXT,
  report_engine_transmission TEXT,
  report_test_protocol TEXT,
  report_test_protocol_version TEXT,
  report_speed_target_kmh REAL,
  report_speed_actual_kmh REAL,
  report_overlap_target_pct REAL,
  report_overlap_actual_pct REAL,
  report_wheelbase_cm_manufacturer REAL,
  report_wheelbase_cm_measured REAL,
  report_overall_length_cm_manufacturer REAL,
  report_overall_length_cm_measured REAL,
  report_overall_width_cm_manufacturer REAL,
  report_overall_width_cm_measured REAL,
  report_curb_weight_kg_manufacturer REAL,
  report_curb_weight_kg_measured REAL,
  report_test_weight_kg_measured REAL,
  edr_vendor TEXT,
  edr_vendor_family TEXT,
  edr_case_number TEXT,
  edr_software_version TEXT,
  vehicle_identification_number TEXT,
  classification_confidence REAL,
  classification_method TEXT,
  preview_png_path TEXT,
  notes TEXT,
  FOREIGN KEY(pdf_document_id) REFERENCES pdf_documents(pdf_document_id) ON DELETE CASCADE,
  FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_family_summary (
  family_key TEXT PRIMARY KEY,
  family_label TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  document_count INTEGER NOT NULL,
  locally_available_count INTEGER NOT NULL,
  completed_count INTEGER NOT NULL,
  avg_page_count REAL,
  avg_table_count REAL,
  avg_word_count REAL,
  avg_confidence REAL
);

CREATE TABLE IF NOT EXISTS pdf_metric_coverage (
  family_key TEXT NOT NULL,
  family_label TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  namespace TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  document_count INTEGER NOT NULL,
  available_document_count INTEGER NOT NULL,
  coverage_ratio REAL NOT NULL,
  PRIMARY KEY (family_key, namespace, metric_name)
);

CREATE TABLE IF NOT EXISTS pdf_result_tables (
  pdf_result_table_id INTEGER PRIMARY KEY AUTOINCREMENT,
  pdf_document_id INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  table_order INTEGER NOT NULL,
  table_ref TEXT,
  title TEXT NOT NULL,
  table_type TEXT NOT NULL,
  table_group TEXT NOT NULL,
  extraction_method TEXT NOT NULL,
  header_json TEXT,
  metadata_json TEXT,
  raw_text TEXT,
  raw_table_json TEXT,
  row_count INTEGER NOT NULL DEFAULT 0,
  UNIQUE(pdf_document_id, page_number, table_order),
  FOREIGN KEY(pdf_document_id) REFERENCES pdf_documents(pdf_document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_result_rows (
  pdf_result_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
  pdf_result_table_id INTEGER NOT NULL,
  row_order INTEGER NOT NULL,
  section_name TEXT,
  seat_position TEXT,
  section_key TEXT,
  label TEXT,
  normalized_label TEXT,
  quality_status TEXT,
  quality_score REAL,
  quality_flags TEXT,
  code TEXT,
  unit TEXT,
  threshold_text TEXT,
  threshold_number REAL,
  result_text TEXT,
  result_number REAL,
  time_text TEXT,
  time_number REAL,
  left_text TEXT,
  left_number REAL,
  left_time_text TEXT,
  left_time_number REAL,
  right_text TEXT,
  right_number REAL,
  right_time_text TEXT,
  right_time_number REAL,
  longitudinal_text TEXT,
  longitudinal_number REAL,
  lateral_text TEXT,
  lateral_number REAL,
  vertical_text TEXT,
  vertical_number REAL,
  resultant_text TEXT,
  resultant_number REAL,
  measure_text TEXT,
  measure_number REAL,
  raw_row_json TEXT,
  UNIQUE(pdf_result_table_id, row_order),
  FOREIGN KEY(pdf_result_table_id) REFERENCES pdf_result_tables(pdf_result_table_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_result_table_summary (
  table_type TEXT PRIMARY KEY,
  table_group TEXT NOT NULL,
  document_count INTEGER NOT NULL,
  table_count INTEGER NOT NULL,
  row_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pdf_common_measure_summary (
  table_type TEXT NOT NULL,
  table_group TEXT NOT NULL,
  section_key TEXT NOT NULL DEFAULT '',
  section_label TEXT NOT NULL DEFAULT '',
  normalized_label TEXT NOT NULL,
  display_label TEXT NOT NULL,
  unit TEXT NOT NULL DEFAULT '',
  seat_positions TEXT,
  document_count INTEGER NOT NULL,
  row_count INTEGER NOT NULL,
  sample_test_codes TEXT,
  PRIMARY KEY (table_type, section_key, normalized_label, unit)
);

CREATE VIEW IF NOT EXISTS pdf_result_row_catalog AS
SELECT prr.pdf_result_row_id,
       prr.pdf_result_table_id,
       prt.pdf_document_id,
       pdi.filegroup_id,
       pdi.test_code,
       pdi.title AS document_title,
       pdi.vehicle_year,
       pdi.vehicle_make_model,
       pdi.pdf_role,
       pdi.family_key,
       pdi.family_label,
       pdi.report_test_side,
       pdi.local_path,
       prt.page_number,
       prt.table_order,
       prt.table_ref,
       prt.title AS table_title,
       prt.table_type,
       prt.table_group,
       prr.row_order,
       prr.section_name,
       prr.seat_position,
       prr.section_key,
       prr.label,
       prr.normalized_label,
       prr.quality_status,
       prr.quality_score,
       prr.quality_flags,
       prr.code,
       prr.unit,
       prr.threshold_text,
       prr.threshold_number,
       prr.result_text,
       prr.result_number,
       prr.time_text,
       prr.time_number,
       prr.left_text,
       prr.left_number,
       prr.left_time_text,
       prr.left_time_number,
       prr.right_text,
       prr.right_number,
       prr.right_time_text,
       prr.right_time_number,
       prr.longitudinal_text,
       prr.longitudinal_number,
       prr.lateral_text,
       prr.lateral_number,
       prr.vertical_text,
       prr.vertical_number,
       prr.resultant_text,
       prr.resultant_number,
       prr.measure_text,
       prr.measure_number,
       prr.raw_row_json
  FROM pdf_result_rows prr
  JOIN pdf_result_tables prt ON prt.pdf_result_table_id = prr.pdf_result_table_id
  JOIN pdf_document_inventory pdi ON pdi.pdf_document_id = prt.pdf_document_id;

CREATE TABLE IF NOT EXISTS extracted_metrics (
  extracted_metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
  filegroup_id INTEGER,
  asset_id INTEGER,
  source_type TEXT NOT NULL,
  source_locator TEXT,
  namespace TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  metric_value_text TEXT,
  metric_value_number REAL,
  metric_unit TEXT,
  confidence REAL,
  extraction_method TEXT,
  FOREIGN KEY(filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE,
  FOREIGN KEY(asset_id) REFERENCES assets(asset_id) ON DELETE CASCADE
);

CREATE VIEW IF NOT EXISTS excel_workbook_inventory AS
WITH sheet_summary AS (
  SELECT excel_workbook_id,
         COUNT(*) AS sheet_count,
         COALESCE(SUM(COALESCE(row_count, 0)), 0) AS total_sheet_rows,
         MAX(COALESCE(column_count, 0)) AS max_column_count
    FROM excel_sheets
   GROUP BY excel_workbook_id
),
metric_summary AS (
  SELECT asset_id,
         COUNT(*) AS metric_count,
         COUNT(DISTINCT namespace) AS namespace_count,
         COUNT(DISTINCT namespace || '|' || metric_name || '|' || COALESCE(metric_unit, '')) AS distinct_metric_count,
         ROUND(AVG(confidence), 3) AS avg_confidence
    FROM extracted_metrics
   WHERE source_type = 'excel_workbook'
   GROUP BY asset_id
),
namespace_summary AS (
  SELECT asset_id,
         GROUP_CONCAT(namespace_entry, ', ') AS namespace_counts
    FROM (
      SELECT asset_id,
             namespace || ':' || namespace_metric_count AS namespace_entry
        FROM (
          SELECT asset_id, namespace, COUNT(*) AS namespace_metric_count
            FROM extracted_metrics
           WHERE source_type = 'excel_workbook'
           GROUP BY asset_id, namespace
        )
       ORDER BY asset_id, namespace
    )
   GROUP BY asset_id
)
SELECT ew.excel_workbook_id,
       ew.asset_id,
       ew.filegroup_id,
       fg.test_code,
       fg.title AS filegroup_title,
       fg.tested_on,
       tt.test_type_label,
       v.vehicle_year,
       v.vehicle_make_model,
       ew.workbook_type,
       ew.extraction_status,
       ew.notes,
       a.filename,
       a.local_path,
       a.relative_path,
       a.folder_path,
       COALESCE(ss.sheet_count, 0) AS sheet_count,
       COALESCE(ss.total_sheet_rows, 0) AS total_sheet_rows,
       COALESCE(ss.max_column_count, 0) AS max_column_count,
       COALESCE(ms.metric_count, 0) AS metric_count,
       COALESCE(ms.namespace_count, 0) AS namespace_count,
       COALESCE(ms.distinct_metric_count, 0) AS distinct_metric_count,
       ms.avg_confidence,
       ns.namespace_counts
  FROM excel_workbooks ew
  JOIN assets a ON a.asset_id = ew.asset_id
  JOIN filegroups fg ON fg.filegroup_id = ew.filegroup_id
  LEFT JOIN test_types tt ON tt.test_type_code = fg.test_type_code
  LEFT JOIN vehicles v ON v.vehicle_id = fg.vehicle_id
  LEFT JOIN sheet_summary ss ON ss.excel_workbook_id = ew.excel_workbook_id
  LEFT JOIN metric_summary ms ON ms.asset_id = ew.asset_id
  LEFT JOIN namespace_summary ns ON ns.asset_id = ew.asset_id;

CREATE VIEW IF NOT EXISTS excel_metric_catalog AS
SELECT em.extracted_metric_id,
       ew.excel_workbook_id,
       ew.asset_id,
       ew.filegroup_id,
       fg.test_code,
       fg.title AS filegroup_title,
       fg.tested_on,
       tt.test_type_label,
       v.vehicle_year,
       v.vehicle_make_model,
       ew.workbook_type,
       ew.extraction_status,
       a.filename,
       a.local_path,
       a.relative_path,
       a.folder_path,
       CASE
         WHEN em.source_locator LIKE 'sheet:%' THEN
           CASE
             WHEN instr(substr(em.source_locator, 7), '|') > 0 THEN substr(substr(em.source_locator, 7), 1, instr(substr(em.source_locator, 7), '|') - 1)
             ELSE substr(em.source_locator, 7)
           END
         ELSE ''
       END AS sheet_name,
       em.source_locator,
       em.namespace,
       em.metric_name,
       em.metric_value_text,
       em.metric_value_number,
       em.metric_unit,
       em.confidence,
       em.extraction_method
  FROM extracted_metrics em
  JOIN excel_workbooks ew ON ew.asset_id = em.asset_id
  JOIN assets a ON a.asset_id = ew.asset_id
  JOIN filegroups fg ON fg.filegroup_id = ew.filegroup_id
  LEFT JOIN test_types tt ON tt.test_type_code = fg.test_type_code
  LEFT JOIN vehicles v ON v.vehicle_id = fg.vehicle_id
 WHERE em.source_type = 'excel_workbook';

CREATE VIEW IF NOT EXISTS excel_metric_summary AS
WITH metric_base AS (
  SELECT excel_workbook_id,
         filegroup_id,
         test_code,
         workbook_type,
         namespace,
         metric_name,
         COALESCE(metric_unit, '') AS metric_unit,
         metric_value_number,
         confidence
    FROM excel_metric_catalog
),
sample_codes AS (
  SELECT workbook_type,
         namespace,
         metric_name,
         metric_unit,
         GROUP_CONCAT(test_code, ', ') AS sample_test_codes
    FROM (
      SELECT DISTINCT workbook_type, namespace, metric_name, metric_unit, test_code
        FROM metric_base
       ORDER BY workbook_type, namespace, metric_name, metric_unit, test_code
    )
   GROUP BY workbook_type, namespace, metric_name, metric_unit
)
SELECT mb.workbook_type,
       mb.namespace,
       mb.metric_name,
       mb.metric_unit,
       COUNT(*) AS metric_count,
       COUNT(DISTINCT mb.excel_workbook_id) AS workbook_count,
       COUNT(DISTINCT mb.filegroup_id) AS filegroup_count,
       COUNT(mb.metric_value_number) AS numeric_value_count,
       ROUND(AVG(mb.confidence), 3) AS avg_confidence,
       ROUND(MIN(mb.metric_value_number), 3) AS min_value_number,
       ROUND(MAX(mb.metric_value_number), 3) AS max_value_number,
       sc.sample_test_codes
  FROM metric_base mb
  LEFT JOIN sample_codes sc
    ON sc.workbook_type = mb.workbook_type
   AND sc.namespace = mb.namespace
   AND sc.metric_name = mb.metric_name
   AND sc.metric_unit = mb.metric_unit
 GROUP BY mb.workbook_type, mb.namespace, mb.metric_name, mb.metric_unit, sc.sample_test_codes;

CREATE INDEX IF NOT EXISTS idx_filegroups_test_type ON filegroups(test_type_code);
CREATE INDEX IF NOT EXISTS idx_filegroups_vehicle ON filegroups(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_assets_filegroup ON assets(filegroup_id);
CREATE INDEX IF NOT EXISTS idx_assets_extension ON assets(file_extension);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_sensor_channels_filegroup ON sensor_channels(filegroup_id);
CREATE INDEX IF NOT EXISTS idx_sensor_channels_iso ON sensor_channels(iso_code);
CREATE INDEX IF NOT EXISTS idx_signal_containers_type ON signal_containers(container_type);
CREATE INDEX IF NOT EXISTS idx_preprocessing_cases_filegroup ON preprocessing_cases(filegroup_id);
CREATE INDEX IF NOT EXISTS idx_preprocessing_cases_mode ON preprocessing_cases(mode);
CREATE INDEX IF NOT EXISTS idx_preprocessing_series_case ON preprocessing_series(preprocessing_case_id);
CREATE INDEX IF NOT EXISTS idx_preprocessing_feature_sets_case ON preprocessing_feature_sets(preprocessing_case_id);
CREATE INDEX IF NOT EXISTS idx_preprocessing_feature_sets_filegroup ON preprocessing_feature_sets(filegroup_id);
CREATE INDEX IF NOT EXISTS idx_preprocessing_feature_values_set ON preprocessing_feature_values(preprocessing_feature_set_id);
CREATE INDEX IF NOT EXISTS idx_preprocessing_neighbors_source ON preprocessing_neighbors(source_feature_set_id);
CREATE INDEX IF NOT EXISTS idx_preprocessing_clusters_set ON preprocessing_clusters(preprocessing_feature_set_id);
CREATE INDEX IF NOT EXISTS idx_preprocessing_representatives_set ON preprocessing_representatives(preprocessing_feature_set_id);
CREATE INDEX IF NOT EXISTS idx_pdf_documents_filegroup ON pdf_documents(filegroup_id);
CREATE INDEX IF NOT EXISTS idx_pdf_layout_assignments_family ON pdf_layout_assignments(family_key);
CREATE INDEX IF NOT EXISTS idx_pdf_document_inventory_role ON pdf_document_inventory(pdf_role);
CREATE INDEX IF NOT EXISTS idx_pdf_document_inventory_family ON pdf_document_inventory(family_key);
CREATE INDEX IF NOT EXISTS idx_pdf_document_inventory_test_code ON pdf_document_inventory(test_code);
CREATE INDEX IF NOT EXISTS idx_pdf_result_tables_document ON pdf_result_tables(pdf_document_id, page_number);
CREATE INDEX IF NOT EXISTS idx_pdf_result_tables_type ON pdf_result_tables(table_type);
CREATE INDEX IF NOT EXISTS idx_pdf_result_rows_table ON pdf_result_rows(pdf_result_table_id, row_order);
CREATE INDEX IF NOT EXISTS idx_pdf_result_rows_label ON pdf_result_rows(normalized_label, section_key);
CREATE INDEX IF NOT EXISTS idx_pdf_common_measure_summary_type ON pdf_common_measure_summary(table_type, document_count);
CREATE INDEX IF NOT EXISTS idx_excel_workbooks_filegroup ON excel_workbooks(filegroup_id);
CREATE INDEX IF NOT EXISTS idx_excel_workbooks_type_status ON excel_workbooks(workbook_type, extraction_status);
CREATE INDEX IF NOT EXISTS idx_extracted_metrics_source_asset ON extracted_metrics(source_type, asset_id);
CREATE INDEX IF NOT EXISTS idx_extracted_metrics_source_namespace_metric ON extracted_metrics(source_type, namespace, metric_name);
