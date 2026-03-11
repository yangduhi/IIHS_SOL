# Core Pipeline Docs

This folder contains the documents for the mandatory project pipeline.

Core axes:
- `acquisition`: discovery and download inventory
- `metadata`: analysis-side CSV and DTS extraction
- `catalog`: research database schema and loading order
- `documents`: Excel and PDF ETL
- `signals`: TDMS export and signal preprocessing

Verified database snapshot on 2026-03-11:
- `filegroups`: 413
- `assets`: 24943
- `signal_containers`: 20192
- `signal_series`: 58915
- `excel_workbooks`: 1851
- `excel_sheets`: 16970
- `pdf_documents`: 472
- `pdf_pages`: 5361
- `pdf_page_features`: 5361
- `pdf_layout_assignments`: 785
- `extracted_metrics`: 216506

Recommended reading order:
1. `database-build-playbook.md`
2. `research-database-architecture.md`
3. `dataset-analysis-guide.md`

Signal-specific references live in `../signals/`.
Operational notes live in `../ops/`.
