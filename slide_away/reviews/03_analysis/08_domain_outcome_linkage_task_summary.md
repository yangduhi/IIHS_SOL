# Domain Outcome Linkage Task Summary

- Date: `2026-03-11`
- Scope: split `slide_away` linkage across outcome domains instead of relying only on pooled safety severity
- Status: `completed with approval state still on hold`

## What Was Added

- new review entrypoint: `scripts/review_domain_outcome_linkage.py`
- new execution module: `scripts/tools/slide_away/review_domain_outcome_linkage.py`
- new review memo: `reviews/03_analysis/07_domain_outcome_linkage_review.md`
- new tables:
  - `artifacts/tables/domain_outcome_scores.csv`
  - `artifacts/tables/domain_linkage_signal_summary.csv`
  - `artifacts/tables/domain_linkage_model_summary.csv`
  - `artifacts/tables/domain_linkage_subgroup_summary.csv`
- new figure:
  - `artifacts/figures/domain_linkage_overview.png`
- new smoke coverage:
  - `tests/slide_away/test_domain_outcome_linkage.py`

## Main Findings

- RI-only linkage stays weak across all domains
- lower-extremity is the strongest current domain for context-aware linkage
  - proxy model adj R^2: `0.0653`
- structure/intrusion improves, but less strongly
  - proxy model adj R^2: `0.0361`
- head-neck-chest is more aligned with harshness than with seat-response
  - proxy model adj R^2: `0.0501`
- restraint/kinematics remains weak
  - proxy model adj R^2: `0.0138`

## Subgroup Read

- passenger lower-extremity interaction model adj R^2: `0.3105`
- era `2015-2017` lower-extremity interaction model adj R^2: `0.3980`
- current read:
  - promising, but still exploratory

## Decision Impact

- RI should remain in the linkage stack, but not as the leading explanatory axis
- seat-response and harshness context now have stronger support than a pooled redirection-only story
- naming should move toward a multiaxis frame rather than a simple redirection-versus-crush frame
- approval state remains `hold`
