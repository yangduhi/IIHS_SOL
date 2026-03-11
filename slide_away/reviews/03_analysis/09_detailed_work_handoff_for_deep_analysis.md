# Slide Away Detailed Work Handoff For Deep Analysis

- Date: `2026-03-11`
- Status: `active handoff`
- Current approval state: `hold`
- Intended reader: the next analyst who will continue deep analysis, challenge current assumptions, or redesign the final mode taxonomy

## 1. Executive Summary

This repository snapshot is no longer an idea-stage study.
It is now a reproducible research package with executable ETL, feature engineering, clustering, review artifacts, and follow-up linkage analysis.

The strongest current interpretation is:

- the package is operational and reproducible
- `RI` alone is weak as a pooled approval signal
- linkage improves when `harshness` and `seat-response` context is added
- the strongest current domain is `lower-extremity`, not a pooled redirection axis
- the current evidence does not justify final `redirection-dominant` / `crush-dominant` operating names
- approval remains `hold` because mode standardization is still unresolved

## 2. Recommended Reading Order

Read the `reviews` folder in this order:

1. `reviews/01_governance/01_final_review.md`
2. `reviews/01_governance/02_next_step_plan.md`
3. `reviews/02_execution/01_script_interface_map.md`
4. `reviews/02_execution/02_phase_execution_summary.md`
5. `reviews/03_analysis/03_window_candidate_review.md`
6. `reviews/03_analysis/04_minor_cluster_review.md`
7. `reviews/03_analysis/05_extended_linkage_review.md`
8. `reviews/03_analysis/07_domain_outcome_linkage_review.md`
9. `reviews/03_analysis/09_detailed_work_handoff_for_deep_analysis.md`
10. `reviews/03_analysis/10_xyz_primary_frame_note.md`
11. `reviews/03_analysis/11_preregistered_lower_ext_subgroup_validation.md`
12. `reviews/03_analysis/12_mode_confounding_signoff.md`
13. `reviews/03_analysis/13_domain_approval_logic_review.md`
14. `reviews/03_analysis/14_observation_flavored_naming_review.md`
15. `reviews/04_casebooks/01_matched_pair_casebook.md`

The review folder index is:

- `reviews/README.md`

## 3. Core Study Frame

The `slide_away` study is currently framed as:

- unit of analysis: `filegroup_id`
- primary mode: `standard_baseline`
- sensitivity mode: `strict_origin`
- first stable baseline cohort: `driver-only`
- passenger data is allowed only after barrier-relative sign harmonization
- primary window history:
  - historic operating baseline: `0-150 ms`
  - current best candidate from window sweep: `100 ms`
- robustness window: `0-250 ms`

Key physical frame:

- driver side uses `a_y_away = +a_y`
- passenger side uses `a_y_away = -a_y`
- `RI` is defined from barrier-relative lateral versus longitudinal delta-V
- occupant-compartment `x/y/z` acceleration is the primary physical reading layer:
  - `x`: ride-down and longitudinal pulse
  - `y`: barrier-relative lateralization and redirection
  - `z`: vertical harshness and wheel or suspension path response
- current interpretation is no longer "RI should dominate"
- current interpretation is "RI is one component inside a multiaxis linkage stack"
- current interpretation is not "x/y/z alone is sufficient"
- current interpretation is "x/y/z is the leading explanatory layer, then seat or foot or compartment response, then domain outcomes"

Three-layer analysis frame:

- `Level 1`: vehicle kinematics and pulse
  - `x/y/z` acceleration, delta-V, RI, timing, pulse duration
- `Level 2`: compartment and occupant-response context
  - seat twist, foot asymmetry, lower-ext proxies, restraint timing proxies
- `Level 3`: approval and outcome evidence
  - intrusion, lower-extremity, restraint/kinematics, head-neck-chest

## 4. Source Data And Dependency Structure

Primary inputs:

- `data/research/research.sqlite`
- `output/small_overlap/tables/canonical_small_overlap_tests.csv`
- `data/derived/small_overlap/preprocessed_signals`
- `docs/signals/preprocessing_db_design.md`

Important database tables used directly:

- `preprocessing_cases`
  - used to reproduce `signal_ready_flag`
- `pdf_result_row_catalog`
  - used as the main outcome ETL source
- PDF families used in outcome ETL:
  - `intrusion`
  - `leg_foot_injury`
  - `restraint_kinematics`
  - `head_injury`
  - `chest_injury`
  - `neck_injury`
  - `thigh_hip_injury`
  - `dummy_clearance`

## 5. Current Review And Analysis Folder Structure

Ordered review structure:

- `slide_away/reviews/01_governance`
  - approval state, final review, next-step plan
- `slide_away/reviews/02_execution`
  - script interface closure, phase execution summary
- `slide_away/reviews/03_analysis`
  - analysis memos, linkage memos, mode review, detailed handoff
- `slide_away/reviews/04_casebooks`
  - matched-pair casebook and structural codebook

Artifact structure:

- `slide_away/artifacts/marts`
  - parquet marts
- `slide_away/artifacts/tables`
  - tabular outputs for clustering, linkage, confounding, and review
- `slide_away/artifacts/figures`
  - summary figures
- `slide_away/artifacts/logs`
  - execution logs

## 6. Pipeline Overview

The implemented workflow is:

1. build `case_master`
2. build `outcomes_v1`
3. build `features_v1` and `features_v1_strict_origin`
4. run `window_sweep`
5. run `mode_study`
6. build `ri_vs_safety_map`
7. build `matched_pair_casebook`
8. run blocker-reduction reviews
   - `window candidate review`
   - `minor cluster review`
   - `extended linkage review`
   - `domain outcome linkage review`

Main wrapper entrypoints:

- `scripts/build_case_master.py`
- `scripts/build_outcome_mart.py`
- `scripts/build_barrier_relative_features.py`
- `scripts/run_window_sweep.py`
- `scripts/run_mode_study.py`
- `scripts/build_ri_safety_map.py`
- `scripts/build_mode_casebook.py`
- `scripts/review_window_candidates.py`
- `scripts/review_minor_cluster.py`
- `scripts/review_extended_linkage.py`
- `scripts/review_domain_outcome_linkage.py`

Main implementation modules:

- `scripts/tools/slide_away/common.py`
- `scripts/tools/slide_away/modeling.py`
- `scripts/tools/slide_away/build_case_master.py`
- `scripts/tools/slide_away/build_outcome_mart.py`
- `scripts/tools/slide_away/build_barrier_relative_features.py`
- `scripts/tools/slide_away/run_window_sweep.py`
- `scripts/tools/slide_away/run_mode_study.py`
- `scripts/tools/slide_away/build_ri_safety_map.py`
- `scripts/tools/slide_away/build_mode_casebook.py`
- `scripts/tools/slide_away/review_window_candidates.py`
- `scripts/tools/slide_away/review_minor_cluster.py`
- `scripts/tools/slide_away/review_extended_linkage.py`
- `scripts/tools/slide_away/review_domain_outcome_linkage.py`

## 7. Implemented Data Structures

### 7.1 `case_master.parquet`

Path:

- `slide_away/artifacts/marts/case_master.parquet`

Observed shape:

- rows: `413`
- columns: `78`

Key column groups:

- identity:
  - `filegroup_id`
  - `vehicle_id`
  - `test_code`
  - `title`
- metadata:
  - `vehicle_year`
  - `vehicle_make_model`
  - `test_side`
  - `tested_on`
  - `era`
  - `make_model_family`
  - `analysis_cohort`
- asset coverage:
  - `pdf_asset_count`
  - `workbook_asset_count`
  - `signalish_asset_count`
  - `pdf_document_count`
  - `excel_workbook_count`
  - `signal_container_count`
- extracted report fields:
  - `report_speed_actual_kmh`
  - `report_speed_target_kmh`
  - `report_overlap_actual_pct`
  - `report_overlap_target_pct`
  - `report_curb_weight_kg_measured`
  - `report_test_weight_kg_measured`
- pipeline flags:
  - `signal_ready_flag`
  - `strict_origin_ready_flag`
  - `pdf_available_flag`
  - `excel_available_flag`
  - `vin_conflict_flag`
- provenance:
  - `standard_preprocessing_case_id`
  - `strict_preprocessing_case_id`
  - `signal_ready_rule`
  - `case_master_version`
  - `generated_at`

### 7.2 `outcomes_v1.parquet`

Path:

- `slide_away/artifacts/marts/outcomes_v1.parquet`

Observed shape:

- rows: `413`
- columns: `27`

Key outcome columns:

- structure:
  - `intrusion_max_resultant_cm`
  - `intrusion_footrest_resultant_cm`
  - `intrusion_left_toepan_resultant_cm`
  - `intrusion_brake_pedal_resultant_cm`
- lower-extremity:
  - `leg_foot_index_left`
  - `leg_foot_index_right`
  - `foot_resultant_accel_left_g`
  - `foot_resultant_accel_right_g`
  - `thigh_hip_risk_proxy`
- restraint/kinematics:
  - `restraint_event_count`
  - `pretensioner_time_ms`
  - `airbag_first_contact_time_ms`
  - `airbag_full_inflation_time_ms`
- injury:
  - `head_hic15`
  - `chest_rib_compression_mm`
  - `chest_viscous_criteria_ms`
  - `neck_tension_extension_nij`
- clearance:
  - `dummy_clearance_head_to_roof_mm`
  - `dummy_clearance_knee_to_dash_left_mm`
  - `dummy_clearance_knee_to_dash_right_mm`
  - `dummy_clearance_min_mm`
- QA/provenance:
  - `outcome_quality_score`
  - `outcome_source_version`
  - `outcome_provenance_json`

### 7.3 `features_v1.parquet`

Path:

- `slide_away/artifacts/marts/features_v1.parquet`

Observed shape:

- rows: `406`
- columns: `162`

Feature structure:

- base identity:
  - `filegroup_id`
  - `preprocessing_case_id`
  - `source_mode`
  - `test_code`
  - `test_side`
  - `era`
  - `make_model_family`
  - `analysis_cohort`
- baseline feature set:
  - `delta_vx_mps`
  - `delta_vy_away_mps`
  - `lr`
  - `lr_100`
  - `ly`
  - `ly_40`
  - `ly_60`
  - `ri`
  - `ri_60`
  - `t_peak_x_ms`
  - `t_peak_y_ms`
  - `t_50_dvx_ms`
  - `max_abs_ax_g`
  - `max_abs_ay_g`
  - `pulse_duration_x_ms`
  - `pulse_duration_y_ms`
  - `seat_twist_peak_mm`
  - `foot_resultant_left_g`
  - `foot_resultant_right_g`
  - `foot_resultant_asymmetry_g`
  - `foot_x_left_right_diff_g`
  - `foot_z_left_right_diff_g`
  - seat/foot lag features
- multiwindow columns:
  - `window_020_*`
  - `window_040_*`
  - `window_060_*`
  - `window_080_*`
  - `window_100_*`
  - `window_120_*`
  - `window_150_*`
  - `window_250_*`
- QA:
  - `cluster_input_flag`
  - `feature_quality_score`
  - `feature_version`

### 7.4 `features_v1_strict_origin.parquet`

Path:

- `slide_away/artifacts/marts/features_v1_strict_origin.parquet`

Observed shape:

- rows: `406`
- columns: `162`

Role:

- sensitivity copy of the feature mart using `strict_origin`
- not used as the current operating mart

### 7.5 `mode_case_assignments.csv`

Path:

- `slide_away/artifacts/tables/mode_case_assignments.csv`

Observed shape:

- rows: `398`
- columns: `165`

Role:

- clustering-ready subset
- contains imputed window feature columns for the selected clustering run
- adds:
  - `cluster_id`
  - `working_mode_label`
  - `exploratory_interpretation`

### 7.6 Window / Mode Summary Tables

- `slide_away/artifacts/tables/window_sweep_summary.csv`
  - rows: `8`
  - columns:
    - `window_ms`
    - `best_k`
    - `sample_count`
    - `silhouette`
    - `size_ratio`
    - `outcome_eta_sq`
    - `composite_score`
    - `candidate_scores_json`
    - `selected_operating_window`
    - `selected_robustness_window`

- `slide_away/artifacts/tables/mode_study_summary.csv`
  - rows: `3`
  - columns:
    - `k`
    - `sample_count`
    - `silhouette`
    - `inertia`
    - `min_cluster_size`
    - `max_cluster_size`
    - `size_ratio`
    - `selection_score`
    - `selected_flag`

### 7.7 Linkage Tables

- `slide_away/artifacts/tables/ri_vs_safety_map.csv`
  - rows: `398`
  - columns: `193`
  - role: feature + outcome + mode join for pooled RI linkage review

- `slide_away/artifacts/tables/domain_outcome_scores.csv`
  - rows: `406`
  - columns: `12`
  - role: domain-specific outcome score frame for deep follow-up analysis
  - key columns:
    - `structure_intrusion_score`
    - `lower_extremity_score`
    - `restraint_kinematics_score`
    - `head_neck_chest_score`
    - `ri_100`
    - `harshness_proxy_z`
    - `seat_response_proxy_z`

- `slide_away/artifacts/tables/domain_linkage_model_summary.csv`
  - rows: `12`
  - columns: `13`
  - role: model fit summary by domain

## 8. Important Implementation Rules And Exceptions

These rules materially affect interpretation.
They should be preserved or consciously changed in the next phase.

### 8.1 `signal_ready_flag`

Current rule:

- `mode='standard_baseline'`
- `status='done'`
- `harmonized_wide_path IS NOT NULL`

Current reproduced count:

- `406`

### 8.2 Barrier-relative sign handling

- driver:
  - `a_y_away = +a_y`
- passenger:
  - `a_y_away = -a_y`

This directly affects:

- `delta_vy_away_mps`
- `ly`
- `ri`
- all windowed lateral features

### 8.3 RI denominator guard

Current rule in `common.py`:

- `RI = abs_delta_vy / abs_delta_vx`
- only if `abs_delta_vx >= 0.25`
- otherwise `RI = NaN`

Reason:

- prevent unstable or exploding RI when longitudinal delta-V is near zero

### 8.4 Feature quality and clustering eligibility

Current rule:

- `cluster_input_flag = 1` when default feature quality score `>= 0.875`

Current clustering preparation in `modeling.py`:

- start only from `cluster_input_flag == 1`
- require row coverage `>= 0.65` across selected window features
- median-impute remaining missing window features column-wise

Interpretation impact:

- clustering is no longer "complete cases only"
- the selected clustering sample is a filtered and partially imputed analytical subset

### 8.5 Outcome plausibility filter

Current rule in `build_outcome_mart.py`:

- `leg_foot_index_left > 5.0 -> NaN`
- `leg_foot_index_right > 5.0 -> NaN`

Reason:

- suppress implausible outlier values before pooled scoring

### 8.6 Pooled safety severity score

Current pooled score combines standardized components from:

- intrusion
- leg index
- foot acceleration
- head HIC15
- rib compression
- NIJ
- thigh proxy

Important caution:

- this pooled score is useful for broad review
- it should not be treated as the only approval target anymore
- domain-split scores are now preferred for deep follow-up analysis

## 9. Phase-By-Phase Work Completed

### Phase 0. Execution Closure

Completed:

- standard wrapper interface closed
- script interface map written
- review folder structure normalized and ordered

Main evidence:

- `reviews/02_execution/01_script_interface_map.md`

### Phase 1. Case Master

Completed:

- built `case_master.parquet`
- reproduced `signal_ready_flag=406`
- created cohort, side, era, asset coverage, preprocessing provenance

Key results:

- canonical cases: `413`
- signal-ready: `406`
- driver: `361`
- passenger: `52`

### Phase 2. Outcome Mart

Completed:

- built `outcomes_v1.parquet`
- joined PDF row catalog into case-level outcome fields
- stored provenance rules per field

Key results:

- row count: `413`
- mean outcome quality score: `0.8054`
- intrusion coverage: `329`
- head HIC15 coverage: `406`
- restraint event coverage: `387`

### Phase 3. Feature Mart

Completed:

- built `features_v1.parquet`
- built `features_v1_strict_origin.parquet`
- computed multiwindow barrier-relative signal features

Key results:

- standard-baseline rows: `406`
- cluster-input-ready rows: `398`
- mean feature quality score: `0.965825`

### Phase 4. Window Sweep

Completed:

- swept `20/40/60/80/100/120/150/250 ms`
- stored candidate scores and selected flags

Key results:

- best current operating candidate: `100 ms`
- selected robustness window: `250 ms`
- best `100 ms` silhouette: `0.7206`
- historic `150 ms` silhouette: `0.7144`

Important interpretation:

- `100 ms` is only slightly ahead of historic `0-150 ms`
- the current evidence is not strong enough for auto-promotion

### Phase 5. Mode Study

Completed:

- compared `k=2/3/4`
- selected conservative working labels
- generated representative-case summary

Key results:

- selected `k=2`
- size split: `392 / 6`
- `k=3` had higher silhouette but extreme imbalance:
  - `100 ms`: `[390, 2, 6]`
  - `150 ms`: `[389, 6, 3]`

Interpretation:

- `k=2` is still too imbalanced for final taxonomy promotion
- `k=3` is even less acceptable for operating standard purposes

### Phase 6. Pooled Outcome Linkage

Completed:

- built `ri_vs_safety_map`
- created pooled RI scatter and delta-V phase plot

Key results:

- cohort-level `RI vs pooled safety severity` correlation: `0.0193`

Interpretation:

- RI-only pooled linkage is effectively weak

### Phase 7. Casebook

Completed:

- built matched-pair casebook
- built structural strategy codebook

Key results:

- matched pairs: `12`

### Post-Phase Review Work

Completed:

- window candidate review
- minor cluster review
- extended linkage review
- domain outcome linkage review

## 10. Key Review Results

### 10.1 Window Candidate Review

Source:

- `reviews/03_analysis/03_window_candidate_review.md`

Main read:

- `100 ms`, `k=2`: silhouette `0.7206`
- `150 ms`, `k=2`: silhouette `0.7144`
- current best candidate remains `100 ms`
- do not retire historic `0-150 ms` automatically

Watchlist features between `100 ms` and `150 ms`:

- `foot_resultant_asymmetry_g`
- `delta_vx_mps`
- `seat_twist_peak_mm`

### 10.2 Minor Cluster Review

Source:

- `reviews/03_analysis/04_minor_cluster_review.md`

Main read:

- minor cluster size: `6`
- all `driver`
- year span: `2012 - 2013`
- all cases belong to a small make-model set

Interpretation:

- too confounded to promote as a stable mode

### 10.3 Extended Linkage Review

Source:

- `reviews/03_analysis/05_extended_linkage_review.md`

Model results:

- RI-only adj R^2: `-0.0016`
- RI + harshness + seat-response proxies adj R^2: `0.0748`
- RI + interaction terms adj R^2: `0.0703`

Best single signal:

- `seat_response_proxy_z`
- Pearson r: `0.2099`
- top-vs-bottom quartile gap: `0.5379`

Interpretation:

- pooled linkage improves with context
- most of the improvement comes from context proxies, not RI interaction terms

Subgroup hints:

- passenger interaction model adj R^2: `0.2117`
- era `2015-2017` interaction model adj R^2: `0.2536`

### 10.4 Domain Outcome Linkage Review

Source:

- `reviews/03_analysis/07_domain_outcome_linkage_review.md`

Domain results:

- structure/intrusion:
  - RI-only adj R^2: `0.0013`
  - proxy model adj R^2: `0.0379`
  - strongest signal: `seat_response_proxy_z`
- lower-extremity:
  - RI-only adj R^2: `0.0017`
  - proxy model adj R^2: `0.0877`
  - strongest signal: `seat_response_proxy_z`
- restraint/kinematics:
  - RI-only adj R^2: `0.0003`
  - proxy model adj R^2: `0.0111`
  - weak and currently not decision-driving
- head-neck-chest:
  - RI-only adj R^2: `-0.0024`
  - proxy model adj R^2: `0.0194`
  - strongest signal: `harshness_proxy_z`

Important subgroup finding:

- passenger lower-extremity interaction model adj R^2: `0.3720`
- era `2015-2017` lower-extremity interaction model adj R^2: `0.4000`

Interpretation:

- the strongest current domain is lower-extremity
- current subgroup gains are concentrated in lower-extremity, not in a general redirection effect

## 11. Current Analytic Interpretation

The current best interpretation is:

- `RI` should be kept
- `RI` should be demoted from the leading explanatory axis
- `x/y/z` acceleration should stay at the center of the physical reading layer
- `seat-response` and `harshness` are currently stronger practical descriptors
- the next naming review should be multiaxis, not binary

This means the project is better described as:

- a study of how `x/y/z` barrier-relative kinematics, `harshness`, and `occupant-compartment response` combine with outcomes

It is no longer best described as:

- a project to prove a single pooled `redirection-dominant` operating standard

## 12. Current Blockers

### 12.1 Operating Window Still Not Signed Off

- `100 ms` is only slightly stronger than historic `0-150 ms`
- case-level rationale is still required

### 12.2 Mode Taxonomy Still Weak

- selected structure `392 / 6`
- minor cluster is confounded by side and era concentration

### 12.3 Linkage Is Better, But Not Yet Approval-Grade

- pooled RI-only linkage is weak
- proxy-aware linkage is only modestly better
- domain-aware linkage is more informative, but still not enough for final causal naming

### 12.4 Naming Frame Is No Longer Stable

Current evidence argues against a simple:

- `redirection-dominant`
- `mixed`
- `crush-dominant`

final operating taxonomy.

The next phase should consider more conservative working names such as:

- `harsh-pulse dominant`
- `seat-response dominant`
- `kinematics-shifted`
- `mixed / unresolved`

## 13. Tests And Validation Status

Current smoke tests:

- `tests/slide_away/test_common.py`
- `tests/slide_away/test_extended_linkage.py`
- `tests/slide_away/test_domain_outcome_linkage.py`

Current smoke result:

- `7` tests passed

What is covered:

- make/model normalization
- passenger sign flip logic
- RI denominator guard
- robust z-score helper
- linear fit helper
- rowwise mean helper
- rowwise max helper

What is still missing:

- regression protection for full feature mart generation
- regression protection for outcome joins
- regression protection for window sweep selection behavior
- regression protection for casebook selection logic

## 14. Recommended Next Deep Analysis

This is the highest-value sequence from the current state.

1. validate the `100 ms` operating window with preregistered representative-case review using `x/y/z` signature changes as the first read
2. complete full manual reading of the `6`-case minor cluster before any stronger taxonomy claim
3. test whether the `passenger` and `2015-2017` lower-extremity gains replicate under stricter subgroup rules
4. run confounding checks against side, era, make-model family, and weight/class proxies
5. decide whether pooled safety severity should remain a top-level summary only, with domain scores used for approval logic
6. redesign working mode names around multiaxis context instead of redirection-versus-crush
7. add stronger regression tests before any attempt to leave `hold`

## 15. Suggested Questions For The Next Analyst

Use these as explicit follow-up questions.

### Window

- does `100 ms` change representative case interpretation enough to justify replacing historic `0-150 ms`?
- which cases show the largest RI and seat-response changes between `100 ms` and `150 ms`?

### Linkage

- is lower-extremity the true primary signal, or is it a proxy-definition artifact?
- do passenger and `2015-2017` subgroup gains survive stricter preregistered evaluation?
- are there domain interactions that should replace the pooled safety score in approval logic?

### Naming

- should the working naming system be changed from outcome-flavored labels to observation-flavored labels?
- what is the minimum defensible taxonomy that does not overclaim physical meaning?

### Confounding

- is the `6`-case minor cluster a real mechanical subgroup or just a side/era/make-model pocket?
- how much of the lower-extremity gain is actually family or era stratification?

## 16. Bottom Line

The repository now supports deep follow-up analysis.
The package is real, reproducible, and reviewable.

But the current evidence still says:

- do not approve a final operating standard
- do not approve final favorable/unfavorable redirection claims
- do not lock the final taxonomy to a simple redirection-versus-crush frame

The most defensible current state remains:

- `validated research package with unresolved mode standardization`
