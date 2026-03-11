# Step 03. Keep / Hold / Delete Plan

## Core Keep

- `scripts/core/acquisition/*`
- `scripts/core/metadata/*`
- `scripts/core/catalog/*`
- `scripts/core/documents/*`
- `scripts/core/signals/*`
- `scripts/core/lib/*`
- `sql/research_database.sql`
- `docs/core/*`
- `docs/signals/*`
- `package.json`

Reason:
- These files are part of the mandatory research pipeline and should remain first-class project assets.

## Hold

- `scripts/tools/dashboards/*`
- `scripts/tools/exports/*`
- `scripts/tools/analytics/*`
- `scripts/tools/bootstrap/*`
- `docs/ops/*`
- `docs/archive/rebuild-from-scratch/*`

Reason:
- These are useful and still referenced, but they are not required to build the core database and preprocessing layers.

## Delete Candidate

- `scripts/legacy/analytics/build_signal_moment_batch.py`
  - Keep for now under `legacy/`, then remove after downstream use is confirmed to be zero.
- `package.json` dependency `fast-xml-parser`
  - Candidate only. Confirm no external workflow depends on it before removal.
- `scripts/core/acquisition/download-filegroup.mjs` option `--pending`
  - Keep for CLI compatibility. Mark as deprecated later.
- Root-level empty or duplicate DB artifacts such as `data/research.sqlite`
  - Remove only after confirming no external tool still points there.

## Rule For Delete Candidates

1. Verify that the candidate has no active caller.
2. Mark it deprecated or move it under `legacy/` first when practical.
3. Remove only in a later cleanup change.

## Already Applied In This Execution

- `package.json` field `main`
  - Removed because `index.js` does not exist.
