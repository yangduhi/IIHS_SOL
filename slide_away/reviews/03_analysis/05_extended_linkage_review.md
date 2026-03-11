# Extended Outcome Linkage Review

- generated_at: `2026-03-11T05:13:37Z`
- scope: extend linkage beyond RI-only correlation using `100 ms` harshness and seat-response proxies

## Overall Read

- RI-only model: adj R^2 `-0.0016`
- RI + harshness + seat-response proxies: adj R^2 `0.0748`
- RI + interaction terms: adj R^2 `0.0703`
- strongest single signal in this pass: `seat_response_proxy_z` with Pearson r `0.2099` and top-bottom safety gap `0.5379`
- interaction terms add very little beyond the proxy-only model at cohort level.

## Proxy Definitions

- `harshness_proxy_z`: mean standardized `window_100_max_abs_az_g` and `window_100_max_abs_resultant_g`
- `seat_response_proxy_z`: mean standardized `window_100_seat_twist_peak_mm` and `window_100_foot_resultant_asymmetry_g`
- `ri_x_harshness`: `RI_z * harshness_proxy_z`
- `ri_x_seat_response`: `RI_z * seat_response_proxy_z`

## Subgroup Read

- passenger subgroup (`n=52`): interaction model adj R^2 `0.2117`
- era `2015-2017` (`n=131`): interaction model adj R^2 `0.2536`
- low seat-response band (`n=101`): RI-only Pearson r `-0.2505`
- the current `mode_1` minor cluster is still too small for a stable subgroup model.

## Interpretation

- outcome linkage improves when harshness and seat-response context are included.
- most of the gain comes from the context proxies themselves, especially seat-response, not from the RI interaction terms.
- this reduces the risk of over-reading RI alone, but it still does not justify final favorable or unfavorable redirection claims.

## Recommendation

- keep RI as one component of the linkage stack rather than a standalone approval signal
- carry `seat_response_proxy_z` and `harshness_proxy_z` into the next reviewer pass
- treat subgroup signals as exploratory until they survive manual review and confounding checks
