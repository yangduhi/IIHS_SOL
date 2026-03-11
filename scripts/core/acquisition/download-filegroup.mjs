import { request, chromium } from 'playwright';
import { createHash } from 'node:crypto';
import fsp from 'node:fs/promises';
import path from 'node:path';

import { exportManifestSnapshots, openManifestDatabase, recordRunFinish, recordRunStart } from '../lib/db.mjs';
import { createLogger, normalizeError, nowIso } from '../lib/logging.mjs';
import {
  SMALL_OVERLAP_TYPES,
  ROOT_URL,
  STORAGE_STATE_PATH,
  absoluteFileUrl,
  captureErrorArtifacts,
  ensureAuthenticated,
  filegroupDataRoot,
  hashFile,
  isPhotoPath,
  isVideoPath,
  normalizeFolderPath,
  parseDetailHeading,
  sanitizePathSegment,
  splitModifiedAndSize,
  waitForPostback,
} from '../lib/iihs-techdata.mjs';

function parseArgs(argv) {
  const args = {
    pending: false,
    filegroupId: null,
    limit: null,
    concurrency: 3,
  };

  for (const arg of argv) {
    if (arg === '--pending') {
      args.pending = true;
    } else if (arg.startsWith('--filegroup-id=')) {
      args.filegroupId = Number(arg.slice('--filegroup-id='.length));
    } else if (arg.startsWith('--limit=')) {
      args.limit = Number(arg.slice('--limit='.length));
    } else if (arg.startsWith('--concurrency=')) {
      args.concurrency = Number(arg.slice('--concurrency='.length));
    }
  }

  if (!args.pending && !args.filegroupId) {
    args.pending = true;
  }

  return args;
}

function typeByCode(typeCode) {
  const found = SMALL_OVERLAP_TYPES.find((typeConfig) => typeConfig.code === typeCode);
  if (!found) {
    throw new Error(`Unsupported type code: ${typeCode}`);
  }
  return found;
}

function getPendingFilegroups(db, args) {
  if (args.filegroupId) {
    return db.prepare('SELECT * FROM filegroups WHERE filegroup_id = ?').all(args.filegroupId);
  }

  if (args.limit) {
    return db.prepare(`
      SELECT *
        FROM filegroups
       WHERE download_status IN ('pending', 'error', 'downloading')
       ORDER BY test_type_code, filegroup_id
       LIMIT ?
    `).all(args.limit);
  }

  return db.prepare(`
    SELECT *
      FROM filegroups
     WHERE download_status IN ('pending', 'error', 'downloading')
     ORDER BY test_type_code, filegroup_id
  `).all();
}

async function mapWithConcurrency(items, limit, worker) {
  const results = new Array(items.length);
  let nextIndex = 0;

  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (true) {
      const currentIndex = nextIndex;
      nextIndex += 1;

      if (currentIndex >= items.length) {
        return;
      }

      results[currentIndex] = await worker(items[currentIndex], currentIndex);
    }
  });

  await Promise.all(runners);
  return results;
}

async function ensureFilePage(page, pageNumber) {
  const select = page.locator('#ctl00_MainContentPlaceholder_FileBrowser_PageSelector_ddPages');
  if (!(await select.count()) || pageNumber === 1) {
    return;
  }

  await waitForPostback(page, async () => {
    await select.selectOption(String(pageNumber));
  });
}

async function clickFolderByIndex(page, folderIndex) {
  const folderLinks = page.locator('#ctl00_MainContentPlaceholder_FileBrowser_FolderList li a');
  await waitForPostback(page, async () => {
    await folderLinks.nth(folderIndex).click();
  });
}

async function readFolders(page) {
  return page.locator('#ctl00_MainContentPlaceholder_FileBrowser_FolderList li a').evaluateAll((nodes) => (
    nodes.map((node, index) => ({
      index,
      folderPath: node.textContent?.trim() ?? '',
    })).filter((entry) => entry.folderPath)
  ));
}

async function readCurrentFiles(page, folderPath, pageNumber) {
  return page.locator('#ctl00_MainContentPlaceholder_FileBrowser_FilesList li').evaluateAll((nodes, context) => (
    nodes.map((node) => {
      const link = node.querySelector('a');
      const parts = (node.innerText ?? '').split(/\n+/).map((value) => value.trim()).filter(Boolean);
      return {
        folderPath: context.folderPath,
        listedOnPage: context.pageNumber,
        filename: link?.textContent?.trim() ?? '',
        sourceUrl: link?.getAttribute('href') ?? '',
        metaLine: parts.slice(1).join(' '),
      };
    }).filter((entry) => entry.filename && entry.sourceUrl)
  ), { folderPath, pageNumber });
}

function resolveLocalFilePath(filegroup, folderPath, filename) {
  const typeConfig = typeByCode(filegroup.test_type_code);
  const baseDir = filegroupDataRoot(typeConfig, filegroup.filegroup_id, filegroup.test_code || `fg-${filegroup.filegroup_id}`);
  const normalizedFolder = normalizeFolderPath(folderPath);
  const folderSegments = normalizedFolder === 'ROOT'
    ? []
    : normalizedFolder.split('\\').map((segment) => sanitizePathSegment(segment));
  return path.join(baseDir, ...folderSegments, sanitizePathSegment(filename));
}

async function writeBufferAtomically(filePath, buffer) {
  await fsp.mkdir(path.dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.part`;
  await fsp.writeFile(tempPath, buffer);
  await fsp.rename(tempPath, filePath);
}

function sha256ForBuffer(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

function bufferStartsWith(buffer, text) {
  if (!Buffer.isBuffer(buffer)) {
    return false;
  }
  return buffer.subarray(0, text.length).equals(Buffer.from(text, 'utf8'));
}

function looksLikeHtml(buffer) {
  if (!Buffer.isBuffer(buffer)) {
    return false;
  }
  const head = buffer.subarray(0, 256).toString('utf8').trimStart().toLowerCase();
  return head.startsWith('<!doctype html') || head.startsWith('<html');
}

function looksLikePdf(buffer) {
  return bufferStartsWith(buffer, '%PDF-');
}

async function isExistingPdfValid(localPath) {
  const handle = await fsp.open(localPath, 'r');
  try {
    const sample = Buffer.alloc(256);
    const { bytesRead } = await handle.read(sample, 0, sample.length, 0);
    const head = sample.subarray(0, bytesRead);
    return looksLikePdf(head) && !looksLikeHtml(head);
  } finally {
    await handle.close();
  }
}

const args = parseArgs(process.argv.slice(2));
const logger = await createLogger({ name: 'download-small-overlap' });
const db = await openManifestDatabase();
const startedAt = nowIso();

recordRunStart(db, {
  runId: logger.runId,
  scriptName: 'download-filegroup',
  startedAt,
  logPath: logger.paths.textPath,
  jsonlLogPath: logger.paths.jsonlPath,
});

const summary = {
  filegroupsAttempted: 0,
  filegroupsDownloaded: 0,
  filesDownloaded: 0,
  filesSkippedExisting: 0,
  filesExcluded: 0,
  fileErrors: 0,
};

const updateFilegroupStatus = db.prepare(`
  UPDATE filegroups
     SET download_status = ?,
         tested_on = COALESCE(?, tested_on),
         title = COALESCE(?, title),
         test_code = COALESCE(?, test_code),
         vehicle_year = COALESCE(?, vehicle_year),
         vehicle_make_model = COALESCE(?, vehicle_make_model),
         data_root = COALESCE(?, data_root),
         last_error = ?
   WHERE filegroup_id = ?
`);

function replaceFilegroupStructure(filegroupId, folders, files) {
  const insertFolder = db.prepare(`
    INSERT INTO folders (
      filegroup_id,
      folder_path,
      is_excluded,
      exclusion_reason,
      bulk_download_url,
      listed_page_count,
      listed_file_count,
      enumerated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const insertFile = db.prepare(`
    INSERT INTO files (
      filegroup_id,
      folder_path,
      filename,
      relative_path,
      listed_on_page,
      modified_label,
      size_label,
      source_url,
      status,
      excluded_reason
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  db.exec('BEGIN');
  try {
    db.prepare('DELETE FROM folders WHERE filegroup_id = ?').run(filegroupId);
    db.prepare('DELETE FROM files WHERE filegroup_id = ?').run(filegroupId);

    for (const folder of folders) {
      insertFolder.run(
        filegroupId,
        folder.folderPath,
        folder.isExcluded ? 1 : 0,
        folder.exclusionReason,
        folder.bulkDownloadUrl,
        folder.listedPageCount,
        folder.listedFileCount,
        nowIso()
      );
    }

    for (const file of files) {
      insertFile.run(
        filegroupId,
        file.folderPath,
        file.filename,
        file.relativePath,
        file.listedOnPage,
        file.modifiedLabel,
        file.sizeLabel,
        file.sourceUrl,
        file.status,
        file.excludedReason
      );
    }

    db.exec('COMMIT');
  } catch (error) {
    db.exec('ROLLBACK');
    throw error;
  }
}

const updateFileDownload = db.prepare(`
  UPDATE files
     SET content_type = ?,
         content_disposition = ?,
         size_bytes = ?,
         sha256 = ?,
         local_path = ?,
         status = ?,
         downloaded_at = ?,
         last_error = ?
   WHERE filegroup_id = ?
     AND folder_path = ?
     AND filename = ?
     AND source_url = ?
`);

const updateFileError = db.prepare(`
  UPDATE files
     SET status = 'error',
         last_error = ?
   WHERE filegroup_id = ?
     AND folder_path = ?
     AND filename = ?
     AND source_url = ?
`);

const updateFileExisting = db.prepare(`
  UPDATE files
     SET sha256 = ?,
         local_path = ?,
         size_bytes = ?,
         status = 'downloaded',
         downloaded_at = ?,
         last_error = NULL
   WHERE filegroup_id = ?
     AND folder_path = ?
     AND filename = ?
     AND source_url = ?
`);

const hasAuthCredentials = Boolean(process.env.IIHS_TECHDATA_EMAIL && process.env.IIHS_TECHDATA_PASSWORD);

let browser;
let context;
let page;
let api;

async function refreshAuthState() {
  if (!hasAuthCredentials) {
    throw new Error('IIHS_TECHDATA_EMAIL and IIHS_TECHDATA_PASSWORD are required to refresh the auth state.');
  }

  const authBrowser = await chromium.launch({ headless: true });
  const authContext = await authBrowser.newContext();
  const authPage = await authContext.newPage();

  await authPage.goto(ROOT_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  const initialBody = await authPage.locator('body').innerText();

  if (initialBody.includes('You are not logged in.')) {
    await authPage.getByRole('link', { name: 'Log in to IIHS TechData' }).click();
    await authPage.waitForLoadState('domcontentloaded');
    await authPage.getByRole('textbox', { name: /User account/i }).fill(process.env.IIHS_TECHDATA_EMAIL);
    await authPage.getByRole('textbox', { name: /Password/i }).fill(process.env.IIHS_TECHDATA_PASSWORD);
    const keepSignedIn = authPage.getByRole('checkbox', { name: /Keep me signed in/i });
    if (await keepSignedIn.count()) {
      if (!(await keepSignedIn.isChecked())) {
        await keepSignedIn.check();
      }
    }
    await authPage.getByRole('button', { name: /Sign in/i }).click();
  }

  await authPage.waitForURL(/https:\/\/techdata\.iihs\.org\/(?:default\.aspx)?$/i, { timeout: 120000 });
  await authPage.waitForLoadState('networkidle');
  await authContext.storageState({ path: STORAGE_STATE_PATH });
  await authContext.close();
  await authBrowser.close();
  logger.info('auth state refreshed');
}

async function openRuntimeContexts() {
  browser = await chromium.launch({ headless: true });
  context = await browser.newContext({ storageState: STORAGE_STATE_PATH });
  await context.route('**/*', (route) => {
    const resourceType = route.request().resourceType();
    if (['image', 'media', 'font', 'stylesheet'].includes(resourceType)) {
      route.abort().catch(() => {});
      return;
    }

    route.continue().catch(() => {});
  });
  page = await context.newPage();
  api = await request.newContext({ storageState: STORAGE_STATE_PATH });
}

async function closeRuntimeContexts() {
  await page?.close().catch(() => {});
  await context?.close().catch(() => {});
  await browser?.close().catch(() => {});
  await api?.dispose().catch(() => {});
  browser = undefined;
  context = undefined;
  page = undefined;
  api = undefined;
}

try {
  const pendingFilegroups = getPendingFilegroups(db, args);
  if (!pendingFilegroups.length) {
    logger.info('no pending filegroups found');
    recordRunFinish(db, {
      runId: logger.runId,
      finishedAt: nowIso(),
      status: 'success',
      summary,
    });
    db.close();
    await logger.close();
    process.exit(0);
  }

  if (hasAuthCredentials) {
    await refreshAuthState();
  }
  await openRuntimeContexts();

  for (const filegroup of pendingFilegroups) {
    summary.filegroupsAttempted += 1;
    const typeConfig = typeByCode(filegroup.test_type_code);
    const dataRoot = filegroupDataRoot(typeConfig, filegroup.filegroup_id, filegroup.test_code || `fg-${filegroup.filegroup_id}`);

    logger.info('filegroup start', {
      filegroupId: filegroup.filegroup_id,
      detailUrl: filegroup.detail_url,
      type: typeConfig.label,
    });

    let completed = false;
    for (let attempt = 1; attempt <= 2 && !completed; attempt += 1) {
      try {
        updateFilegroupStatus.run(
          'downloading',
          filegroup.tested_on,
          filegroup.title,
          filegroup.test_code,
          filegroup.vehicle_year,
          filegroup.vehicle_make_model,
          dataRoot,
          null,
          filegroup.filegroup_id
        );

        await page.goto(filegroup.detail_url, { waitUntil: 'networkidle', timeout: 120000 });
        await ensureAuthenticated(page);

      const bodyLines = (await page.locator('body').innerText())
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);
      const detailTitle = bodyLines.find((line) => line.startsWith('Small overlap frontal:')) ?? filegroup.title;
      const testedOnLine = bodyLines.find((line) => /^Tested on\s+\d{4}-\d{2}-\d{2}$/.test(line)) ?? '';
      const testedOn = testedOnLine.replace(/^Tested on\s+/, '') || filegroup.tested_on;
      const parsedHeading = parseDetailHeading(detailTitle);
      const folders = await readFolders(page);

      const enumeratedFolders = [];
      const enumeratedFiles = [];
      const seenFileKeys = new Set();

      for (const folder of folders) {
        const normalizedFolderPath = normalizeFolderPath(folder.folderPath);
        const folderExcluded = isVideoPath(normalizedFolderPath) || isPhotoPath(normalizedFolderPath);
        const folderRecord = {
          folderPath: normalizedFolderPath,
          isExcluded: folderExcluded,
          exclusionReason: isVideoPath(normalizedFolderPath)
            ? 'video-folder'
            : (isPhotoPath(normalizedFolderPath) ? 'photo-folder' : null),
          bulkDownloadUrl: null,
          listedPageCount: 1,
          listedFileCount: 0,
        };

        if (folderExcluded) {
          summary.filesExcluded += 1;
          enumeratedFolders.push(folderRecord);
          logger.info('folder excluded', {
            filegroupId: filegroup.filegroup_id,
            folderPath: normalizedFolderPath,
          });
          continue;
        }

        await clickFolderByIndex(page, folder.index);

        const bulkLink = page.locator('#ctl00_MainContentPlaceholder_FileBrowser_ZipFileLink');
        if (await bulkLink.count()) {
          folderRecord.bulkDownloadUrl = await bulkLink.getAttribute('href');
        }

        const filePageSelector = page.locator('#ctl00_MainContentPlaceholder_FileBrowser_PageSelector_ddPages');
        const filePageCount = await filePageSelector.count()
          ? await filePageSelector.locator('option').count()
          : 1;
        folderRecord.listedPageCount = filePageCount;

        for (let pageNumber = 1; pageNumber <= filePageCount; pageNumber += 1) {
          await ensureFilePage(page, pageNumber);
          const currentFiles = await readCurrentFiles(page, normalizedFolderPath, pageNumber);

          for (const fileEntry of currentFiles) {
            const meta = splitModifiedAndSize(fileEntry.metaLine);
            const excludedReason = isVideoPath(normalizedFolderPath, fileEntry.filename)
              ? 'video-extension'
              : (isPhotoPath(normalizedFolderPath, fileEntry.filename) ? 'photo-extension' : null);
            const relativePath = path.posix.join(
              ...(normalizedFolderPath === 'ROOT' ? [] : normalizedFolderPath.split('\\').map((segment) => sanitizePathSegment(segment))),
              sanitizePathSegment(fileEntry.filename)
            );
            const fileKey = [
              normalizedFolderPath,
              fileEntry.filename,
              fileEntry.sourceUrl,
            ].join('||');

            if (seenFileKeys.has(fileKey)) {
              logger.warn('duplicate file listing skipped', {
                filegroupId: filegroup.filegroup_id,
                folderPath: normalizedFolderPath,
                filename: fileEntry.filename,
                sourceUrl: fileEntry.sourceUrl,
              });
              continue;
            }

            seenFileKeys.add(fileKey);

            enumeratedFiles.push({
              folderPath: normalizedFolderPath,
              filename: fileEntry.filename,
              relativePath,
              listedOnPage: pageNumber,
              modifiedLabel: meta.modifiedLabel,
              sizeLabel: meta.sizeLabel,
              sourceUrl: fileEntry.sourceUrl,
              status: excludedReason ? 'excluded' : 'pending',
              excludedReason,
            });

            if (excludedReason) {
              summary.filesExcluded += 1;
            }
          }
        }

        folderRecord.listedFileCount = enumeratedFiles.filter((file) => file.folderPath === normalizedFolderPath).length;
        enumeratedFolders.push(folderRecord);
      }

      replaceFilegroupStructure(filegroup.filegroup_id, enumeratedFolders, enumeratedFiles);

      const downloadableFiles = db.prepare(`
        SELECT *
          FROM files
         WHERE filegroup_id = ?
           AND status = 'pending'
         ORDER BY folder_path, filename
      `).all(filegroup.filegroup_id);

      await mapWithConcurrency(downloadableFiles, Math.max(1, args.concurrency), async (fileRow) => {
        const localPath = resolveLocalFilePath(filegroup, fileRow.folder_path, fileRow.filename);
        const absoluteUrl = absoluteFileUrl(fileRow.source_url);

        try {
          const existingStat = await fsp.stat(localPath).catch(() => null);
          if (existingStat?.isFile() && existingStat.size > 0) {
            const shouldValidatePdf = path.extname(fileRow.filename).toLowerCase() === '.pdf';
            if (shouldValidatePdf) {
              const isValidPdf = await isExistingPdfValid(localPath).catch(() => false);
              if (!isValidPdf) {
                logger.warn('existing pdf is invalid, forcing re-download', {
                  filegroupId: filegroup.filegroup_id,
                  filename: fileRow.filename,
                  localPath,
                });
              } else {
                const sha256 = await hashFile(localPath);
                updateFileExisting.run(
                  sha256,
                  localPath,
                  existingStat.size,
                  nowIso(),
                  filegroup.filegroup_id,
                  fileRow.folder_path,
                  fileRow.filename,
                  fileRow.source_url
                );
                summary.filesSkippedExisting += 1;
                logger.info('file exists, skipping download', {
                  filegroupId: filegroup.filegroup_id,
                  filename: fileRow.filename,
                  localPath,
                });
                return;
              }
            } else {
              const sha256 = await hashFile(localPath);
              updateFileExisting.run(
                sha256,
                localPath,
                existingStat.size,
                nowIso(),
                filegroup.filegroup_id,
                fileRow.folder_path,
                fileRow.filename,
                fileRow.source_url
              );
              summary.filesSkippedExisting += 1;
              logger.info('file exists, skipping download', {
                filegroupId: filegroup.filegroup_id,
                filename: fileRow.filename,
                localPath,
              });
              return;
            }
          }

          const response = await api.get(absoluteUrl, { timeout: 120000 });
          if (!response.ok()) {
            throw new Error(`HTTP ${response.status()} for ${absoluteUrl}`);
          }

          const body = await response.body();
          const headers = response.headers();
          const isPdfDownload = path.extname(fileRow.filename).toLowerCase() === '.pdf';
          const contentType = headers['content-type'] ?? null;
          if (isPdfDownload && !looksLikePdf(body)) {
            if (looksLikeHtml(body) || /html/i.test(contentType ?? '')) {
              throw new Error('Authenticated session is no longer valid.');
            }
            throw new Error(`Downloaded file is not a valid PDF: ${fileRow.filename}`);
          }
          const sha256 = sha256ForBuffer(body);
          await writeBufferAtomically(localPath, body);

          updateFileDownload.run(
            contentType,
            headers['content-disposition'] ?? null,
            body.length,
            sha256,
            localPath,
            'downloaded',
            nowIso(),
            null,
            filegroup.filegroup_id,
            fileRow.folder_path,
            fileRow.filename,
            fileRow.source_url
          );
          summary.filesDownloaded += 1;
          logger.info('file downloaded', {
            filegroupId: filegroup.filegroup_id,
            filename: fileRow.filename,
            sizeBytes: body.length,
          });
        } catch (error) {
          summary.fileErrors += 1;
          const normalizedError = normalizeError(error);
          updateFileError.run(
            JSON.stringify(normalizedError),
            filegroup.filegroup_id,
            fileRow.folder_path,
            fileRow.filename,
            fileRow.source_url
          );
          logger.error('file download failed', {
            filegroupId: filegroup.filegroup_id,
            filename: fileRow.filename,
            error: normalizedError,
          });
        }
      });

      const counts = db.prepare(`
        SELECT
          COUNT(*) AS totalFiles,
          SUM(CASE WHEN status = 'downloaded' THEN 1 ELSE 0 END) AS downloadedFiles,
          SUM(CASE WHEN status = 'excluded' THEN 1 ELSE 0 END) AS excludedFiles,
          SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS errorFiles
        FROM files
        WHERE filegroup_id = ?
      `).get(filegroup.filegroup_id);

      db.prepare(`
        UPDATE filegroups
           SET folder_count = ?,
               file_count = ?,
               downloaded_file_count = ?,
               excluded_file_count = ?,
               tested_on = ?,
               title = ?,
               test_code = ?,
               vehicle_year = ?,
               vehicle_make_model = ?,
               data_root = ?,
               download_status = ?,
               last_error = ?
         WHERE filegroup_id = ?
      `).run(
        enumeratedFolders.length,
        counts.totalFiles ?? 0,
        counts.downloadedFiles ?? 0,
        counts.excludedFiles ?? 0,
        testedOn,
        parsedHeading.title || filegroup.title,
        parsedHeading.testCode || filegroup.test_code,
        parsedHeading.vehicleYear || filegroup.vehicle_year,
        parsedHeading.vehicleMakeModel || filegroup.vehicle_make_model,
        dataRoot,
        (counts.errorFiles ?? 0) > 0 ? 'error' : 'downloaded',
        (counts.errorFiles ?? 0) > 0 ? `download errors: ${counts.errorFiles}` : null,
        filegroup.filegroup_id
      );

        if ((counts.errorFiles ?? 0) > 0) {
          logger.warn('filegroup completed with download errors', {
            filegroupId: filegroup.filegroup_id,
            counts,
          });
        } else {
          summary.filegroupsDownloaded += 1;
          logger.info('filegroup complete', {
            filegroupId: filegroup.filegroup_id,
            counts,
          });
        }

        completed = true;
      } catch (error) {
        const normalizedError = normalizeError(error);
        const isAuthError = /Authenticated session is no longer valid/i.test(normalizedError.message || '');

        if (isAuthError && attempt === 1 && hasAuthCredentials) {
          logger.warn('auth expired during download, refreshing and retrying', {
            filegroupId: filegroup.filegroup_id,
          });
          await refreshAuthState();
          await closeRuntimeContexts();
          await openRuntimeContexts();
          continue;
        }

        const artifacts = page ? await captureErrorArtifacts(page, `filegroup-${filegroup.filegroup_id}`).catch(() => null) : null;
        updateFilegroupStatus.run(
          'error',
          filegroup.tested_on,
          filegroup.title,
          filegroup.test_code,
          filegroup.vehicle_year,
          filegroup.vehicle_make_model,
          dataRoot,
          JSON.stringify({ ...normalizedError, artifacts }),
          filegroup.filegroup_id
        );
        logger.error('filegroup failed', {
          filegroupId: filegroup.filegroup_id,
          error: normalizedError,
          artifacts,
        });
        break;
      }
    }
  }

  await exportManifestSnapshots(db);
  recordRunFinish(db, {
    runId: logger.runId,
    finishedAt: nowIso(),
    status: summary.fileErrors > 0 ? 'warning' : 'success',
    summary,
  });
  logger.info('download run complete', summary);
} catch (error) {
  const normalizedError = normalizeError(error);
  recordRunFinish(db, {
    runId: logger.runId,
    finishedAt: nowIso(),
    status: 'error',
    summary: normalizedError,
  });
  logger.error('download run failed', normalizedError);
  process.exitCode = 1;
} finally {
  await closeRuntimeContexts();
  db.close();
  await logger.close();
}
