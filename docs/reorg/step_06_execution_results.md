# Step 06. Execution Results

## Completed

- Implementations moved into `scripts/core/`, `scripts/tools/`, and `scripts/legacy/`
- Root-level wrappers recreated for historical script entrypoints
- Shared Node libraries moved into `scripts/core/lib/`
- Python cross-module imports updated to package-style imports
- `REPO_ROOT` calculations corrected for moved Python implementations
- Core, signal, ops, and archive docs moved into functional folders
- Root-level doc stubs created for the moved top-level docs
- Invalid `package.json > main` metadata removed

## Verification

Successful checks:
- `python -c "import scripts.process_excels, scripts.preprocess_known_signal_families, scripts.build_signal_feature_batch"`
- `python scripts/process_excels.py --help`
- `python scripts/preprocess_known_signal_families.py --help`
- `python scripts/build_signal_feature_batch.py --help`
- `python scripts/rebuild_excel_pipeline.py --help`
- `python scripts/rebuild_pdf_catalog.py --help`
- `python scripts/run_full_tdms_standard_batch.py --help`
- `python scripts/query_signal_similarity.py --help`

Observed external blocker:
- `node scripts/discover-small-overlap.mjs`
- `node scripts/download-filegroup.mjs --pending`

Blocker detail:
- Both Node acquisition flows now resolve the moved code correctly.
- Live execution stops because the IIHS authenticated session is no longer valid.
- This is an environment/session issue, not a post-move import-path regression.

## Remaining Follow-Up

- Remove `fast-xml-parser` only after one more dependency audit
- Decide whether to formally deprecate `--pending` in the downloader help text
