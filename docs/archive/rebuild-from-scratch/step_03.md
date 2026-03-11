# Step 03. 공통 로그 모듈 작성

이 단계에서는 `scripts/lib/logging.mjs`를 만든다.  
이 파일은 discovery와 download의 공통 로그 출력을 담당한다.

## 생성할 파일

- `scripts/lib/logging.mjs`

## 이 파일이 반드시 제공해야 하는 기능

- ISO 시각 문자열 생성
- 실행 단위 `runId` 생성
- Error 객체를 JSON 직렬화 가능한 평면 구조로 정규화
- 텍스트 로그와 JSONL 로그를 동시에 기록
- 표준출력에도 같은 메시지를 남김

## 로그 출력 위치

이 모듈은 로그를 항상 아래 경로에 써야 한다.

- `output/logs/{runId}.log`
- `output/logs/{runId}.jsonl`

## 파일 작성 내용

아래 코드와 동일한 기능으로 작성한다.

```js
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
```

## 구현 포인트

- `safeSerialize`는 순환참조 등으로 `JSON.stringify`가 실패해도 로그를 깨뜨리지 않아야 한다.
- `createLogger`는 항상 `output/logs`를 먼저 만든다.
- 로그는 파일 기록과 콘솔 기록을 동시에 해야 한다.
- `close()`를 호출하지 않으면 버퍼가 flush되지 않을 수 있으므로, 상위 스크립트에서 `finally` 블록에서 닫아야 한다.

## 자체 검증

아래 임시 검증 코드를 실행한다.

```powershell
@'
import { createLogger } from "./scripts/lib/logging.mjs";

const logger = await createLogger({ name: "smoke-log" });
logger.info("hello", { ok: true });
await logger.close();
'@ | node -
```

성공 조건:

- `output/logs/` 아래에 `smoke-log-*.log`, `smoke-log-*.jsonl` 생성
- 두 파일 모두 비어 있지 않음

검증 후 생성된 테스트 로그는 지워도 된다.
