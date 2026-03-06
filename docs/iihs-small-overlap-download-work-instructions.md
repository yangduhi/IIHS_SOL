# IIHS TechData Small Overlap Download Work Instructions

## Goal

Build a repeatable project that downloads all available IIHS TechData assets for:

- `Small overlap frontal: driver-side`
- `Small overlap frontal: passenger-side`

The project must support an initial historical backfill and ongoing incremental sync.

## Facts Confirmed On March 6, 2026

- `https://techdata.iihs.org/` is publicly reachable, but file access requires login.
- The public landing page states that registered users get access to technical data and reports.
- Clicking `Log in to IIHS TechData` redirects to Microsoft login for the `iihspublic.onmicrosoft.com` tenant.
- After authentication, the site exposes an RSS link at `https://techdata.iihs.org/rss.ashx`.
- RSS items use URLs like `https://techdata.iihs.org/secure/filegroups.aspx?updated=02/28/2026`.
- Individual file groups use URLs like `https://techdata.iihs.org/secure/filegroup.aspx?8751`.
- The test-type dropdown includes the exact labels `Small overlap frontal: driver-side` and `Small overlap frontal: passenger-side`.
- A file group detail page shows a folder tree on the left and file list on the right. The provided example contains folders such as `DATA\DAS\Logs`, `DATA\DAS\Reports`, `DATA\Excel`, `PHOTOS`, `REPORTS`, and `VIDEO`.
- Authenticated list URLs follow `https://techdata.iihs.org/secure/filegroups.aspx?t={typeCode}&r=released`.
- Confirmed type codes:
  - `25` = `Small overlap frontal: driver-side`
  - `26` = `Small overlap frontal: passenger-side`
- The test-type dropdown does not refresh results by itself in automation; after selecting a type, you must submit the form.
- File group folder clicks are ASP.NET postbacks, while file downloads resolve to direct links under `/secure/file.ashx?...`.
- A direct `/secure/file.ashx?...` request without authenticated cookies redirects to `/`, while the same URL succeeds from the authenticated browser context.

## Gate 0: Permission And Access

Do this before any bulk download work.

1. Create or confirm a valid IIHS TechData account.
2. Confirm login works through the Microsoft sign-in flow.
3. Confirm with your internal owner whether large-scale repetitive download is acceptable under your intended use.
4. If needed, ask IIHS for written confirmation before full historical backfill.

Why this gate exists:

- The public site states that repetitive copying or redistribution for commercial use is not permitted without written permission.
- Support contact shown on the site: `techdatasupport@iihs.org`
- Legal contact shown on the site: `legal@iihs.org`

Exit criteria:

- One working account.
- One approved usage decision.
- One person designated to solve MFA, password reset, or access revocation issues.

## Recommended Tooling

Use the tools in this order.

1. `playwright` skill
   Use this for authenticated browser automation, element snapshots, file download flow discovery, and session capture.
2. `shell_command`
   Use this to run `npx @playwright/cli`, manage files, redirect logs, and schedule batch runs.
3. `js_repl`
   Use this for Node-based helpers such as RSS parsing, manifest cleanup, dedupe logic, and quick data transforms.
4. `web`
   Use this only for public pages, public RSS validation, or non-authenticated documentation checks.
5. Optional `screenshot` skill
   Use this only if OS-level capture is needed for troubleshooting a headed browser session.

## Important Environment Note

This workspace is Windows PowerShell-based. The `playwright` skill ships a Bash wrapper, but on Windows the most reliable invocation is the direct CLI:

```powershell
npx --yes --package @playwright/cli playwright-cli --help
```

Use that form in all initial project notes and scripts unless you standardize on Git Bash.

## Suggested Repository Layout

```text
docs/
  iihs-small-overlap-download-work-instructions.md
  field-notes.md
scripts/
  capture-session.ps1
  discover-small-overlap.mjs
  download-filegroup.mjs
  sync-rss.mjs
data/
  index/
    filegroups.jsonl
    files.jsonl
    manifest.sqlite
  raw/
    small-overlap-driver-side/
    small-overlap-passenger-side/
output/
  playwright/
.auth/
  profile/
  storage-state.json
```

Rules:

- Never commit credentials.
- Never commit raw downloaded payloads unless there is an explicit policy to do so.
- Keep index/manifest files separate from raw binaries.

## Step-By-Step Execution Plan

### Step 1: Bootstrap The Project Shell

Actions:

1. Create the directory structure above.
2. Add a `.gitignore` for `.auth/`, `output/`, `.playwright-cli/`, and large raw data paths.
3. Initialize a Node project if you plan to script parsing or manifests.
4. Record the confirmed site facts in `docs/field-notes.md`.

Suggested commands:

```powershell
New-Item -ItemType Directory -Force docs, scripts, data, data\index, data\raw, output, output\playwright, .auth, .auth\profile
npm init -y
```

Exit criteria:

- Repeatable folder layout exists.
- Local project can store auth, logs, metadata, and raw files separately.

### Step 2: Capture A Reusable Authenticated Session

Purpose:

- Avoid re-entering credentials on every run.
- Make discovery and download flows scriptable after the first manual sign-in.

Primary method:

```powershell
npx --yes --package @playwright/cli playwright-cli open https://techdata.iihs.org/ --headed --persistent --profile .auth\profile
npx --yes --package @playwright/cli playwright-cli snapshot
```

Then:

1. Click the login link in the headed browser.
2. Complete Microsoft sign-in and any MFA manually.
3. After reaching the authenticated TechData area, save state.

```powershell
npx --yes --package @playwright/cli playwright-cli state-save .auth\storage-state.json
```

Fallback:

- If the Playwright MCP browser fails to launch on this machine, continue with the CLI path above.
- If `storage-state.json` becomes unstable because of the identity provider, prefer the persistent profile directory `.auth\profile`.

Exit criteria:

- One authenticated browser profile.
- One saved storage-state file.
- A short note in `docs/field-notes.md` describing whether MFA, forced re-login, or consent prompts appear.

### Step 3: Reverse-Engineer The Small Overlap List Flow

Purpose:

- Find the exact authenticated route, filter controls, pagination behavior, and file group link pattern for both small-overlap categories.

Actions:

1. Open the logged-in search or downloads page.
2. Take a Playwright snapshot before touching filters.
3. Select `Small overlap frontal: driver-side`.
4. Snapshot again and capture network activity.
5. Repeat for `Small overlap frontal: passenger-side`.
6. Record:
   - Current page URL after filter selection
   - Whether the page reloads or updates via XHR
   - Pagination or lazy-load behavior
   - Exact element refs or DOM markers that identify each file group row

Useful commands:

```powershell
npx --yes --package @playwright/cli playwright-cli snapshot --filename output\playwright\pre-filter.md
npx --yes --package @playwright/cli playwright-cli network --clear
npx --yes --package @playwright/cli playwright-cli snapshot --filename output\playwright\driver-side.md
npx --yes --package @playwright/cli playwright-cli network > output\playwright\driver-side-network.txt
```

Decision rule:

- If an authenticated JSON/XHR endpoint exists for result lists, use it for discovery.
- If not, keep discovery browser-driven with Playwright and DOM parsing.

Exit criteria:

- One confirmed discovery path for `driver-side`.
- One confirmed discovery path for `passenger-side`.
- One note describing whether pagination is page-based, date-based, or infinite scroll.

### Step 4: Build The Historical File Group Index

Purpose:

- Create a complete metadata inventory before downloading binaries.

Per file group, capture at minimum:

- `filegroup_id`
- `test_type`
- `title`
- `test_code`
- `vehicle_year`
- `vehicle_make_model`
- `tested_on`
- `detail_url`
- `discovered_at`
- `source` (`ui-scan` or `rss`)

Rules:

- Treat `filegroup_id` as the primary key if present.
- Store every discovery event, but dedupe the current index on `filegroup_id`.
- Do not start mass file downloads until the historical index looks complete.

Recommended outputs:

- `data/index/filegroups.jsonl`
- `data/index/manifest.sqlite`

Exit criteria:

- Historical index contains both small-overlap categories.
- No duplicate current rows by `filegroup_id`.

### Step 5: Reverse-Engineer The File Group Download Flow

Purpose:

- Determine whether files can be downloaded by authenticated HTTP requests or only by browser click flow.

Actions per sample file group:

1. Open one known small-overlap detail page.
2. Expand several folders in the left tree.
3. Observe how the right pane loads file lists.
4. Click one small file and inspect the resulting network request.
5. Record:
   - Direct file URL pattern, if any
   - Required cookies or headers
   - Whether downloads are normal responses or generated links

Decision rule:

- Prefer authenticated direct HTTP download if the request pattern is stable.
- Fall back to Playwright-driven clicks only if direct download cannot be reproduced safely.

Exit criteria:

- One stable file download method selected.
- One sample file downloaded end-to-end and written to disk.

### Step 6: Implement The Downloader

Downloader responsibilities:

1. Read pending file groups from the index.
2. Open each file group detail page.
3. Enumerate folder nodes and files.
4. Download each file into a deterministic path.
5. Write file-level metadata and checksum.
6. Mark the file group complete only when every listed file is downloaded successfully.

Recommended target path:

```text
data/raw/{normalized-test-type}/{filegroup-id}-{test-code}/{folder-path}/{filename}
```

Minimum file manifest fields:

- `filegroup_id`
- `relative_path`
- `filename`
- `source_url` or `download_action`
- `size_bytes`
- `sha256`
- `downloaded_at`
- `status`

Idempotency rules:

- Skip files whose checksum already matches.
- Re-download files with zero bytes, partial size, or checksum mismatch.
- Keep incomplete runs resumable.

### Step 7: Add Incremental Sync From RSS

Use RSS only for updates after the historical index exists.

Why:

- The sample RSS shows only daily updates, not a full archive guarantee.
- Historical backfill must come from the authenticated UI or authenticated endpoints.

Incremental process:

1. Fetch the RSS feed daily.
2. Parse each item.
3. Keep only links related to the small-overlap categories.
4. For each matching update:
   - enqueue the `filegroup` or `updated date` page
   - refresh metadata
   - re-download changed files if the file group changed

Matching rule:

- Accept titles beginning with `Small overlap frontal: driver-side`
- Accept titles beginning with `Small overlap frontal: passenger-side`

Outputs:

- `data/index/rss-items.jsonl`
- appended sync logs in `output/playwright/` or `output/logs/`

### Step 8: Validation And Reconciliation

Checks after each major run:

1. Count discovered file groups by type.
2. Count downloaded file groups by type.
3. Compare folder/file counts against the live detail page for a random sample.
4. Verify no zero-byte files remain.
5. Re-open a random completed file group and confirm manifest parity.

Monthly reconciliation:

1. Re-run a full authenticated discovery scan.
2. Diff against the manifest.
3. Queue missing or changed file groups.

### Step 9: Operational Hardening

Add these only after the manual workflow is stable.

1. Structured logs for discovery and downloads.
2. Retry with backoff for transient HTTP or browser failures.
3. Session health checks before long runs.
4. A lock file so two bulk runs do not collide.
5. Rate limiting to avoid hammering the site.

## Recommended Script Breakdown

Implement in this order.

1. `scripts/capture-session.ps1`
   Opens the site in headed mode and saves session state.
2. `scripts/discover-small-overlap.mjs`
   Builds the historical file group index.
3. `scripts/download-filegroup.mjs`
   Downloads all files for one file group and writes manifest rows.
4. `scripts/sync-rss.mjs`
   Polls RSS and schedules incremental refresh.

## MCP And Skill Playbook

Use this sequence while building.

1. `playwright` skill
   Capture login flow, snapshots, and network evidence.
2. `shell_command`
   Persist command lines and redirect artifacts to files.
3. `js_repl`
   Parse RSS XML, normalize titles, and generate test manifests quickly in Node.
4. `web`
   Validate only public pages and public RSS details when auth is not required.

Do not start with raw HTTP guessing. First prove the browser flow, then replace only the stable parts with direct requests.

## First Run Checklist

- Account works.
- Permission decision is documented.
- Persistent Playwright profile works.
- One small-overlap driver-side file group can be indexed.
- One small-overlap passenger-side file group can be indexed.
- One sample file can be downloaded and checksummed.
- Historical index is being written separately from raw files.
- RSS incremental logic is disabled until the historical backfill is proven.

## Authenticated Findings To Encode In Scripts

- Driver-side list URL:
  - `https://techdata.iihs.org/secure/filegroups.aspx?t=25&r=released`
- Passenger-side list URL:
  - `https://techdata.iihs.org/secure/filegroups.aspx?t=26&r=released`
- Observed page counts on March 6, 2026:
  - driver-side: `15` list pages
  - passenger-side: `3` list pages
- Example authenticated detail page:
  - `https://techdata.iihs.org/secure/filegroup.aspx?2589`
- Example folder contents on that detail page:
  - `Root`
  - `DATA\DAS`
  - `DATA\DIAdem`
  - `DATA\EDR`
  - `DATA\EXCEL`
  - `PHOTOS`
  - `REPORTS`
  - `VIDEO`
- Example folder pagination:
  - `PHOTOS` on filegroup `2589` shows `9` pages of files
- Example file response:
  - authenticated `fetch('/secure/file.ashx?...')` returned `200`
  - response `Content-Type` was `image/jpeg`
  - response `Content-Disposition` was `inline; filename=CN15007#01_w.jpg`

## Immediate Next Action

Before writing the actual downloader, spend one focused session on Step 3 and Step 5 only. The most important unknowns are:

- how the authenticated result list is populated
- how folder/file panes are loaded
- whether file downloads can be replayed without browser clicks

Once those three points are confirmed, implementation becomes straightforward.
