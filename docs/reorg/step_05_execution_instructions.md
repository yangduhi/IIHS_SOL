# Step 05. Execution Instructions

## Phase 0. Baseline

1. Validate the current database state.
2. Record the planned target structure.
3. Confirm the CLI compatibility policy.

Status:
- Completed

## Phase 1. Directory Skeleton

1. Create `scripts/core`, `scripts/tools`, and `scripts/legacy`.
2. Create `docs/core`, `docs/signals`, `docs/ops`, and `docs/archive`.

Status:
- Completed

## Phase 2. Core Script Moves

1. Move acquisition, metadata, catalog, document, and signal implementations into `scripts/core/`.
2. Move shared Node libraries into `scripts/core/lib/`.
3. Recreate root-level wrappers for the old script paths.

Status:
- Completed

## Phase 3. Tool And Legacy Moves

1. Move dashboards, exports, analytics, and bootstrap helpers into `scripts/tools/`.
2. Move the older MOMENT batch path into `scripts/legacy/analytics/`.
3. Recreate root-level wrappers for compatibility.

Status:
- Completed

## Phase 4. Runtime Fixes

1. Fix moved import paths.
2. Fix `REPO_ROOT` path calculations inside moved Python modules.
3. Re-run smoke tests.

Status:
- Completed

## Phase 5. Documentation Move

1. Move core docs into `docs/core/`.
2. Move signal docs into `docs/signals/`.
3. Move operational docs into `docs/ops/`.
4. Move rebuild guides into `docs/archive/`.
5. Leave root-level stub files behind.

Status:
- Completed

## Phase 6. Cleanup Review

1. Remove obviously invalid metadata such as `package.json > main`.
2. Leave higher-risk cleanup items for a later pass.

Status:
- Completed for low-risk cleanup. Higher-risk cleanup candidates remain deferred by design.
