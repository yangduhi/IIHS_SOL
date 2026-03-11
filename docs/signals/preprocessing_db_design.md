# Preprocessing DB Design

This document defines the current three-mode preprocessing layout and the fixed-window harmonized layer for the IIHS small overlap corpus.

## Scope

- Source of truth for raw signal inventory remains `signal_containers` and `signal_series`.
- Preprocessed outputs are stored as Parquet under `data/derived/small_overlap/preprocessed_signals`.
- SQLite stores catalog metadata, not waveform blobs.
- Advanced feature outputs are stored in SQLite plus summary tables under `output/small_overlap/tables`.

## Modes

### `standard_baseline`

- Applies baseline subtraction using the IIHS `-50 ms` to `-40 ms` pre-impact window.
- Preserves the native TDMS time basis.
- Acts as the canonical research mode.

### `strict_origin`

- Starts from `standard_baseline`.
- Crops at the first native sample at or after official time zero.
- Subtracts the channel value at the crop sample so each channel starts at `(0, 0)`.

### `exploratory_t0`

- Starts from `standard_baseline`.
- Detects `T0` from vehicle longitudinal acceleration using anchor/backtrack logic.
- Crops at detected `T0`.
- Subtracts the channel value at `T0` so each channel starts at `(0, 0)`.

## Harmonized Layer

- Fixed window: default `0.0 s` to `0.25 s`
- Fixed sample rate: default `10 kHz`
- Fixed sample count: `2501`
- Interpolation policy: linear only
- Out-of-range policy: `NaN` padding

The harmonized layer is for model-ready comparison matrices. It is not the canonical source of signal truth.

## DB Tables

### `preprocessing_runs`

- One row per batch execution.
- Tracks parser version, scope, start/end timestamps, and run summary notes.

### `preprocessing_cases`

- One row per `filegroup_id + mode`.
- Stores output paths, reference method, reference time, native/harmonized sample counts, and mode metrics.

### `preprocessing_series`

- One row per `preprocessing_case + standard_name`.
- Stores source channel provenance and native/harmonized summary stats.

### `preprocessing_feature_runs`

- One row per feature/clustering/similarity batch execution.
- Tracks feature parser version, source preprocessing mode, feature space, and summary notes.

### `preprocessing_feature_sets`

- One row per `preprocessing_case + feature_space`.
- Stores the flattened explainable feature vector and per-channel coverage for clustering and matching.

### `preprocessing_feature_values`

- One row per `feature_set + standard_name + feature_name`.
- Stores explainable metrics such as peak, peak time, area, energy proxy, rise time,
  onset/rebound/settle landmarks, and derived-signal summaries.

### `preprocessing_neighbors`

- Top-k neighbor graph for each source case.
- Stores hybrid similarity score plus weighted correlation, DTW distance,
  multiview similarity, and per-view phase similarity diagnostics.

### `preprocessing_clusters`

- One row per feature set with cluster assignment, centroid distance, robust outlier score,
  local-density outlier score, stability score, and coverage score.

### `preprocessing_representatives`

- Stores cluster-centroid, cluster-boundary, cluster-stable, cluster-high-coverage,
  and global-centroid representative cases for benchmark set construction.

## Scripts

### Single case

```powershell
python scripts/preprocess_known_signal_families.py --filegroup-id 7168 --register-db
```

### Full TDMS standard, single case

```powershell
python scripts/preprocess_tdms_full_standard.py --filegroup-id 7168
```

### Batch

```powershell
python scripts/run_preprocessing_batch.py --limit 25
```

### Feature batch

```powershell
python scripts/build_signal_feature_batch.py
```

### Query similar cases

```powershell
python scripts/query_signal_similarity.py --filegroup-id 7168 --top-k 5
```

### Compliance audit and ETL monitor

```powershell
python scripts/build_signal_operations_audit.py
```

### ML dataset export

```powershell
python scripts/export_signal_ml_dataset.py
```

### Reproducibility bundle

```powershell
python scripts/restore_signal_case_bundle.py --filegroup-id 7168 --mode standard_baseline
```

### Automated case report

```powershell
python scripts/generate_signal_case_report.py --filegroup-id 7168
```

### Full TDMS standard, 400 longitudinal-capable TDMS filegroups

```powershell
python scripts/run_full_tdms_standard_batch.py
```

### Explicit filegroups

```powershell
python scripts/run_preprocessing_batch.py --filegroup-id 7168 --filegroup-id 1602
```

## Current Kia Seltos Validation

- `filegroup_id=7168`
- `test_code=CEN2005`
- `standard_baseline` native sample count: `6000`
- `strict_origin` native sample count: `5000`
- `exploratory_t0` native sample count: `5000`
- All harmonized outputs: `2501` samples

## Full TDMS Standard Snapshot

- Scope: `400` TDMS filegroups with vehicle longitudinal `ACX*` support
- Output root: `data/derived/small_overlap/preprocessed_signals_full_tdms`
- Native wide output only, plus `harmonized_wide`
- Summary table: `output/small_overlap/tables/full_tdms_standard_summary.csv`

## Feature Batch Snapshot

- Source mode: `standard_baseline`
- Feature space: `official_known_harmonized_v3`
- Feature sets: `406`
- Feature values: `216,804`
- Neighbor rows: `4,060`
- Cluster count: `2`
- Outlier count: `7`
- Representative rows: `34`
- Cluster sizes:
  - `cluster 0`: `37`
  - `cluster 1`: `369`
- Upgrades over `v2`:
  - landmark-aware shape features including `onset_time_abs`, `settle_time_abs`,
    `onset_to_peak_s`, `peak_to_rebound_s`, `peak_to_settle_s`
  - phase-aware similarity across `build`, `rebound`, `settle`
  - cross-channel lag features from vehicle pulse to seat/foot response
  - derived physics channels including `jerk`, `delta_v`, and deflection `rate`
  - multiview similarity with separate `pulse`, `occupant`, `lower_extremity` views
  - local-density outlier scoring and expanded representative set
  - weighted hybrid neighbor search `hybrid_similarity_v3`
  - medoid-based multiview clustering `kmedoids_multiview_v3`
- Representative kinds:
  - `cluster_centroid`: `6`
  - `cluster_boundary`: `6`
  - `cluster_stable`: `6`
  - `cluster_high_coverage`: `6`
  - `global_centroid`: `10`
- Reports:
  - `output/small_overlap/tables/signal_feature_neighbors__standard_baseline__official_known_harmonized_v3.csv`
  - `output/small_overlap/tables/signal_feature_clusters__standard_baseline__official_known_harmonized_v3.csv`
  - `output/small_overlap/tables/signal_feature_representatives__standard_baseline__official_known_harmonized_v3.csv`
  - `output/small_overlap/tables/signal_feature_summary__standard_baseline__official_known_harmonized_v3.json`

## Operations Snapshot

- Compliance audit:
  - `output/small_overlap/tables/signal_preprocessing_audit.csv`
  - `output/small_overlap/tables/signal_preprocessing_audit.json`
- ETL monitor:
  - `output/small_overlap/tables/signal_etl_monitor.csv`
  - `output/small_overlap/tables/signal_etl_monitor.json`
- Current summary:
  - TDMS done cases: `406`
  - `standard_baseline done`: `406`
  - `strict_origin done`: `406`
  - `exploratory_t0 done`: `398`
  - `exploratory_t0 unavailable`: `8`
  - `standard_baseline_full_tdms done`: `400`

## ML Snapshot

- Dataset tensor:
  - `output/small_overlap/ml/signal_ml_dataset__standard_baseline.npz`
- Metadata:
  - `output/small_overlap/ml/signal_ml_dataset__standard_baseline__cases.csv`
  - `output/small_overlap/ml/signal_ml_dataset__standard_baseline__summary.json`
- Shape: `406 x 10 x 2501`

## Reproducibility Snapshot

- Example restore bundle:
  - `output/small_overlap/restore_bundles/7168-CEN2005__standard_baseline/restore_bundle.json`
- Copied artifacts include manifest, native wide/long, and harmonized wide/long Parquet outputs.

## Automated Report Snapshot

- Example report:
  - `output/small_overlap/reports/7168-CEN2005__standard_baseline/index.html`
- Example plots:
  - `output/small_overlap/reports/7168-CEN2005__standard_baseline/comparison_overlay.png`
  - `output/small_overlap/reports/7168-CEN2005__standard_baseline/cluster_representatives.png`
- Report highlights:
  - v3 neighbor table includes multiview and pulse-phase diagnostics
  - cluster diagnostics include robust distance, local density, stability, and coverage
  - representative table lists representative kind as well as rank and score
