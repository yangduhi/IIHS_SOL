# Slide Away Study Standard

## Purpose

This folder is the working standard for the `slide_away` study in the IIHS small overlap project.
It freezes the research frame, the required data marts, the execution order, and the phase gates.

This package is intended to be read and followed in the order below:

1. `01_work_instruction.md`
2. `02_execution_plan.md`
3. `03_phase_checklists.md`

## Current Baseline Snapshot

Reference snapshot date: `2026-03-11`

- `filegroups`: `413`
- `vehicles`: `368`
- `signal-ready cohort`: `406`
- `driver-side`: `361`
- `passenger-side`: `52`
- `standard_baseline`: `406`
- `strict_origin`: `406`
- `standard_baseline_full_tdms`: `400`
- `pdf_documents`: `472`
- `pdf_result_tables`: `3337`
- `pdf_result_rows`: `37073`
- `extracted_metrics`: `216506`

Current PDF result table coverage observed in `research.sqlite`:

- `intrusion`: `340` documents / `340` tables
- `restraint_kinematics`: `399` documents / `452` tables
- `leg_foot_injury`: `421` documents / `421` tables
- `head_injury`: `419` documents / `472` tables
- `neck_injury`: `418` documents / `418` tables
- `chest_injury`: `422` documents / `422` tables
- `thigh_hip_injury`: `348` documents / `348` tables
- `dummy_clearance`: `412` documents / `464` tables

## Current Review Status

Review date: `2026-03-11`

- Status: `hold before final approval`
- The study frame, side harmonization rule, and outcome axis remain structurally coherent.
- Standard script interface closure, `signal_ready_flag` evidence, and phase artifacts now exist in the repository.
- The remaining hold reason is validation, not packaging.
- Current window sweep favors `100 ms`, but that operating-window promotion still needs manual acceptance.
- Window review shows `100 ms` only slightly ahead of the historic `0-150 ms` baseline, so the prior baseline is not yet retired.
- Current mode study selects `k=2` with severe imbalance (`392 / 6`), so no final mode standard is approved.
- Minor-cluster review shows the `6`-case cluster is all `driver` and limited to `2012 - 2013`, so confounding remains plausible.
- Current RI-to-safety linkage is weak and does not justify favorable or unfavorable redirection claims.
- Extended linkage review shows proxy-aware linkage is better than RI alone, but the gain comes mostly from harshness and seat-response context.
- Domain outcome linkage shows the strongest current signal is on lower-extremity outcomes, not on a pooled redirection axis.
- Preregistered subgroup validation keeps `passenger` and `2015-2017` lower-ext signals as reviewer evidence only.
- Approval logic now treats pooled severity as summary-only and lower-extremity as the primary review domain.
- Observation-flavored naming now uses `bulk moderate / unresolved` and `high-lateral review pocket`.
- Basic `unittest` coverage now includes feature rules, window selection, and domain join behavior, but validation depth is still below a final operating standard.
- The current package is best treated as a validated research package with unresolved mode standardization.

## Frozen Study Decisions

- The study frame is not a fixed binary type classification.
- The primary frame is `barrier-relative kinematics` on a continuum, with a second axis for `safety outcome`.
- The first research target is `occupant-compartment pulse and kinematics`, not full vehicle energy accounting.
- The primary physical reading layer is occupant-compartment `x/y/z` acceleration:
  - `x`: ride-down and longitudinal pulse
  - `y`: barrier-relative lateralization and redirection
  - `z`: vertical harshness and wheel or suspension path response
- The working kinematics frame is `x+y+z`, not `x+y` alone.
- `x/y/z` is a leading explanatory layer, not a standalone approval rule.
- Seat or foot or compartment-response signals act as context and amplification.
- Domain outcomes remain the approval layer.
- `standard_baseline` is the canonical analysis mode.
- `strict_origin` is used for sensitivity checks only.
- Driver and passenger sides must not be pooled before barrier-relative sign harmonization.
- The primary discovery window is `0-150 ms`.
- The robustness window is `0-250 ms`.
- The first stable baseline cohort is `driver-side only`.
- Passenger-side analysis is an extension layer after the driver-side baseline is validated.
- Outcome enrichment starts from PDF result tables already in `data/research/research.sqlite`.

## Folder Contents

- `README.md`
  - index and frozen decisions
- `01_work_instruction.md`
  - authoritative study instruction
- `02_execution_plan.md`
  - detailed phase-by-phase execution plan
- `03_phase_checklists.md`
  - entry, exit, and QA checklist for each phase
- `reviews/01_governance/01_final_review.md`
  - current approval status and closure items
- `reviews/02_execution/01_script_interface_map.md`
  - executed script interface closure
- `reviews/03_analysis/03_window_candidate_review.md`
  - `100 ms` vs historic `0-150 ms` comparison memo
- `reviews/03_analysis/04_minor_cluster_review.md`
  - manual review memo for the `6`-case minor cluster
- `reviews/03_analysis/05_extended_linkage_review.md`
  - RI, harshness, seat-response, and subgroup linkage memo
- `reviews/03_analysis/07_domain_outcome_linkage_review.md`
  - domain-split linkage memo across structure, lower-extremity, restraint, and head-neck-chest
- `reviews/03_analysis/11_preregistered_lower_ext_subgroup_validation.md`
  - fixed-rule subgroup validation for passenger and `2015-2017` lower-ext signals
- `reviews/03_analysis/12_mode_confounding_signoff.md`
  - side, era, family, and weight proxy sign-off for the selected mode structure
- `reviews/03_analysis/13_domain_approval_logic_review.md`
  - pooled versus domain-aware approval decision memo
- `reviews/03_analysis/14_observation_flavored_naming_review.md`
  - conservative working names for the current selected structure
- `reviews/01_governance/02_next_step_plan.md`
  - prioritized blocker-reduction plan from the current `hold` state
- `reviews/README.md`
  - review folder index and category structure
- `final_study_brief.md`
  - current study outcome and interpretation
- `final_decision_log.md`
  - final approval decision and promotion conditions

## Required Source Paths

- `data/research/research.sqlite`
- `data/analysis/filegroups.csv`
- `output/small_overlap/tables/canonical_small_overlap_tests.csv`
- `output/small_overlap/tables/analysis_cohort_counts.csv`
- `output/small_overlap/tables/signal_feature_summary__standard_baseline__official_known_harmonized_v3_window015.json`
- `data/derived/small_overlap/preprocessed_signals`
- `docs/signals/preprocessing_db_design.md`

Notes:

- `signal_ready_flag` must be reproducible from `research.sqlite` `preprocessing_cases` coverage or from equivalent manifests under `data/derived/small_overlap/preprocessed_signals`.

## Update Rule

If a future change modifies study scope, coordinate conventions, feature definitions, cohort policy, or phase gates, update the four core documents in this folder together:
`README.md`, `01_work_instruction.md`, `02_execution_plan.md`, and `03_phase_checklists.md`.
Do not update only one file and leave the others inconsistent.
