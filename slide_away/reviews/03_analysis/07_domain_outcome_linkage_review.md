# Domain Outcome Linkage Review

- generated_at: `2026-03-11T05:13:36Z`
- scope: decompose outcome linkage into structure, lower-extremity, restraint, and head-neck-chest axes

## Overall Read

- `structure/intrusion`: RI-only adj R^2 `0.0013`, proxy model `0.0379`, interaction model `0.0360`, strongest signal `seat_response_proxy_z` (`r=0.1912`)
- `lower-extremity`: RI-only adj R^2 `0.0017`, proxy model `0.0877`, interaction model `0.0850`, strongest signal `seat_response_proxy_z` (`r=0.2327`)
- `restraint/kinematics`: RI-only adj R^2 `0.0003`, proxy model `0.0111`, interaction model `0.0194`, strongest signal `seat_response_proxy_z` (`r=0.1260`)
- `head-neck-chest`: RI-only adj R^2 `-0.0024`, proxy model `0.0194`, interaction model `0.0195`, strongest signal `harshness_proxy_z` (`r=0.1188`)

## Interpretation

- RI-only linkage stays weak across all outcome domains.
- context-aware linkage is strongest on the lower-extremity axis, where seat-response is the dominant single signal in this pass.
- structure/intrusion also improves under the context model, but less than lower-extremity.
- head-neck-chest linkage leans more on harshness than on seat-response.
- restraint/kinematics remains weak and should not drive naming or approval decisions yet.

## Subgroup Hints

- passenger lower-extremity interaction model: adj R^2 `0.3720` (`n=52`)
- era `2015-2017` lower-extremity interaction model: adj R^2 `0.4000` (`n=131`)
- current subgroup gains look concentrated in lower-extremity outcomes rather than in a general redirection effect.

## Recommendation

- keep RI in the linkage stack, but demote it from the leading explanatory axis
- prioritize seat-response and harshness context in the next naming review
- split future approval discussions by outcome domain instead of relying on a single pooled safety score
