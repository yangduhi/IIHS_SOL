# Extended Linkage Task Summary

- Date: `2026-03-11`
- Scope: expand `slide_away` outcome linkage beyond RI-only correlation
- Status: `completed with approval state still on hold`

## What Was Added

- new review entrypoint: `scripts/review_extended_linkage.py`
- new execution module: `scripts/tools/slide_away/review_extended_linkage.py`
- new review memo: `reviews/03_analysis/05_extended_linkage_review.md`
- new tables:
  - `artifacts/tables/extended_linkage_signal_summary.csv`
  - `artifacts/tables/extended_linkage_model_summary.csv`
  - `artifacts/tables/extended_linkage_subgroup_summary.csv`
- new figure:
  - `artifacts/figures/extended_linkage_overview.png`
- new smoke coverage:
  - `tests/slide_away/test_extended_linkage.py`

## Linkage Stack Used

- `RI_100`
- `harshness_proxy_z`
  - mean standardized `window_100_max_abs_ax_g`
  - mean standardized `window_100_max_abs_ay_g`
- `seat_response_proxy_z`
  - mean standardized `window_100_seat_twist_peak_mm`
  - mean standardized `window_100_foot_resultant_asymmetry_g`
- interaction terms:
  - `RI_z x harshness_proxy_z`
  - `RI_z x seat_response_proxy_z`

## Main Findings

- RI-only model adj R^2: `-0.0016`
- RI + harshness + seat-response proxies adj R^2: `0.0689`
- RI + interaction terms adj R^2: `0.0654`
- strongest single signal: `seat_response_proxy_z`
  - Pearson r: `0.2099`
  - top-vs-bottom quartile safety gap: `0.5379`

## Subgroup Read

- passenger subgroup:
  - `n=52`
  - interaction model adj R^2: `0.2677`
- era `2015-2017`:
  - `n=131`
  - interaction model adj R^2: `0.2736`
- current interpretation:
  - interesting, but still exploratory

## Decision Impact

- outcome linkage is stronger with context than with RI alone
- most of the gain comes from harshness and seat-response context, not from RI interaction terms
- this supports keeping RI as one component of the linkage stack
- this does not justify final favorable or unfavorable redirection claims
- approval state remains `hold`
