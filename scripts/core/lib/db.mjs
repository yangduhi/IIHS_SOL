import fsp from 'node:fs/promises';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';

const SCHEMA_SQL = `
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  script_name TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  summary_json TEXT,
  log_path TEXT,
  jsonl_log_path TEXT
);

CREATE TABLE IF NOT EXISTS filegroups (
  filegroup_id INTEGER PRIMARY KEY,
  test_type_code INTEGER NOT NULL,
  test_type_label TEXT NOT NULL,
  title TEXT NOT NULL,
  test_code TEXT,
  vehicle_year INTEGER,
  vehicle_make_model TEXT,
  tested_on TEXT,
  detail_url TEXT NOT NULL,
  discovered_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  source TEXT NOT NULL,
  list_page INTEGER,
  download_status TEXT NOT NULL DEFAULT 'pending',
  folder_count INTEGER NOT NULL DEFAULT 0,
  file_count INTEGER NOT NULL DEFAULT 0,
  downloaded_file_count INTEGER NOT NULL DEFAULT 0,
  excluded_file_count INTEGER NOT NULL DEFAULT 0,
  data_root TEXT,
  last_error TEXT
);

CREATE TABLE IF NOT EXISTS folders (
  filegroup_id INTEGER NOT NULL,
  folder_path TEXT NOT NULL,
  is_excluded INTEGER NOT NULL DEFAULT 0,
  exclusion_reason TEXT,
  bulk_download_url TEXT,
  listed_page_count INTEGER NOT NULL DEFAULT 1,
  listed_file_count INTEGER NOT NULL DEFAULT 0,
  enumerated_at TEXT,
  PRIMARY KEY (filegroup_id, folder_path),
  FOREIGN KEY (filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS files (
  file_id INTEGER PRIMARY KEY AUTOINCREMENT,
  filegroup_id INTEGER NOT NULL,
  folder_path TEXT NOT NULL,
  filename TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  listed_on_page INTEGER NOT NULL DEFAULT 1,
  modified_label TEXT,
  size_label TEXT,
  source_url TEXT NOT NULL,
  content_type TEXT,
  content_disposition TEXT,
  size_bytes INTEGER,
  sha256 TEXT,
  local_path TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  excluded_reason TEXT,
  downloaded_at TEXT,
  last_error TEXT,
  UNIQUE (filegroup_id, folder_path, filename, source_url),
  FOREIGN KEY (filegroup_id) REFERENCES filegroups(filegroup_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_filegroups_download_status ON filegroups(download_status, test_type_code, filegroup_id);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status, filegroup_id);
CREATE INDEX IF NOT EXISTS idx_files_filegroup ON files(filegroup_id, folder_path);
`;

function tableOrder(tableName) {
  switch (tableName) {
    case 'filegroups':
      return 'ORDER BY test_type_code, filegroup_id';
    case 'folders':
      return 'ORDER BY filegroup_id, folder_path';
    case 'files':
      return 'ORDER BY filegroup_id, folder_path, filename';
    default:
      return '';
  }
}

export async function openManifestDatabase(dbPath = path.resolve('data/index/manifest.sqlite')) {
  await fsp.mkdir(path.dirname(dbPath), { recursive: true });
  const db = new DatabaseSync(dbPath);
  db.exec(SCHEMA_SQL);
  return db;
}

export function recordRunStart(db, { runId, scriptName, startedAt, logPath, jsonlLogPath }) {
  db.prepare(`
    INSERT INTO runs (run_id, script_name, started_at, status, log_path, jsonl_log_path)
    VALUES (?, ?, ?, 'running', ?, ?)
  `).run(runId, scriptName, startedAt, logPath, jsonlLogPath);
}

export function recordRunFinish(db, { runId, finishedAt, status, summary }) {
  db.prepare(`
    UPDATE runs
       SET finished_at = ?,
           status = ?,
           summary_json = ?
     WHERE run_id = ?
  `).run(finishedAt, status, summary ? JSON.stringify(summary) : null, runId);
}

export async function exportTableToJsonl(db, tableName, outputPath) {
  const rows = db.prepare(`SELECT * FROM ${tableName} ${tableOrder(tableName)}`).all();
  const content = rows.map((row) => JSON.stringify(row)).join('\n');
  await fsp.mkdir(path.dirname(outputPath), { recursive: true });
  await fsp.writeFile(outputPath, content ? `${content}\n` : '', 'utf8');
}

export async function exportManifestSnapshots(db) {
  await exportTableToJsonl(db, 'filegroups', path.resolve('data/index/filegroups.jsonl'));
  await exportTableToJsonl(db, 'folders', path.resolve('data/index/folders.jsonl'));
  await exportTableToJsonl(db, 'files', path.resolve('data/index/files.jsonl'));
}
