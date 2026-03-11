# Preregistered Lower-Extremity Subgroup Validation

- generated_at: `2026-03-11T05:14:16Z`
- target: `lower_extremity_score`
- fixed subgroup list: `test_side=passenger`, `era=2015-2017`
- fixed model list: `ri_plus_proxies`, `ri_plus_interactions`
- fixed readout: adjusted R^2 plus bootstrap stability and composition checks

## Overall Read

- `test_side=passenger`: proxy adj R^2 `0.3748` (bootstrap median `0.4010`; p10-p90 `0.1439 - 0.5794`), interaction adj R^2 `0.3720`, complement proxy adj R^2 `0.0688`
- `era=2015-2017`: proxy adj R^2 `0.3852` (bootstrap median `0.4040`; p10-p90 `0.2616 - 0.5578`), interaction adj R^2 `0.4000`, complement proxy adj R^2 `0.0432`

## Composition Watch

- `test_side=passenger` top family `Toyota Tacoma` share `0.0577`; top weight quartile `` share `nan`
- `era=2015-2017` top family `Hyundai Sonata` share `0.0227`; top weight quartile `Q4` share `0.4079`

## Interpretation

- The preregistered subgroup signal remains strongest on lower-extremity outcomes, not on pooled severity.
- Passenger and `2015-2017` gains remain review-worthy, but they still require confounding caution before any operating claim.
- If bootstrap support collapses or composition concentration dominates, treat the gain as opportunistic rather than as a stable subgroup rule.

## Recommendation

- Keep these subgroup results as structured reviewer evidence, not as approval-grade claims.
- Carry the subgroup read into confounding closure and approval-logic review before any taxonomy change.
