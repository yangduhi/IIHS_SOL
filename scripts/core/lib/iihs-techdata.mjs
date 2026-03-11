import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

export const ROOT_URL = 'https://techdata.iihs.org';
export const PROFILE_DIR = path.resolve('.auth/profile');
export const STORAGE_STATE_PATH = path.resolve('.auth/storage-state.json');
export const ERROR_ARTIFACTS_DIR = path.resolve('output/playwright/errors');
export const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.avi', '.wmv', '.mkv', '.webm']);
export const PHOTO_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif']);

export const SMALL_OVERLAP_TYPES = [
  { code: 25, label: 'Small overlap frontal: driver-side', slug: 'small-overlap-driver-side' },
  { code: 26, label: 'Small overlap frontal: passenger-side', slug: 'small-overlap-passenger-side' },
];

export function buildListUrl(typeCode) {
  return `${ROOT_URL}/secure/filegroups.aspx?t=${typeCode}&r=released`;
}

export function buildDetailUrl(filegroupId) {
  return `${ROOT_URL}/secure/filegroup.aspx?${filegroupId}`;
}

export function sanitizePathSegment(value) {
  return String(value ?? '')
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\.+$/g, '')
    .slice(0, 180) || 'unnamed';
}

export function normalizeFolderPath(folderPath) {
  const raw = String(folderPath ?? '').trim();
  if (!raw || raw.toUpperCase() === 'ROOT') {
    return 'ROOT';
  }

  return raw.replace(/\//g, '\\');
}

export function isVideoPath(folderPath, filename = '') {
  const normalizedFolder = normalizeFolderPath(folderPath).toUpperCase();
  const ext = path.extname(String(filename ?? '')).toLowerCase();

  if (normalizedFolder === 'VIDEO') {
    return true;
  }

  if (normalizedFolder.startsWith('VIDEO\\')) {
    return true;
  }

  if (normalizedFolder.includes('\\VIDEO\\') || normalizedFolder.includes('/VIDEO/')) {
    return true;
  }

  return VIDEO_EXTENSIONS.has(ext);
}

export function isPhotoPath(folderPath, filename = '') {
  const normalizedFolder = normalizeFolderPath(folderPath).toUpperCase();
  const ext = path.extname(String(filename ?? '')).toLowerCase();

  if (normalizedFolder === 'PHOTOS') {
    return true;
  }

  if (normalizedFolder.startsWith('PHOTOS\\')) {
    return true;
  }

  if (normalizedFolder.includes('\\PHOTOS\\') || normalizedFolder.includes('/PHOTOS/')) {
    return true;
  }

  return PHOTO_EXTENSIONS.has(ext);
}

export function parseListEntry(typeConfig, linkText, href) {
  const trimmedText = String(linkText ?? '').trim();
  const idMatch = String(href ?? '').match(/filegroup\.aspx\?(\d+)/i);
  const splitIndex = trimmedText.indexOf(':');
  const testCode = splitIndex === -1 ? trimmedText : trimmedText.slice(0, splitIndex).trim();
  const vehicle = splitIndex === -1 ? '' : trimmedText.slice(splitIndex + 1).trim();
  const vehicleYearMatch = vehicle.match(/^(\d{4})\b/);

  return {
    filegroupId: idMatch ? Number(idMatch[1]) : null,
    title: `${typeConfig.label} Test ${trimmedText}`,
    testCode,
    vehicleYear: vehicleYearMatch ? Number(vehicleYearMatch[1]) : null,
    vehicleMakeModel: vehicle,
    detailUrl: idMatch ? buildDetailUrl(idMatch[1]) : null,
  };
}

export function parseDetailHeading(headingText) {
  const trimmed = String(headingText ?? '').trim();
  const match = trimmed.match(/^(?<testType>.+?) Test (?<testCode>[^:]+): (?<vehicle>.+)$/);

  if (!match) {
    return {
      title: trimmed,
      testTypeLabel: null,
      testCode: null,
      vehicleMakeModel: null,
      vehicleYear: null,
    };
  }

  const vehicle = match.groups.vehicle.trim();
  const vehicleYearMatch = vehicle.match(/^(\d{4})\b/);

  return {
    title: trimmed,
    testTypeLabel: match.groups.testType.trim(),
    testCode: match.groups.testCode.trim(),
    vehicleMakeModel: vehicle,
    vehicleYear: vehicleYearMatch ? Number(vehicleYearMatch[1]) : null,
  };
}

export function splitModifiedAndSize(metaLine) {
  const trimmed = String(metaLine ?? '').trim();
  if (!trimmed) {
    return { modifiedLabel: null, sizeLabel: null };
  }

  const splitIndex = trimmed.lastIndexOf(',');
  if (splitIndex === -1) {
    return { modifiedLabel: trimmed, sizeLabel: null };
  }

  return {
    modifiedLabel: trimmed.slice(0, splitIndex).trim(),
    sizeLabel: trimmed.slice(splitIndex + 1).trim(),
  };
}

export function filegroupDataRoot(typeConfig, filegroupId, testCode) {
  return path.resolve('data/raw', typeConfig.slug, `${filegroupId}-${sanitizePathSegment(testCode)}`);
}

export function absoluteFileUrl(relativeUrl) {
  return new URL(relativeUrl, ROOT_URL).toString();
}

export async function ensureAuthenticated(page) {
  const bodyText = await page.locator('body').innerText();
  if (/You are not logged in\./i.test(bodyText)) {
    throw new Error('Authenticated session is no longer valid.');
  }
}

export async function hashFile(filePath) {
  const buffer = await fs.readFile(filePath);
  return createHash('sha256').update(buffer).digest('hex');
}

export async function captureErrorArtifacts(page, label) {
  await fs.mkdir(ERROR_ARTIFACTS_DIR, { recursive: true });
  const safeLabel = sanitizePathSegment(label);
  const base = path.join(ERROR_ARTIFACTS_DIR, `${new Date().toISOString().replace(/[:.]/g, '')}-${safeLabel}`);
  const htmlPath = `${base}.html`;
  const pngPath = `${base}.png`;
  await fs.writeFile(htmlPath, await page.content(), 'utf8');
  await page.screenshot({ path: pngPath, fullPage: true });
  return { htmlPath, pngPath };
}

export async function waitForPostback(page, action) {
  const responsePromise = page.waitForResponse(
    (response) => response.request().method() === 'POST' && /filegroup|filegroups/i.test(response.url()),
    { timeout: 30000 }
  ).catch(() => null);

  await action();
  await responsePromise;
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(100);
}
