# Domain Approval Logic Review

- generated_at: `2026-03-11T05:14:25Z`
- scope: compare pooled approval logic against domain-aware approval logic

## Readout

- pooled severity proxy model adj R^2: `0.0748`
- lower-extremity proxy model adj R^2: `0.0877`
- head-neck-chest proxy model adj R^2: `0.0194`
- structure/intrusion proxy model adj R^2: `0.0379`
- restraint/kinematics proxy model adj R^2: `0.0111`

## Decision Frame

- Pooled safety severity should remain a summary-only readout.
- Lower-extremity is the current primary approval domain.
- Head-neck-chest and structure/intrusion can support interpretation when they align with lower-extremity.
- Restraint/kinematics is currently too weak to drive naming or approval.

## Recommendation

- Do not approve taxonomy changes from pooled severity alone.
- Use domain scores as the reviewer-facing approval layer until mode standardization becomes more stable.
- Keep subgroup signals as exploratory hints inside the domain frame, not as standalone approval evidence.
