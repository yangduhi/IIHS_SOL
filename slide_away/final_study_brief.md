# Slide Away Final Study Brief

- Date: `2026-03-11`
- Status: `hold before final approval`

## What Is Now Operational

- The study package is execution-ready.
- `case_master`, `outcomes_v1`, `features_v1`, `window_sweep`, `mode_study`, `ri_vs_safety_map`, and `casebook` artifacts were generated in the standard `slide_away` paths.
- `signal_ready_flag=406` is reproducible from `preprocessing_cases`.

## Current Evidence

- Cohort:
  - canonical cases: `413`
  - signal-ready: `406`
  - driver: `361`
  - passenger: `52`
- Outcome mart:
  - mean quality score: `0.8054`
  - intrusion coverage: `329`
  - head HIC15 coverage: `406`
- Window sweep:
  - current best operating window: `100 ms`
  - best `k`: `2`
  - silhouette: `0.7206`
- Window candidate review:
  - historic `0-150 ms` baseline remains close at silhouette `0.7144`
  - `100 ms` is slightly better on the current objective, but not enough for automatic promotion
  - feature stability watchlist includes `foot_resultant_asymmetry_g`, `delta_vx_mps`, and `seat_twist_peak_mm`
- Mode study:
  - selected structure: `2` modes
  - size split: `392 / 6`
- Minor cluster review:
  - all `6` cases are `driver`
  - year span: `2012 - 2013`
  - confounding remains a serious concern
- Outcome linkage:
  - RI vs safety severity correlation: `0.0193`
- Extended linkage review:
  - RI-only model adj R^2: `-0.0016`
  - RI + harshness + seat-response proxies adj R^2: `0.0748`
  - RI + interaction terms adj R^2: `0.0703`
  - strongest single signal in this pass: `seat_response_proxy_z`
- Domain outcome linkage review:
  - lower-extremity proxy model adj R^2: `0.0877`
  - structure/intrusion proxy model adj R^2: `0.0379`
  - head-neck-chest proxy model adj R^2: `0.0194`
  - restraint/kinematics proxy model adj R^2: `0.0111`
  - strongest subgroup hints are concentrated in lower-extremity outcomes
- Preregistered subgroup validation:
  - passenger lower-ext proxy adj R^2: `0.3748`
  - era `2015-2017` lower-ext proxy adj R^2: `0.3852`
  - both remain review evidence, not approval-grade claims
- Confounding sign-off:
  - the `6`-case minor cluster is still concentrated on `driver`, `2001-2014`, and `Q2` weight proxy
- Approval logic review:
  - pooled severity remains summary-only
  - lower-extremity is the current primary review domain
- Observation-flavored naming review:
  - `mode_0 -> bulk moderate / unresolved`
  - `mode_1 -> high-lateral review pocket`
- Validation:
  - `unittest` coverage now includes feature rules, window selection, and domain join behavior
  - current smoke result: `11` tests passed

## Interpretation

- The barrier-relative ETL stack is now real and reproducible.
- The present data does not yet support a stable final `slide_away` mode standard.
- The package is best described as a validated research package with unresolved mode standardization.
- Occupant-compartment `x/y/z` acceleration should remain the primary physical reading layer for the next pass.
- Use `x=ride-down`, `y=barrier-relative lateralization`, and `z=vertical harshness` as the leading explanatory frame.
- Do not treat `x/y/z` as a standalone approval rule; approval still needs domain outcomes and compartment-response context.
- Current mode structure is too imbalanced to justify promotion to a working taxonomy.
- Current RI-based linkage is too weak to justify favorable or unfavorable redirection claims.
- Proxy-aware linkage is more informative than RI alone, but the gain comes mostly from seat-response and harshness context rather than RI interaction terms.
- Current outcome separation looks strongest on the lower-extremity axis, which argues against a simple redirection-versus-crush naming frame.

## Operating Rule

- Keep the current working labels conservative.
- Do not promote `crush-dominant` or `redirection-dominant` beyond exploratory interpretation.
- Treat the current output as a validated research package with unresolved mode standardization.

## Next Required Work

1. accept or reject `100 ms` as the operating window with case-level `x/y/z` rationale
2. complete reviewer reading on the `6`-case high-lateral pocket and decide whether it is rejected as confounded
3. decide whether the `passenger` and `2015-2017` lower-ext signals remain exploratory or are accepted as structured reviewer evidence
4. sign off or reject the domain-first approval frame
5. sign off or reject the conservative observation-flavored naming rule
6. decide whether the current `11` tests are sufficient for research-package status or if stronger production coverage is required
