# Window Candidate Review

- generated_at: `2026-03-11T05:13:41Z`
- scope: compare current best `100 ms` candidate against historic `0-150 ms` baseline outputs

## Summary

- `100 ms`, `k=2`: silhouette `0.7206`, size ratio `65.3333`
- `150 ms`, `k=2`: silhouette `0.7144`, size ratio `65.3333`
- `100 ms` performs slightly better on the current clustering objective.
- This is still not enough for automatic operating-window promotion.

## Feature Stability Watchlist

- `foot_resultant_asymmetry_g`: paired `406`, correlation `0.8163`, mean abs delta `2.4432`
- `delta_vx_mps`: paired `406`, correlation `0.8717`, mean abs delta `2.4635`
- `seat_twist_peak_mm`: paired `318`, correlation `0.9612`, mean abs delta `3.3458`

## Largest Case-Level XYZ Signature Shifts

- `CEN1813` `2019 Chevrolet Silverado 1500 (crew cab)`: `ax 34.16 -> 34.16`, `ay 26.47 -> 39.12`, `az 62.76 -> 69.14`, `RI 0.462 -> 0.302`, safety `0.157`
- `CEN1901` `2019 Honda HR-V`: `ax 34.91 -> 34.91`, `ay 16.76 -> 23.02`, `az 28.59 -> 38.21`, `RI 0.382 -> 0.438`, safety `-0.344`
- `CEN2102` `2021 Ford Mustang Mach-E`: `ax 81.11 -> 84.04`, `ay 51.33 -> 64.16`, `az 33.10 -> 33.10`, `RI 0.570 -> 1.391`, safety `-0.400`
- `CEN1601` `2016 Chevrolet Silverado 1500 (Crew cab)`: `ax 29.84 -> 33.46`, `ay 23.73 -> 32.27`, `az 38.52 -> 38.52`, `RI 0.411 -> 0.269`, safety `1.300`
- `CEN2209` `2022 Rivian R1T (crew cab)`: `ax 23.74 -> 31.77`, `ay 13.75 -> 13.75`, `az 33.20 -> 33.20`, `RI 0.348 -> 0.184`, safety `-0.129`

## Recommendation

- Keep `100 ms` as the current best candidate.
- Read the operating-window difference first through `x/y/z` pulse signatures, not RI alone.
- Do not auto-replace the historic `0-150 ms` operating baseline until a reviewer accepts the window change with case-level rationale.
