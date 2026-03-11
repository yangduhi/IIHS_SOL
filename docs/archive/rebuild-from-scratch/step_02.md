# Step 02. 기본 디렉터리와 패키지 구성

이 단계의 목표는 현재 저장소와 동일한 기본 골격을 만드는 것이다.

## 만들어야 할 디렉터리

아래 디렉터리를 정확히 만든다.

```powershell
New-Item -ItemType Directory -Force docs
New-Item -ItemType Directory -Force scripts
New-Item -ItemType Directory -Force scripts\lib
New-Item -ItemType Directory -Force data
New-Item -ItemType Directory -Force data\index
New-Item -ItemType Directory -Force data\raw
New-Item -ItemType Directory -Force output
New-Item -ItemType Directory -Force output\logs
New-Item -ItemType Directory -Force output\playwright
New-Item -ItemType Directory -Force output\playwright\errors
New-Item -ItemType Directory -Force .auth
New-Item -ItemType Directory -Force .auth\profile
```

## `.gitignore` 만들기

파일명: `.gitignore`

권장 내용:

```gitignore
.auth/
.venv/
.playwright-cli/
output/
data/raw/
node_modules/
__pycache__/
.pytest_cache/
.ai/runlog/reports/
docs/changes/
docs/conversations/
docs/sessions/
docs/reports/
```

설명:

- `.auth/`: 브라우저 세션과 저장 상태가 들어간다.
- `output/`: 로그와 Playwright 아티팩트가 쌓인다.
- `data/raw/`: 실제 다운로드 파일이 매우 커질 수 있다.
- `node_modules/`: 표준 제외 대상이다.

## `package.json` 만들기

파일명: `package.json`

현재 저장소 기준 내용:

```json
{
  "name": "iihs-sol",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "directories": {
    "doc": "docs"
  },
  "scripts": {
    "discover": "node scripts/discover-small-overlap.mjs",
    "download:pending": "node scripts/download-filegroup.mjs --pending",
    "backfill": "npm run discover && npm run download:pending"
  },
  "keywords": [],
  "author": "",
  "license": "ISC",
  "type": "commonjs",
  "dependencies": {
    "fast-xml-parser": "^5.4.2",
    "playwright": "^1.58.2"
  }
}
```

중요:

- `type`은 `commonjs`로 둔다.
- 실제 `.mjs` 파일은 ES module로 동작하므로 `package.json`의 `type` 값 때문에 깨지지 않는다.
- `fast-xml-parser`는 현재 구현에서 핵심 경로는 아니지만, 향후 RSS 확장을 염두에 두고 현재 저장소와 동일하게 넣는다.

## 의존성 설치

```powershell
npm install
```

실행 후 기대 결과:

- `node_modules/` 생성
- `package-lock.json` 생성
- `playwright` 패키지 설치

## Playwright 패키지 확인

```powershell
@'
const pkg = require("./package.json");
console.log(pkg.dependencies);
'@ | node -
```

추가로 CLI 패키지가 호출 가능한지 확인한다.

```powershell
npx --yes --package @playwright/cli playwright-cli --help
```

여기서 도움말이 출력되면 `capture-session.ps1`에서 동일한 호출 방식을 쓸 수 있다.

## 현재 단계에서 아직 만들지 않는 것

- `.auth\storage-state.json`
- `data\index\manifest.sqlite`
- `data\index\filegroups.jsonl`
- `data\index\folders.jsonl`
- `data\index\files.jsonl`

이 파일들은 이후 스크립트를 실행해야 생성된다.

## 이 단계 종료 체크리스트

- 디렉터리 구조가 준비되었다.
- `.gitignore`가 만들어졌다.
- `package.json`이 저장되었다.
- `npm install`이 성공했다.
- `package-lock.json`이 생성되었다.
- `npx --yes --package @playwright/cli playwright-cli --help`가 동작한다.
