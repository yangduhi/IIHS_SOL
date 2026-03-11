# Step 08. 파일 다운로드 스크립트 작성

이 단계에서는 `scripts/download-filegroup.mjs`를 만든다.  
이 파일이 프로젝트의 핵심이며, 파일그룹 상세 페이지를 열어 폴더/파일 목록을 저장하고 실제 파일을 다운로드한다.

## 생성할 파일

- `scripts/download-filegroup.mjs`

## 지원해야 하는 CLI 인자

- `--pending`
- `--filegroup-id=숫자`
- `--limit=숫자`
- `--concurrency=숫자`

기본 규칙:

- `--pending`와 `--filegroup-id` 둘 다 없으면 자동으로 `pending` 모드로 간주한다.
- 기본 concurrency는 `3`으로 둔다.

## 스크립트의 책임

1. 다운로드 대상 파일그룹을 DB에서 고른다.
2. 브라우저 context와 HTTP request context를 인증 상태로 준비한다.
3. 파일그룹 상세 페이지를 연다.
4. 인증 상태를 검사한다.
5. 본문 텍스트에서 제목과 `Tested on YYYY-MM-DD`를 추출한다.
6. 왼쪽 폴더 트리를 전부 읽는다.
7. 각 폴더를 클릭하면서 오른쪽 파일 목록을 전 페이지 순회한다.
8. 폴더 목록은 `folders` 테이블에, 파일 목록은 `files` 테이블에 다시 써넣는다.
9. `PHOTOS` 폴더, `VIDEO` 폴더, 사진 확장자, 영상 확장자는 제외한다.
10. 나머지 파일은 Playwright의 `request.newContext()`로 직접 GET 다운로드한다.
11. SHA-256을 계산하고 로컬 경로를 기록한다.
12. 파일그룹 단위 카운트와 상태를 `filegroups` 테이블에 반영한다.
13. 에러가 나면 HTML/PNG 아티팩트를 저장한다.

## 반드시 사용할 selector

- 폴더 목록: `#ctl00_MainContentPlaceholder_FileBrowser_FolderList li a`
- 파일 목록: `#ctl00_MainContentPlaceholder_FileBrowser_FilesList li`
- 파일 페이지 셀렉터: `#ctl00_MainContentPlaceholder_FileBrowser_PageSelector_ddPages`
- 폴더별 zip 링크: `#ctl00_MainContentPlaceholder_FileBrowser_ZipFileLink`

## 구현해야 하는 보조 함수

최소한 아래 함수가 있어야 한다.

- `parseArgs(argv)`
- `typeByCode(typeCode)`
- `getPendingFilegroups(db, args)`
- `mapWithConcurrency(items, limit, worker)`
- `ensureFilePage(page, pageNumber)`
- `clickFolderByIndex(page, folderIndex)`
- `readFolders(page)`
- `readCurrentFiles(page, folderPath, pageNumber)`
- `resolveLocalFilePath(filegroup, folderPath, filename)`
- `writeBufferAtomically(filePath, buffer)`
- `sha256ForBuffer(buffer)`
- `replaceFilegroupStructure(filegroupId, folders, files)`

## `getPendingFilegroups` 쿼리 규칙

`--filegroup-id`가 있으면 단건 우선이다.

`--limit`가 있으면 아래 상태를 대상으로 제한 조회한다.

- `pending`
- `error`
- `downloading`

정렬 기준:

- `ORDER BY test_type_code, filegroup_id`

## `readFolders(page)` 요구사항

반환값은 아래 구조 배열이어야 한다.

```js
[
  { index: 0, folderPath: 'ROOT' },
  { index: 1, folderPath: 'DATA\\DAS' }
]
```

실제 구현에서는 빈 문자열 폴더명을 제거한다.

## `readCurrentFiles(page, folderPath, pageNumber)` 요구사항

각 파일 항목에서 최소 아래를 읽어야 한다.

- `folderPath`
- `listedOnPage`
- `filename`
- `sourceUrl`
- `metaLine`

`metaLine`은 후속 처리에서 수정일/사이즈로 분해한다.

## 제외 규칙

다음을 제외한다.

- 폴더 경로가 `PHOTOS`
- 폴더 경로가 `PHOTOS\`로 시작
- 폴더 경로 안에 `\PHOTOS\` 포함
- 폴더 경로가 `VIDEO`
- 폴더 경로가 `VIDEO\`로 시작
- 폴더 경로 안에 `\VIDEO\` 포함
- 파일 확장자가 사진 확장자 집합에 포함
- 파일 확장자가 영상 확장자 집합에 포함

주의:

- 현재 최종 완료 상태와 맞추려면 `PHOTOS`를 제외해야 한다.
- 폴더 레벨 bulk zip 링크가 있더라도 현재 구현은 개별 파일 다운로드를 기준으로 한다.

## 파일 목록 적재 규칙

각 파일 row에는 최소 아래 필드가 들어가야 한다.

- `filegroup_id`
- `folder_path`
- `filename`
- `relative_path`
- `listed_on_page`
- `modified_label`
- `size_label`
- `source_url`
- `status`
- `excluded_reason`

상태 규칙:

- 제외 파일이면 `excluded`
- 다운로드 대상이면 `pending`

## 중복 방지 규칙

초기 실행 로그에서 `UNIQUE constraint failed`가 발생한 이력이 있으므로, 현재 재구축본은 반드시 중복 방지 키를 둬야 한다.

추천 키:

```js
const fileKey = [
  normalizedFolderPath,
  fileEntry.filename,
  fileEntry.sourceUrl,
].join('||');
```

이미 본 키면 warn 로그를 남기고 스킵한다.

## 다운로드 규칙

다운로드는 브라우저 클릭이 아니라 인증 쿠키를 가진 HTTP 요청으로 수행한다.

핵심 절차:

1. `api = await request.newContext({ storageState: STORAGE_STATE_PATH })`
2. `absoluteFileUrl(fileRow.source_url)`로 절대 URL 생성
3. `api.get(absoluteUrl, { timeout: 120000 })`
4. `response.ok()` 검사
5. `response.body()`로 버퍼 획득
6. `sha256` 계산
7. `.part` 파일로 먼저 쓰고 rename
8. DB에 `content_type`, `content_disposition`, `size_bytes`, `sha256`, `local_path`, `downloaded_at` 반영

## 로컬 저장 경로 규칙

아래 규칙을 따라야 현재 저장소와 동일한 구조가 된다.

```text
data/raw/{type-slug}/{filegroupId}-{testCode}/{folder-path}/{filename}
```

예시:

```text
data/raw/small-overlap-driver-side/1472-CF09004/DATA/DAS/CF09004001.BIN
data/raw/small-overlap-driver-side/1472-CF09004/REPORTS/cf09004 _concorde_.pdf
data/raw/small-overlap-driver-side/1472-CF09004/info.txt
```

## 기존 파일 재활용 규칙

같은 로컬 경로에 이미 파일이 있고 조건이 아래와 같으면 재다운로드하지 않는다.

- regular file
- size > 0

이 경우:

- 파일 SHA-256을 다시 계산
- 상태를 `downloaded`로 갱신
- `filesSkippedExisting` 카운트를 올린다

## 파일그룹 상태 전이 규칙

시작 시:

- `download_status = 'downloading'`

정상 종료 시:

- 에러 파일 0개면 `downloaded`
- 에러 파일 1개 이상이면 `error`

반드시 반영할 집계 필드:

- `folder_count`
- `file_count`
- `downloaded_file_count`
- `excluded_file_count`
- `tested_on`
- `title`
- `test_code`
- `vehicle_year`
- `vehicle_make_model`
- `data_root`
- `last_error`

## 권장 첫 실행 명령

가장 먼저 단건 테스트:

```powershell
node .\scripts\download-filegroup.mjs --filegroup-id=1472 --concurrency=2
```

그다음 제한 실행:

```powershell
node .\scripts\download-filegroup.mjs --pending --limit=3 --concurrency=2
```

검증 후 전체 대기열:

```powershell
npm run download:pending
```

## 성공 판단 기준

- `data/raw/...` 아래에 실제 파일이 생김
- `files` 테이블의 `status='downloaded'` 증가
- `filegroups.download_status='downloaded'` 증가
- `output/logs/download-small-overlap-*.log` 생성
- 최종 raw 아래에 `PHOTOS`, `VIDEO` 디렉터리가 없어야 함

## 실패 시 필수 아티팩트

파일그룹 단위 예외가 나면 아래가 남아야 한다.

- `output/playwright/errors/{timestamp}-filegroup-{id}.html`
- `output/playwright/errors/{timestamp}-filegroup-{id}.png`

이 아티팩트는 인증 만료, 예상치 못한 DOM 변화, 잘못된 postback 흐름을 진단하는 데 사용한다.

## 최종 완료 상태에서 확인된 예외

반복 재시도 후에도 아래 2개 파일은 사이트가 직접 `HTTP 400`을 반환했다.

- filegroup `2344` / `DATA\EXCEL\CEN1438 Driver Door`
- filegroup `7961` / `DATA\EXCEL\5A65DF20`

따라서 완료 판정은 "모든 정상 응답 파일 다운로드 + 예외 목록 기록" 기준으로 잡는 편이 현실적이다.

또한 아래 파일은 원본 메타데이터 자체가 `0 bytes`였다.

- filegroup `1726` / `ROOT\TestEnvironmentalData.csv`

이 경우 zero-byte 자체를 오류로 처리하지 말고, `size_label='0 bytes'`와 로컬 길이 `0`이 일치하는지로 검증한다.
