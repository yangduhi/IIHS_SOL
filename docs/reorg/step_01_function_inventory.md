# Step 01. Function Inventory

## Core Pipeline

### Acquisition
- Purpose: discover IIHS small-overlap filegroups and download source assets
- Runtime entrypoints:
  - `scripts/discover-small-overlap.mjs`
  - `scripts/download-filegroup.mjs`
  - `scripts/lib/db.mjs`
  - `scripts/lib/iihs-techdata.mjs`
  - `scripts/lib/logging.mjs`
- Primary outputs:
  - `data/index/manifest.sqlite`
  - `data/raw/...`
  - `output/playwright/...`

### Metadata
- Purpose: build analysis-side CSV and JSON metadata from downloaded assets
- Runtime entrypoints:
  - `scripts/extract_dataset_metadata.py`
- Primary outputs:
  - `data/analysis/*.csv`
  - `data/analysis/dataset_overview.json`

### Catalog
- Purpose: assemble the research SQLite database from discovery and metadata outputs
- Runtime entrypoints:
  - `scripts/init_research_database.py`
  - `scripts/excel_catalog_schema.py`
  - `sql/research_database.sql`
- Primary outputs:
  - `data/research/research.sqlite`

### Documents
- Purpose: run Excel and PDF ETL into the research database
- Runtime entrypoints:
  - `scripts/process_excels.py`
  - `scripts/rebuild_excel_pipeline.py`
  - `scripts/process_pdfs.py`

### Signals
- Purpose: export TDMS data, standardize signal families, and build preprocessing artifacts
- Runtime entrypoints:
  - `scripts/export_signal_parquet.py`
  - `scripts/preprocess_known_signal_families.py`
  - `scripts/preprocess_tdms_full_standard.py`
  - `scripts/run_preprocessing_batch.py`
  - `scripts/run_full_tdms_standard_batch.py`

## Higher-Level Tools

### Dashboards
- `scripts/build_excel_dashboard.py`
- `scripts/build_pdf_dashboard.py`
- `scripts/build_signal_catalog_dashboard.py`
- `scripts/build_signal_dashboard.py`
- `scripts/plot_preprocessed_signals.py`

### Exports
- `scripts/export_excel_catalog.py`
- `scripts/export_pdf_result_catalog.py`
- `scripts/export_pdf_result_rows.py`
- `scripts/export_signal_ml_dataset.py`
- `scripts/rebuild_excel_catalog.py`
- `scripts/rebuild_pdf_catalog.py`

### Analytics
- `scripts/build_signal_feature_batch.py`
- `scripts/build_signal_feature_batch_moment.py`
- `scripts/build_signal_operations_audit.py`
- `scripts/generate_signal_case_report.py`
- `scripts/query_signal_similarity.py`
- `scripts/restore_signal_case_bundle.py`

### Bootstrap
- `scripts/capture-session.ps1`

## Legacy

- `scripts/build_signal_moment_batch.py`
  - Reason: older MOMENT-based batch path with partially fixed settings and weaker fit than the newer feature-batch tooling
