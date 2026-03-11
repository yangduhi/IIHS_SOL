# Slide Away Final Review

- Review date: `2026-03-11`
- Status: `hold before final approval`
- Scope: `slide_away` standard package, repository implementation, executed artifacts, and `research.sqlite` baseline snapshot

## Summary

`slide_away` is now execution-ready.
The standard script interface is closed, `signal_ready_flag=406` is reproducible from `preprocessing_cases`, and Phase 1-7 artifacts exist under `slide_away/artifacts` and `slide_away/reviews`.

The approval state remains `hold` for a different reason than before.
The remaining blocker is no longer package incompleteness; it is validation weakness.
The most accurate current description is a validated research package with unresolved mode standardization.
The active physical reading frame for the next pass is occupant-compartment `x/y/z` acceleration plus compartment-response context and domain outcomes.

## Closed Items

1. Standard script interface closure
   - implemented wrappers and execution modules for:
     - `build_case_master`
     - `build_outcome_mart`
     - `build_barrier_relative_features`
     - `run_window_sweep`
     - `run_mode_study`
     - `build_mode_casebook`
     - `build_ri_safety_map`
2. `signal_ready_flag` reproducibility
   - reproduced as:
     - `mode='standard_baseline'`
     - `status='done'`
     - `harmonized_wide_path IS NOT NULL`
   - reproduced count: `406`
3. Artifact and QA closure
   - `case_master.parquet`
   - `outcomes_v1.parquet`
   - `features_v1.parquet`
   - `features_v1_strict_origin.parquet`
   - `window_sweep_summary.csv`
   - `mode_study_summary.csv`
   - `ri_vs_safety_map.csv`
   - `matched_pair_casebook.md`
   - figures and logs

## Current Findings

- Phase 1 cohort snapshot:
  - canonical cases: `413`
  - signal-ready: `406`
  - PDF-available: `410`
  - Excel-available: `413`
- Phase 2 outcome mart:
  - mean quality score: `0.8054`
  - intrusion coverage: `329`
  - head HIC15 coverage: `406`
  - restraint event coverage: `387`
- Phase 4 window sweep:
  - current best operating window: `100 ms`
  - best `k`: `2`
  - silhouette: `0.7206`
- Phase 5 mode study:
  - selected `k=2`
  - cluster sizes: `392 / 6`
  - interpretation remains provisional
- Window candidate review:
  - `100 ms`, `k=2`: silhouette `0.7206`
  - historic `0-150 ms`, `k=2`: silhouette `0.7144`
  - current evidence supports `100 ms` as the best candidate, not as an auto-approved standard
- Minor cluster review:
  - all `6` cases are `driver`
  - year span: `2012 - 2013`
  - make-model concentration remains high enough that confounding is still plausible
- Phase 6 outcome linkage:
  - RI vs safety severity correlation: `0.0193`
  - current continuous RI signal does not yet produce a persuasive safety separation by itself
- Extended linkage review:
  - RI-only model adj R^2: `-0.0016`
  - RI + harshness + seat-response proxies adj R^2: `0.0748`
  - RI + interaction terms adj R^2: `0.0703`
  - strongest single signal in this pass: `seat_response_proxy_z`
  - passenger and `2015-2017` subgroup signals are interesting but still exploratory
- Domain outcome linkage review:
  - lower-extremity proxy model adj R^2: `0.0877`
  - structure/intrusion proxy model adj R^2: `0.0379`
  - head-neck-chest proxy model adj R^2: `0.0194`
  - restraint/kinematics proxy model adj R^2: `0.0111`
  - passenger and `2015-2017` subgroup gains remain concentrated in lower-extremity outcomes
  - the next analytic pass should read `x=ride-down`, `y=barrier-relative lateralization`, and `z=vertical harshness` together instead of reducing the frame to RI alone
- Preregistered subgroup validation:
  - passenger proxy adj R^2: `0.3748`
  - era `2015-2017` proxy adj R^2: `0.3852`
  - both remain exploratory until reviewer disposition
- Confounding sign-off:
  - minor-cluster enrichment is strongest on `driver`, `2001-2014`, and `Q2` weight proxy
- Approval logic review:
  - pooled severity is summary-only
  - lower-extremity is the current primary review domain
- Naming review:
  - current safe working names are `bulk moderate / unresolved` and `high-lateral review pocket`
- Validation status:
  - regression coverage now exists for shared helpers, feature rules, window selection, and domain join logic
  - smoke result: `11` tests passed
  - regression protection for feature/window/join logic is still incomplete

## Remaining Approval Blockers

1. Mode validity is still weak
   - selected `k=2` is extremely imbalanced
   - the minor cluster has only `6` cases
   - the minor cluster is also side- and era-concentrated
   - this is not strong enough for a working standard mode taxonomy
2. Outcome linkage is still weak
   - current RI-to-safety relationship is near-zero at cohort level
   - proxy-aware linkage is better than RI alone, but most of the gain comes from context proxies
   - domain linkage is strongest on lower-extremity and not on a pooled redirection axis
   - `x/y/z` should remain the primary explanatory layer, but not the sole approval layer
   - the present mart supports review, but not a final causal claim
3. Operating window promotion is not signed off
   - `100 ms` slightly outperforms historic `0-150 ms`
   - current evidence is still short of a reviewer-approved operating-window change
4. Final naming is not justified
   - `crush-dominant` and `redirection-dominant` remain exploratory notes only
   - current evidence supports a multiaxis frame more than a simple redirection-versus-crush frame
   - no stable final `slide_away` mode count should be declared yet

## Promotion Rule

Promote from `hold` only after the following are met.

1. the selected window is manually accepted as the new operating standard or explicitly rejected with rationale
2. the mode structure remains interpretable after imbalance review and confounding checks
3. proxy-aware linkage survives subgroup and confounding review with practical separation across the relevant outcome domains
4. regression coverage expands beyond shared helpers into core feature/window/join logic
5. `final_decision_log.md` records the acceptance basis for the final operating standard
