# Step 02. Target Folder Structure

## Scripts

```text
scripts/
  core/
    acquisition/
    metadata/
    catalog/
    documents/
    signals/
    lib/
  tools/
    dashboards/
    exports/
    analytics/
    bootstrap/
  legacy/
    analytics/
```

## Docs

```text
docs/
  core/
  signals/
  ops/
  archive/
  reorg/
```

## Compatibility Layer

- Keep the historical root-level script names in `scripts/`
- Point each root script to the moved implementation
- Keep the historical root-level doc paths in `docs/`
- Point each moved doc path to the new location with a short stub file

## Resulting Rule

- `core/` holds the required build pipeline
- `tools/` holds optional dashboards, exports, reporting, and analysis helpers
- `legacy/` holds old-but-retained code that should not be treated as the active path
