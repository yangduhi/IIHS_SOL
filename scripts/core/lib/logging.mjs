import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';

function safeSerialize(data) {
  if (data === undefined) {
    return '';
  }

  try {
    return JSON.stringify(data);
  } catch (error) {
    return JSON.stringify({ serializationError: String(error), fallback: String(data) });
  }
}

export function nowIso() {
  return new Date().toISOString();
}

export function makeRunId(name) {
  return `${name}-${nowIso().replace(/[:.]/g, '').replace('T', '-').replace('Z', '')}`;
}

export function normalizeError(error) {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack,
    };
  }

  return {
    message: String(error),
  };
}

export async function createLogger({ name }) {
  const logsDir = path.resolve('output/logs');
  await fsp.mkdir(logsDir, { recursive: true });

  const runId = makeRunId(name);
  const textPath = path.join(logsDir, `${runId}.log`);
  const jsonlPath = path.join(logsDir, `${runId}.jsonl`);
  const textStream = fs.createWriteStream(textPath, { flags: 'a' });
  const jsonlStream = fs.createWriteStream(jsonlPath, { flags: 'a' });

  const write = (level, message, data) => {
    const ts = nowIso();
    const line = `[${ts}] [${level}] ${message}`;
    const serialized = data === undefined ? '' : ` | ${safeSerialize(data)}`;
    textStream.write(`${line}${serialized}\n`);
    jsonlStream.write(`${JSON.stringify({ ts, level, message, data: data ?? null })}\n`);

    if (level === 'ERROR') {
      console.error(line, data ?? '');
      return;
    }

    if (level === 'WARN') {
      console.warn(line, data ?? '');
      return;
    }

    console.log(line, data ?? '');
  };

  return {
    runId,
    paths: {
      textPath,
      jsonlPath,
    },
    debug(message, data) {
      write('DEBUG', message, data);
    },
    info(message, data) {
      write('INFO', message, data);
    },
    warn(message, data) {
      write('WARN', message, data);
    },
    error(message, data) {
      write('ERROR', message, data);
    },
    async close() {
      await Promise.all([
        new Promise((resolve) => textStream.end(resolve)),
        new Promise((resolve) => jsonlStream.end(resolve)),
      ]);
    },
  };
}
