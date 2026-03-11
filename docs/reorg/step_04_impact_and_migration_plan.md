# Step 04. Impact and Migration Plan

## Impact Areas

### Script Imports
- Python modules that imported sibling scripts by old top-level names
- Node entrypoints that imported `scripts/lib/*`
- Wrapper entrypoints that need repo-root bootstrap behavior

### CLI Compatibility
- Existing `npm` script names must keep working
- Existing `python scripts/<name>.py` calls must keep working
- Existing `node scripts/<name>.mjs` calls must keep working

### Documentation Links
- Existing root-level doc links should not fail immediately after the move

### Default Paths
- Moved implementations must continue to resolve:
  - `data/research/research.sqlite`
  - `data/derived/...`
  - `output/...`

## Migration Rules

1. Move implementations first.
2. Recreate the old entrypoints as wrappers.
3. Fix imports inside moved implementations so package import remains valid.
4. Correct `REPO_ROOT` calculations after the move.
5. Move docs and leave root stubs behind.
6. Verify before removing any deprecated element.

## Validation Targets

- Wrapper import works
- `--help` works for key Python entrypoints
- Package imports work for moved Python modules
- Node entrypoints resolve new library paths
- Docs open from both new paths and old stub paths
