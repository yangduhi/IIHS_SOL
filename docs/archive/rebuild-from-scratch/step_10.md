# Step 10. discovery 실행과 매니페스트 검증

이 단계에서는 목록 수집이 실제로 잘 되는지 검증한다.  
목표는 "파일그룹을 발견해 DB에 넣고 JSONL로 내보내는 것"이다.

## 1차 스모크 테스트

먼저 드라이버측 1페이지만 스캔한다.

```powershell
node .\scripts\discover-small-overlap.mjs --types=25 --limit-pages=1
```

이 단계에서 확인할 것:

- 에러 없이 종료되는가
- `output/logs/discover-small-overlap-*.log` 생성되는가
- `data/index/filegroups.jsonl`이 비어 있지 않은가

## 2차 전체 discovery

```powershell
npm run discover
```

## 검증 1. type code별 파일그룹 개수

```powershell
@'
const { DatabaseSync } = require("node:sqlite");
const path = require("node:path");
const db = new DatabaseSync(path.resolve("data/index/manifest.sqlite"));
const rows = db.prepare(`
  SELECT test_type_code, test_type_label, COUNT(*) AS cnt
    FROM filegroups
GROUP BY test_type_code, test_type_label
ORDER BY test_type_code
`).all();
console.log(JSON.stringify(rows, null, 2));
'@ | node -
```

참조값:

- 2026-03-06 기준 `25`는 약 361개
- 2026-03-06 기준 `26`는 약 52개

실행 시점에 값이 바뀔 수 있다.  
중요한 것은 "두 유형 모두 데이터가 존재"하고 "0건이 아니어야 한다"는 점이다.

## 검증 2. `download_status` 초기값 확인

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

정상 기대:

- 대부분 `pending`

## 검증 3. JSONL 내보내기 확인

다음 파일이 모두 있어야 한다.

- `data/index/filegroups.jsonl`
- `data/index/folders.jsonl`
- `data/index/files.jsonl`

이 단계 직후에는 `folders.jsonl`, `files.jsonl`가 비어 있거나 거의 비어 있을 수 있다.  
그것은 아직 download를 하지 않았기 때문이다.

## discovery 실패 시 점검 항목

- `.auth\storage-state.json`이 실제 로그인 상태인가
- `authenticated-home.md`가 로그인 페이지로 돌아간 것은 아닌가
- 목록 URL `t=25`, `t=26`에 직접 접근했을 때 인증이 유지되는가
- `#ctl00_MainContentPlaceholder_PageSelector_ddPages`가 여전히 존재하는가

## 이 단계 종료 체크리스트

- `filegroups` 테이블이 채워졌다.
- type code 25, 26 데이터가 둘 다 있다.
- JSONL 스냅샷이 갱신되었다.
- `download_status`가 기본적으로 `pending`으로 세팅되었다.
- 이제 download 단계로 넘어갈 수 있다.
