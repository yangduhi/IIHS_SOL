# Mode Confounding Sign-Off Review

- generated_at: `2026-03-11T05:14:08Z`
- scope: selected mode structure only

## Minor Cluster Headline

- `test_side` top category `driver`: cluster share `1.0000`, overall share `0.8693`, enrichment `1.1503`
- `era` top category `2001-2014`: cluster share `1.0000`, overall share `0.3769`, enrichment `2.6533`
- `weight_quartile` top category `Q2`: cluster share `0.5000`, overall share `0.1407`, enrichment `3.5536`
- family mix: Honda Accord 4 door (1), Honda Civic 4 Door (1), Volvo XC 60 (1), Honda Accord 2 door (1), Honda Civic 2 door (1)

## Interpretation

- The selected minor cluster remains confounded if side or era concentration is near-complete.
- Weight-quartile concentration is a proxy warning, not a full causal explanation.
- Family dispersion alone does not close confounding when the cluster is this small.

## Recommendation

- Keep the current selected mode structure on `hold` until these concentration patterns are explicitly accepted or rejected by review.
