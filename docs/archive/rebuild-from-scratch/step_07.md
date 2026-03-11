# Step 07. 파일그룹 discovery 스크립트 작성

이 단계에서는 `scripts/discover-small-overlap.mjs`를 만든다.  
이 스크립트는 IIHS 목록 페이지를 스캔해 파일그룹 메타데이터를 `filegroups` 테이블에 적재한다.

## 생성할 파일

- `scripts/discover-small-overlap.mjs`

## 지원해야 하는 CLI 인자

- `--types=25,26`
- `--limit-pages=숫자`

기본 동작:

- 아무 인자도 없으면 25, 26 두 유형 전체를 스캔한다.
- `--limit-pages`가 있으면 각 유형의 앞쪽 일부 페이지만 스캔한다.

## 이 스크립트의 실행 순서

1. 인자를 파싱한다.
2. logger를 만든다.
3. `manifest.sqlite`를 연다.
4. `runs` 테이블에 시작 기록을 쓴다.
5. `.auth/profile`로 persistent Chromium context를 띄운다.
6. 현재 세션을 `.auth/storage-state.json`으로 다시 저장한다.
7. 이미지/폰트/스타일시트/미디어는 route abort 해서 속도를 높인다.
8. 유형별 목록 URL로 이동한다.
9. 인증이 유효한지 확인한다.
10. 페이지 셀렉터의 옵션 수로 총 페이지 수를 구한다.
11. 각 페이지에서 `a[href*="filegroup.aspx?"]` 링크를 수집한다.
12. `parseListEntry`로 `filegroup_id`, `title`, `testCode`, `vehicleYear`, `vehicleMakeModel`, `detailUrl`을 만든다.
13. `filegroups` 테이블에 upsert 한다.
14. 마지막에 JSONL 스냅샷을 갱신한다.
15. `runs` 테이블에 성공 또는 실패 상태를 기록한다.

## `filegroups` upsert 요구사항

초기 insert 시 최소한 아래를 채워야 한다.

- `filegroup_id`
- `test_type_code`
- `test_type_label`
- `title`
- `test_code`
- `vehicle_year`
- `vehicle_make_model`
- `detail_url`
- `discovered_at`
- `last_seen_at`
- `source = 'ui-scan'`
- `list_page`
- `download_status = 'pending'`

충돌 시 업데이트해야 하는 필드:

- `test_type_code`
- `test_type_label`
- `title`
- `test_code`
- `vehicle_year`
- `vehicle_make_model`
- `detail_url`
- `last_seen_at`
- `list_page`
- `last_error = NULL`

## 반드시 사용할 selector

- 페이지 셀렉터: `#ctl00_MainContentPlaceholder_PageSelector_ddPages`
- 목록 링크: `a[href*="filegroup.aspx?"]`

## 구현상 세부 규칙

- `pageSelector`가 없으면 총 페이지 수는 `1`로 간주한다.
- 2페이지 이상으로 이동할 때는 단순 `selectOption()`만 하지 말고 `waitForPostback()`으로 감싸야 한다.
- 각 유형별로 `seenIds` 집합을 두어 같은 실행에서 중복 ID를 경고할 수 있어야 한다.
- malformed 링크는 스킵하고 warn 로그를 남긴다.

## 꼭 들어가야 하는 요약 정보

실행이 끝나면 아래 구조와 유사한 summary를 남긴다.

```js
{
  types: [
    {
      typeCode: 25,
      typeLabel: 'Small overlap frontal: driver-side',
      pagesScanned: 15,
      uniqueFilegroups: 361,
      rowsProcessed: 361
    }
  ],
  totalFilegroups: 413
}
```

위 숫자는 참조 예시일 뿐이며, 실제 값은 실행 시점에 달라질 수 있다.

## 첫 실행 권장 명령

전체 스캔 전에 소규모 검증:

```powershell
node .\scripts\discover-small-overlap.mjs --types=25 --limit-pages=1
```

정상 확인 후 전체:

```powershell
npm run discover
```

## 실행 후 확인할 것

- `data/index/manifest.sqlite` 존재
- `data/index/filegroups.jsonl`이 비어 있지 않음
- `filegroups` 테이블에 type code 25/26 데이터 존재
- `download_status`가 새 행 기준 `pending`

## 간단 검증 명령

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

## 실패 시 자주 보는 증상

- 인증 만료: `Authenticated session is no longer valid.`
- 목록이 비어 있음: 세션이 로그인 상태가 아님
- 페이지 이동 실패: `waitForPostback` 없이 selectOption을 사용했을 가능성
