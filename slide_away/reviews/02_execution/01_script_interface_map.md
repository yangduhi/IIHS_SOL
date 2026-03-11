# Slide Away Script Interface Map

- Date: `2026-03-11`
- Status: `closed`

## Standard Interface

| Planned script | Wrapper path | Execution module | Phase |
| --- | --- | --- | --- |
| `build_case_master.py` | `scripts/build_case_master.py` | `scripts/tools/slide_away/build_case_master.py` | 1 |
| `build_outcome_mart.py` | `scripts/build_outcome_mart.py` | `scripts/tools/slide_away/build_outcome_mart.py` | 2 |
| `build_barrier_relative_features.py` | `scripts/build_barrier_relative_features.py` | `scripts/tools/slide_away/build_barrier_relative_features.py` | 3 |
| `run_window_sweep.py` | `scripts/run_window_sweep.py` | `scripts/tools/slide_away/run_window_sweep.py` | 4 |
| `run_mode_study.py` | `scripts/run_mode_study.py` | `scripts/tools/slide_away/run_mode_study.py` | 5 |
| `build_ri_safety_map.py` | `scripts/build_ri_safety_map.py` | `scripts/tools/slide_away/build_ri_safety_map.py` | 6 |
| `build_mode_casebook.py` | `scripts/build_mode_casebook.py` | `scripts/tools/slide_away/build_mode_casebook.py` | 7 |

## Supporting Modules

- `scripts/tools/slide_away/common.py`
  - path constants
  - `signal_ready_flag` rule
  - barrier-relative signal metrics
  - safety severity helper
- `scripts/tools/slide_away/modeling.py`
  - window feature selection
  - clustering
  - centroid distance helper

## Review Support Scripts

| Review script | Wrapper path | Execution module | Purpose |
| --- | --- | --- | --- |
| `review_window_candidates.py` | `scripts/review_window_candidates.py` | `scripts/tools/slide_away/review_window_candidates.py` | compare `100 ms` vs historic `0-150 ms` |
| `review_minor_cluster.py` | `scripts/review_minor_cluster.py` | `scripts/tools/slide_away/review_minor_cluster.py` | profile the `6`-case minor cluster and confounding |
| `review_extended_linkage.py` | `scripts/review_extended_linkage.py` | `scripts/tools/slide_away/review_extended_linkage.py` | extend linkage beyond RI-only correlation |
| `review_domain_outcome_linkage.py` | `scripts/review_domain_outcome_linkage.py` | `scripts/tools/slide_away/review_domain_outcome_linkage.py` | split linkage across outcome domains |
| `review_preregistered_lower_ext_subgroups.py` | `scripts/review_preregistered_lower_ext_subgroups.py` | `scripts/tools/slide_away/review_preregistered_lower_ext_subgroups.py` | rerun lower-ext subgroup checks under fixed reviewer rules |
| `review_mode_confounding.py` | `scripts/review_mode_confounding.py` | `scripts/tools/slide_away/review_mode_confounding.py` | produce side, era, family, and weight confounding sign-off |
| `review_approval_logic.py` | `scripts/review_approval_logic.py` | `scripts/tools/slide_away/review_approval_logic.py` | compare pooled versus domain-aware approval logic |
| `review_observation_flavored_naming.py` | `scripts/review_observation_flavored_naming.py` | `scripts/tools/slide_away/review_observation_flavored_naming.py` | keep naming conservative and observation-based |

## Executed Commands

```powershell
python scripts/build_case_master.py
python scripts/build_outcome_mart.py
python scripts/build_barrier_relative_features.py --mode standard_baseline
python scripts/build_barrier_relative_features.py --mode strict_origin
python scripts/run_window_sweep.py
python scripts/run_mode_study.py --window 0.10
python scripts/build_ri_safety_map.py
python scripts/build_mode_casebook.py
python scripts/review_window_candidates.py
python scripts/review_minor_cluster.py
python scripts/review_extended_linkage.py
python scripts/review_domain_outcome_linkage.py
python scripts/review_preregistered_lower_ext_subgroups.py
python scripts/review_mode_confounding.py
python scripts/review_approval_logic.py
python scripts/review_observation_flavored_naming.py
```

## Closure Notes

- `signal_ready_flag` is sourced from `preprocessing_cases`, not filesystem inference.
- Outcome ETL is anchored on `pdf_result_row_catalog` at `filegroup_id` grain.
- Barrier-relative feature ETL is anchored on `harmonized_wide.parquet` from `preprocessing_cases`.
- Barrier-relative feature ETL now includes `x/y/z` plus resultant harshness metrics for downstream review.
- All required wrapper paths now exist and execute in this repository snapshot.
- Review support scripts now exist for blocker-reduction work after the initial package build.
