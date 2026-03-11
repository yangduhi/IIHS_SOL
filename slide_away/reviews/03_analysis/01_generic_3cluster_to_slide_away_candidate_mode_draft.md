# Exploratory Slide-Away Interpretation Hypotheses

- Draft date: `2026-03-11`
- Status: `exploratory only`
- Source baseline:
  - `standard_baseline`
  - `official_known_harmonized_v3_window015`
  - `kmedoids_multiview_v3_window015`
  - `0-150 ms`

## Purpose

This memo records a cautious interpretation layer for the existing generic signal `3 cluster`.
It is not the final `slide_away` mode map.

The current generic cluster comes from a multiview signal morphology batch.
It is not built from a dedicated barrier-relative `slide_away` feature mart.

## Current Generic Cluster Snapshot

- total cases: `406`
- selected cluster count: `3`
- silhouette: `0.2696`
- cluster sizes:
  - `cluster 0`: `359`
  - `cluster 1`: `23`
  - `cluster 2`: `24`

## Safe Working Interpretation

| Generic cluster | Current safe working name | Exploratory slide_away interpretation | Confidence | Why |
| --- | --- | --- | --- | --- |
| `cluster 0` | `bulk moderate / mixed holding bucket` | `mixed` candidate | medium | dominant bulk cluster; likely still contains more than one physical subtype |
| `cluster 1` | `occupant-compartment-response dominant` | `crush-dominant` candidate | low | separation is driven more by seat and lower-extremity response than by vehicle pulse magnitude |
| `cluster 2` | `harsh-pulse dominant` | `redirection-dominant` candidate | low | separation is driven by vehicle resultant/lateral/vertical harshness, but barrier-relative redirection is not yet directly established |

## Cluster Notes

### Cluster 0

- Best treated as the current bulk holding bucket.
- `mixed` is still a temporary name, not a final class.
- This cluster likely contains multiple subtypes that a barrier-relative mart could split later.

### Cluster 1

- Current safe reading: `occupant-compartment-response dominant`
- Exploratory note: it may later align with a `crush-dominant` subgroup.
- Restriction:
  - do not promote this cluster to `failed crush management`
  - do not treat the current label as a final physical mode

### Cluster 2

- Current safe reading: `harsh-pulse dominant`
- Exploratory note: it may later align with a `redirection-dominant` subgroup.
- Restriction:
  - do not promote this cluster to `favorable redirection`
  - do not treat the current label as a final physical mode

## Why This Is Not Final

The generic `3 cluster` is still not a final `slide_away` mode for four reasons.

1. Barrier-relative lateral sign harmonization is not directly baked into the generic cluster.
2. `RI`, `LY`, seat twist, and foot asymmetry are not the defining feature axes.
3. Outcome linkage is not built into the clustering step.
4. The `359 / 23 / 24` size imbalance is too strong to promote the minor clusters as final physical classes.

## Current Working Rule

Current operating use is limited to the safe working names below.

- `cluster 0` -> `bulk moderate / mixed holding bucket`
- `cluster 1` -> `occupant-compartment-response dominant`
- `cluster 2` -> `harsh-pulse dominant`

The exploratory notes below may be recorded in review documents, but not used as current working labels.

- `cluster 1` may later align with `crush-dominant`
- `cluster 2` may later align with `redirection-dominant`

## Promotion Rule

Only revisit promotion after the following are complete.

1. barrier-relative feature mart generation
2. window sensitivity review
3. outcome linkage review
4. side / era / make-model confounding review
5. representative-case manual review
