from __future__ import annotations

import sqlite3


EXCEL_CATALOG_SQL = """
CREATE INDEX IF NOT EXISTS idx_excel_workbooks_type_status ON excel_workbooks(workbook_type, extraction_status);
CREATE INDEX IF NOT EXISTS idx_extracted_metrics_source_asset ON extracted_metrics(source_type, asset_id);
CREATE INDEX IF NOT EXISTS idx_extracted_metrics_source_namespace_metric ON extracted_metrics(source_type, namespace, metric_name);

DROP VIEW IF EXISTS excel_metric_summary;
DROP VIEW IF EXISTS excel_metric_catalog;
DROP VIEW IF EXISTS excel_workbook_inventory;

CREATE VIEW excel_workbook_inventory AS
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

CREATE VIEW excel_metric_catalog AS
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

CREATE VIEW excel_metric_summary AS
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
"""


def ensure_excel_catalog_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(EXCEL_CATALOG_SQL)
