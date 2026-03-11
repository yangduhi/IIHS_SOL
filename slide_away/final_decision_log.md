# Final Decision Log

- Decision date: `2026-03-11`
- Current approval state: `hold`

## Decision

The `slide_away` package is not approved as a final operating standard.

## Why Approval Did Not Advance

1. The package is now executable, but validation remains weaker than a final operating standard requires.
2. The current `100 ms` candidate only slightly outperforms the historic `0-150 ms` baseline and still needs manual acceptance.
3. The selected mode structure is highly imbalanced at `392 / 6`.
4. The `6`-case minor cluster is entirely `driver` and limited to `2012 - 2013`, so confounding remains plausible.
5. The current RI-to-safety linkage is weak at cohort level.
6. Proxy-aware linkage is better than RI alone, but most of the gain comes from context proxies rather than RI interaction terms.
7. Domain outcome linkage is strongest on lower-extremity and not on a pooled redirection axis.
8. Preregistered lower-ext subgroup validation is promising but still exploratory.
9. Final naming for `slide_away` modes is still not defensible.

## What Was Accepted

- standard wrapper interface
- reproducible `signal_ready_flag`
- case master, outcome mart, feature mart
- occupant-compartment `x/y/z` acceleration as the primary physical reading layer for the next pass
- window sweep, mode study, RI map, casebook
- `100 ms` vs `0-150 ms` comparison review
- `6`-case minor-cluster review
- extended linkage review with harshness, seat-response, and subgroup summaries
- domain outcome linkage review across structure, lower-extremity, restraint, and head-neck-chest axes
- preregistered lower-extremity subgroup validation
- mode confounding sign-off review
- domain-aware approval logic review
- observation-flavored naming review
- QA logs and review notes under `slide_away`
- expanded `unittest` coverage for shared helpers, feature rules, window selection, and domain join logic

## What Remains Provisional

- operating window promotion from historic `0-150 ms` baseline to current `100 ms` candidate
- any final mode count
- any final `redirection-dominant` or `crush-dominant` class naming
- any favorable / unfavorable redirection claim
- any claim that `x/y/z` acceleration alone is sufficient for final approval
- any claim that the `6`-case minor cluster is a stable physical mode rather than a confounded subgroup
- any claim that passenger or `2015-2017` subgroup linkage is stable enough for an operating standard
- any claim that pooled safety severity is the only approval target for mode naming
- any final promotion of `high-lateral review pocket` beyond a conservative working label

## Promotion Conditions

Advance from `hold` only if all of the following are met.

1. the selected operating window is manually accepted with rationale
2. mode structure remains interpretable after imbalance and confounding review
3. proxy-aware outcome linkage survives subgroup and confounding review with practical separation across the relevant outcome domains
4. smoke coverage expands beyond shared helpers to core feature/window/join logic
5. a reviewer signs off the final class naming rule
