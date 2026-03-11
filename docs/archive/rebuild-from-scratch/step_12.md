# Step 12. 최종 검증과 산출물 검사

이 단계에서는 "현재 프로젝트와 같은 품질로 내려받고 있는지"를 확인한다.  
단순히 파일이 생겼다는 것만으로는 충분하지 않다.

## 검증 1. 허용되지 않은 zero-byte 파일이 없어야 한다

```powershell
@'
const { DatabaseSync } = require("node:sqlite");
const path = require("node:path");
const db = new DatabaseSync(path.resolve("data/index/manifest.sqlite"));
const row = db.prepare(`
  SELECT COUNT(*) AS cnt
    FROM files
   WHERE status = 'downloaded'
     AND (size_bytes IS NULL OR size_bytes = 0)
     AND COALESCE(size_label, '') <> '0 bytes'
`).get();
console.log(JSON.stringify(row, null, 2));
'@ | node -
```

기대값:

- `cnt = 0`

추가 메모:

- 현재 최종 상태에는 filegroup `1726`의 `ROOT\TestEnvironmentalData.csv` 1건이 `size_label='0 bytes'`인 정상 zero-byte 원본으로 남아 있다.
- 따라서 zero-byte 자체를 전부 실패로 보면 안 된다.

## 검증 2. `PHOTOS`와 `VIDEO` 디렉터리가 raw 경로에 없어야 한다

```powershell
Get-ChildItem -Directory -Recurse data\raw | Where-Object { $_.Name -eq 'PHOTOS' } | Measure-Object | Select-Object Count
Get-ChildItem -Directory -Recurse data\raw | Where-Object { $_.Name -eq 'VIDEO' } | Measure-Object | Select-Object Count
```

기대값:

- 둘 다 `Count = 0`

## 검증 3. 사진/영상 파일이 raw 경로에 없어야 한다

```powershell
rg -n "\\\\VIDEO\\\\|/VIDEO/|\\.jpg$|\\.jpeg$|\\.png$|\\.tif$|\\.tiff$|\\.bmp$|\\.gif$|\\.mp4$|\\.mov$|\\.avi$|\\.wmv$|\\.mkv$|\\.webm$" data\raw
```

기대값:

- 아무 결과도 없어야 한다

## 검증 4. 폴더/파일 집계가 말이 되는지 확인

```powershell
@'
const { DatabaseSync } = require("node:sqlite");
const path = require("node:path");
const db = new DatabaseSync(path.resolve("data/index/manifest.sqlite"));
const rows = db.prepare(`
  SELECT filegroup_id, title, folder_count, file_count, downloaded_file_count, excluded_file_count, download_status
    FROM filegroups
   WHERE download_status = 'downloaded'
ORDER BY filegroup_id
LIMIT 10
`).all();
console.log(JSON.stringify(rows, null, 2));
'@ | node -
```

## 검증 5. 샘플 파일그룹 실물 경로 확인

예시:

```powershell
Get-ChildItem -Recurse -File .\data\raw\small-overlap-driver-side\1472-CF09004 | Select-Object FullName,Length | Select-Object -First 20
```

이때 아래 유형이 보여야 정상이다.

- `DATA\...`
- `REPORTS\...`
- root의 `info.txt` 또는 `README.txt`

`PHOTOS`, `VIDEO`는 없어야 한다.

## 검증 6. 로그 파일 생성 확인

```powershell
Get-ChildItem .\output\logs | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,Length,LastWriteTime
```

정상 기대:

- `discover-small-overlap-*.log`
- `discover-small-overlap-*.jsonl`
- `download-small-overlap-*.log`
- `download-small-overlap-*.jsonl`

## 검증 7. 에러 아티팩트가 있다면 내용 확인

```powershell
Get-ChildItem .\output\playwright\errors | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,Length,LastWriteTime
```

에러 HTML을 열었을 때 로그인 페이지면 인증 문제다.  
DOM 자체가 다르면 사이트 구조가 변한 것이다.

## 기준선과 비교하는 방법

현재 저장소에서 확인된 참조 성질:

- type code 25, 26만 사용
- 인증은 Microsoft 경유
- detail 페이지 폴더 이동은 ASP.NET postback
- 파일은 `/secure/file.ashx?...`로 직접 내려받음
- 사진은 최종 완성본 기준 제외
- 영상은 제외
- 일부 파일은 사이트가 직접 `HTTP 400`을 반환할 수 있음
- 일부 원본은 `size_label='0 bytes'`일 수 있음

이 성질이 모두 유지되면 "동일 시스템"으로 판단할 수 있다.

## 이 단계 종료 체크리스트

- 허용되지 않은 zero-byte 다운로드 파일이 없다.
- raw 폴더에 `PHOTOS`, `VIDEO` 디렉터리가 없다.
- raw 폴더에 사진/영상 파일이 없다.
- 샘플 파일그룹의 구조가 예상과 맞는다.
- 로그가 정상 생성된다.
- 오류가 있다면 HTML/PNG로 원인 추적이 가능하다.
