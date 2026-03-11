import { chromium } from 'playwright';

import { exportManifestSnapshots, openManifestDatabase, recordRunFinish, recordRunStart } from '../lib/db.mjs';
import { createLogger, normalizeError, nowIso } from '../lib/logging.mjs';
import {
  SMALL_OVERLAP_TYPES,
  PROFILE_DIR,
  STORAGE_STATE_PATH,
  buildListUrl,
  ensureAuthenticated,
  parseListEntry,
  waitForPostback,
} from '../lib/iihs-techdata.mjs';

function parseArgs(argv) {
  const args = {
    onlyTypeCodes: null,
    limitPages: null,
  };

  for (const arg of argv) {
    if (arg.startsWith('--types=')) {
      args.onlyTypeCodes = arg
        .slice('--types='.length)
        .split(',')
        .map((value) => Number(value.trim()))
        .filter(Boolean);
    } else if (arg.startsWith('--limit-pages=')) {
      args.limitPages = Number(arg.slice('--limit-pages='.length));
    }
  }

  return args;
}

const args = parseArgs(process.argv.slice(2));
const logger = await createLogger({ name: 'discover-small-overlap' });
const db = await openManifestDatabase();
const startedAt = nowIso();

recordRunStart(db, {
  runId: logger.runId,
  scriptName: 'discover-small-overlap',
  startedAt,
  logPath: logger.paths.textPath,
  jsonlLogPath: logger.paths.jsonlPath,
});

const upsertFilegroup = db.prepare(`
  INSERT INTO filegroups (
    filegroup_id,
    test_type_code,
    test_type_label,
    title,
    test_code,
    vehicle_year,
    vehicle_make_model,
    detail_url,
    discovered_at,
    last_seen_at,
    source,
    list_page,
    download_status
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ui-scan', ?, 'pending')
  ON CONFLICT(filegroup_id) DO UPDATE SET
    test_type_code = excluded.test_type_code,
    test_type_label = excluded.test_type_label,
    title = excluded.title,
    test_code = excluded.test_code,
    vehicle_year = excluded.vehicle_year,
    vehicle_make_model = excluded.vehicle_make_model,
    detail_url = excluded.detail_url,
    last_seen_at = excluded.last_seen_at,
    list_page = excluded.list_page,
    last_error = NULL
`);

const types = args.onlyTypeCodes
  ? SMALL_OVERLAP_TYPES.filter((typeConfig) => args.onlyTypeCodes.includes(typeConfig.code))
  : SMALL_OVERLAP_TYPES;

let context;
let page;

const summary = {
  types: [],
  totalFilegroups: 0,
};

try {
  context = await chromium.launchPersistentContext(PROFILE_DIR, { headless: true });
  await context.storageState({ path: STORAGE_STATE_PATH });
  await context.route('**/*', (route) => {
    const resourceType = route.request().resourceType();
    if (['image', 'media', 'font', 'stylesheet'].includes(resourceType)) {
      route.abort().catch(() => {});
      return;
    }

    route.continue().catch(() => {});
  });
  page = context.pages()[0] || await context.newPage();

  for (const typeConfig of types) {
    await page.goto(buildListUrl(typeConfig.code), { waitUntil: 'networkidle', timeout: 120000 });
    await ensureAuthenticated(page);

    const pageSelector = page.locator('#ctl00_MainContentPlaceholder_PageSelector_ddPages');
    const totalPages = await pageSelector.count()
      ? await pageSelector.locator('option').count()
      : 1;
    const maxPages = args.limitPages ? Math.min(totalPages, args.limitPages) : totalPages;
    const seenIds = new Set();
    let rowsProcessed = 0;

    logger.info('discovery start', {
      typeCode: typeConfig.code,
      typeLabel: typeConfig.label,
      totalPages,
      maxPages,
    });

    for (let pageNumber = 1; pageNumber <= maxPages; pageNumber += 1) {
      if (pageNumber > 1) {
        await waitForPostback(page, async () => {
          await pageSelector.selectOption(String(pageNumber));
        });
      }

      const linkEntries = await page.locator('a[href*="filegroup.aspx?"]').evaluateAll((nodes) => (
        nodes.map((node) => ({
          text: node.textContent?.trim() ?? '',
          href: node.getAttribute('href') ?? '',
        }))
      ));

      logger.info('page scanned', {
        typeCode: typeConfig.code,
        pageNumber,
        linkCount: linkEntries.length,
      });

      for (const linkEntry of linkEntries) {
        const parsed = parseListEntry(typeConfig, linkEntry.text, linkEntry.href);
        if (!parsed.filegroupId || !parsed.detailUrl) {
          logger.warn('skipping malformed list entry', { typeCode: typeConfig.code, pageNumber, linkEntry });
          continue;
        }

        if (seenIds.has(parsed.filegroupId)) {
          logger.warn('duplicate filegroup seen', { filegroupId: parsed.filegroupId, typeCode: typeConfig.code, pageNumber });
        }

        seenIds.add(parsed.filegroupId);
        upsertFilegroup.run(
          parsed.filegroupId,
          typeConfig.code,
          typeConfig.label,
          parsed.title,
          parsed.testCode,
          parsed.vehicleYear,
          parsed.vehicleMakeModel,
          parsed.detailUrl,
          startedAt,
          nowIso(),
          pageNumber
        );
        rowsProcessed += 1;
      }
    }

    summary.types.push({
      typeCode: typeConfig.code,
      typeLabel: typeConfig.label,
      pagesScanned: maxPages,
      uniqueFilegroups: seenIds.size,
      rowsProcessed,
    });
    summary.totalFilegroups += seenIds.size;
  }

  await exportManifestSnapshots(db);
  recordRunFinish(db, {
    runId: logger.runId,
    finishedAt: nowIso(),
    status: 'success',
    summary,
  });
  logger.info('discovery complete', summary);
} catch (error) {
  const normalizedError = normalizeError(error);
  recordRunFinish(db, {
    runId: logger.runId,
    finishedAt: nowIso(),
    status: 'error',
    summary: normalizedError,
  });
  logger.error('discovery failed', normalizedError);
  process.exitCode = 1;
} finally {
  await page?.close().catch(() => {});
  await context?.close().catch(() => {});
  db.close();
  await logger.close();
}
