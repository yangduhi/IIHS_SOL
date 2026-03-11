# Step 11. download 실행, 재개, 장애 대응

이 단계에서는 실제 파일을 다운로드한다.  
처음부터 전체 백필을 돌리지 말고, 반드시 단건 -> 소량 -> 전체 순서로 진행한다.

## 1단계. 단건 검증

샘플 파일그룹 하나만 먼저 실행한다.

```powershell
node .\scripts\download-filegroup.mjs --filegroup-id=1472 --concurrency=2
```

단건 검증에서 봐야 할 것:

- `data/raw/small-overlap-driver-side/1472-CF09004` 하위에 파일이 생기는가
- `output/logs/download-small-overlap-*.log`가 생기는가
- `files` 테이블에 `downloaded`가 생기는가
- `PHOTOS`, `VIDEO`는 모두 제외되는가

## 2단계. 소량 배치 검증

```powershell
node .\scripts\download-filegroup.mjs --pending --limit=3 --concurrency=2
```

이 단계의 목적:

- 인증이 최소 수분 이상 유지되는지
- 여러 파일그룹을 연속으로 처리해도 폴더/파일 목록 적재가 안정적인지
- 기존 파일 재사용 로직이 동작하는지

## 3단계. 전체 대기열 실행

```powershell
npm run download:pending
```

주의:

- 장시간 실행 중 세션이 끊길 수 있다.
- 따라서 야간 배치로 돌리기 전에 반드시 위 2단계까지 성공시킨다.

## 현재 구현의 재개 전략

이 스크립트는 아래 상태를 모두 재대상으로 잡는다.

- `pending`
- `error`
- `downloading`

즉, 중간에 죽어도 별도 복구 스크립트 없이 아래 명령으로 이어서 돌릴 수 있다.

```powershell
node .\scripts\download-filegroup.mjs --pending
```

## 장애 패턴 1. 인증 만료

대표 오류:

- `Authenticated session is no longer valid.`

대표 증상:

- `output/playwright/errors/*.html`을 열면 로그인 페이지 HTML
- `authenticated-home.md`도 다시 로그인 페이지일 수 있음

대응 순서:

1. `capture-session.ps1` 다시 실행
2. `authenticated-home.md`가 정상인지 확인
3. `node .\scripts\download-filegroup.mjs --pending` 재실행

## 장애 패턴 2. 중복 키 오류

과거 로그에서 실제 발생했던 오류:

- `UNIQUE constraint failed: files.filegroup_id, files.folder_path, files.filename, files.source_url`

원인:

- 동일 파일이 여러 번 열거되었는데 dedupe 없이 insert

예방:

- `seenFileKeys` 집합으로 `(folder_path, filename, source_url)` 조합을 중복 제거한다.

## 장애 패턴 3. 기존 파일이 있는데 다시 내려받는 문제

예방:

- 로컬 파일이 이미 존재하고 size > 0이면 SHA-256만 계산하고 skip
- 로그에 `file exists, skipping download`가 찍혀야 한다

## 장애 패턴 4. 사이트가 특정 파일에 HTTP 400을 반환하는 경우

최종 완료 상태 기준 실제로 남은 예외:

- filegroup `2344` / `CEN1438 Driver Door`
- filegroup `7961` / `5A65DF20`

특징:

- 둘 다 `DATA\EXCEL` 아래 파일
- 파일명에 확장자가 없음
- 반복 실행 후에도 `HTTP 400` 유지

운영 지침:

- 1회 재시도 후에도 동일하면 사이트 측 예외로 분류한다.
- `last_error`를 보존하고 예외 목록에 남긴다.
- 나머지 파일그룹은 완료 처리한다.

## 상태 확인 명령

```powershell
@'
const { DatabaseSync } = require("node:sqlite");
const path = require("node:path");
const db = new DatabaseSync(path.resolve("data/index/manifest.sqlite"));
const rows = db.prepare(`
  SELECT download_status, COUNT(*) AS cnt
    FROM filegroups
GROUP BY download_status
ORDER BY download_status
`).all();
console.log(JSON.stringify(rows, null, 2));
'@ | node -
```

## 최근 실패 파일그룹 보기

```powershell
@'
const { DatabaseSync } = require("node:sqlite");
const path = require("node:path");
const db = new DatabaseSync(path.resolve("data/index/manifest.sqlite"));
const rows = db.prepare(`
  SELECT filegroup_id, test_type_label, download_status, last_error
    FROM filegroups
   WHERE download_status = 'error'
ORDER BY filegroup_id
LIMIT 20
`).all();
console.log(JSON.stringify(rows, null, 2));
'@ | node -
```

## root 폴더 파일도 허용해야 한다

실제 다운로드 로그에서 아래 파일이 root에 존재하는 사례가 확인됐다.

- `info.txt`
- `README.txt`
- `TestEnvironmentalData.csv`

따라서 구현 시 `ROOT` 폴더에도 파일이 있을 수 있다는 점을 반드시 고려해야 한다.

## 이 단계 종료 체크리스트

- 단건 다운로드가 성공했다.
- 소량 배치 다운로드가 성공했다.
- 재실행 시 이미 있는 파일을 skip 한다.
- 인증 만료 후 세션 재확보 -> `--pending` 재개 흐름이 정착됐다.
