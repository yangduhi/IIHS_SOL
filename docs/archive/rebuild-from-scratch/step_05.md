# Step 05. IIHS 전용 공통 헬퍼 모듈 작성

이 단계에서는 `scripts/lib/iihs-techdata.mjs`를 만든다.  
이 파일은 IIHS TechData 사이트에 특화된 상수, URL 규칙, 경로 정규화, 인증 확인, postback 대기 로직을 담당한다.

## 생성할 파일

- `scripts/lib/iihs-techdata.mjs`

## 이 파일이 반드시 제공해야 하는 상수

- `ROOT_URL`
- `PROFILE_DIR`
- `STORAGE_STATE_PATH`
- `ERROR_ARTIFACTS_DIR`
- `VIDEO_EXTENSIONS`
- `PHOTO_EXTENSIONS`
- `SMALL_OVERLAP_TYPES`

값 기준:

- `ROOT_URL = 'https://techdata.iihs.org'`
- `PROFILE_DIR = path.resolve('.auth/profile')`
- `STORAGE_STATE_PATH = path.resolve('.auth/storage-state.json')`
- `ERROR_ARTIFACTS_DIR = path.resolve('output/playwright/errors')`
- `SMALL_OVERLAP_TYPES`는 아래 2개만 넣는다.
  - `{ code: 25, label: 'Small overlap frontal: driver-side', slug: 'small-overlap-driver-side' }`
  - `{ code: 26, label: 'Small overlap frontal: passenger-side', slug: 'small-overlap-passenger-side' }`

## 핵심 설계 원칙

- 이 프로젝트는 `VIDEO`와 `PHOTOS`를 모두 제외한다.
- 폴더 경로는 내부에서 항상 백슬래시 기준으로 정규화한다.
- `ROOT`라는 가상 폴더 이름을 허용한다.
- 인증 실패 판정은 페이지 본문에 `You are not logged in.`가 나타나는지로 판단한다.

## 구현해야 하는 함수 목록

- `buildListUrl(typeCode)`
- `buildDetailUrl(filegroupId)`
- `sanitizePathSegment(value)`
- `normalizeFolderPath(folderPath)`
- `isVideoPath(folderPath, filename = '')`
- `isPhotoPath(folderPath, filename = '')`
- `parseListEntry(typeConfig, linkText, href)`
- `parseDetailHeading(headingText)`
- `splitModifiedAndSize(metaLine)`
- `filegroupDataRoot(typeConfig, filegroupId, testCode)`
- `absoluteFileUrl(relativeUrl)`
- `ensureAuthenticated(page)`
- `hashFile(filePath)`
- `captureErrorArtifacts(page, label)`
- `waitForPostback(page, action)`

## `isVideoPath` 구현 규칙

아래 중 하나라도 참이면 `true`를 반환해야 한다.

- 폴더 경로가 `VIDEO`
- 폴더 경로가 `VIDEO\`로 시작
- 폴더 경로 내부에 `\VIDEO\` 포함
- 파일 확장자가 아래 중 하나
  - `.mp4`
  - `.mov`
  - `.avi`
  - `.wmv`
  - `.mkv`
  - `.webm`

## `isPhotoPath` 구현 규칙

아래 중 하나라도 참이면 `true`를 반환해야 한다.

- 폴더 경로가 `PHOTOS`
- 폴더 경로가 `PHOTOS\`로 시작
- 폴더 경로 내부에 `\PHOTOS\` 포함
- 파일 확장자가 아래 중 하나
  - `.jpg`
  - `.jpeg`
  - `.png`
  - `.tif`
  - `.tiff`
  - `.bmp`
  - `.gif`

중요:

- 최종 완성본 기준으로 `PHOTOS`는 실제 다운로드 대상이 아니다.
- 현재 재구축본도 `PHOTOS`를 제외해야 최종 상태와 일치한다.

## `parseListEntry` 구현 규칙

입력:

- `typeConfig`
- IIHS 목록 링크 텍스트
- 링크 href

출력 필드:

- `filegroupId`
- `title`
- `testCode`
- `vehicleYear`
- `vehicleMakeModel`
- `detailUrl`

파싱 규칙:

- `filegroup.aspx?{숫자}`에서 filegroup ID 추출
- 링크 텍스트는 대체로 `{testCode}: {vehicle info}` 형태다
- `title`은 아래 형식으로 조합한다  
  `"{type label} Test {원본 링크 텍스트}"`

## `parseDetailHeading` 구현 규칙

대상 문자열 예시:

- `Small overlap frontal: driver-side Test CF09004: 2004 Chrysler Concorde`

이 값에서 아래를 추출해야 한다.

- 시험유형 라벨
- 테스트 코드
- 차종 설명
- 연식

## `captureErrorArtifacts` 구현 규칙

- `output/playwright/errors`를 생성한다.
- HTML과 PNG 두 파일을 남긴다.
- 파일명에는 ISO timestamp와 안전한 라벨을 넣는다.
- 반환값은 `{ htmlPath, pngPath }`

## `waitForPostback` 구현 규칙

IIHS 상세/목록 페이지는 ASP.NET postback을 사용하므로 다음 조건을 만족해야 한다.

- 액션 전후에 POST 응답을 기다린다.
- URL에 `filegroup` 또는 `filegroups`가 들어간 응답을 기다린다.
- 응답 대기 후 `networkidle`까지 기다린다.
- 마지막에 짧은 `waitForTimeout(100)`을 둔다.

## 권장 구현 예시

이 단계에서는 전체 코드를 그대로 재작성해도 된다.  
다만 아래 5개는 반드시 현재 저장소와 같은 계약을 가져야 한다.

```js
export const ROOT_URL = 'https://techdata.iihs.org';
export const PROFILE_DIR = path.resolve('.auth/profile');
export const STORAGE_STATE_PATH = path.resolve('.auth/storage-state.json');
export const ERROR_ARTIFACTS_DIR = path.resolve('output/playwright/errors');
export const VIDEO_EXTENSIONS = new Set(['.mp4', '.mov', '.avi', '.wmv', '.mkv', '.webm']);
export const PHOTO_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif']);
```

```js
export const SMALL_OVERLAP_TYPES = [
  { code: 25, label: 'Small overlap frontal: driver-side', slug: 'small-overlap-driver-side' },
  { code: 26, label: 'Small overlap frontal: passenger-side', slug: 'small-overlap-passenger-side' },
];
```

```js
export function buildListUrl(typeCode) {
  return `${ROOT_URL}/secure/filegroups.aspx?t=${typeCode}&r=released`;
}
```

```js
export function buildDetailUrl(filegroupId) {
  return `${ROOT_URL}/secure/filegroup.aspx?${filegroupId}`;
}
```

```js
export async function ensureAuthenticated(page) {
  const bodyText = await page.locator('body').innerText();
  if (/You are not logged in\./i.test(bodyText)) {
    throw new Error('Authenticated session is no longer valid.');
  }
}
```

## 이 단계 종료 체크리스트

- `scripts/lib/iihs-techdata.mjs`가 생성되었다.
- `SMALL_OVERLAP_TYPES`에 25/26만 정의되어 있다.
- `VIDEO` 제외 규칙이 구현되었다.
- `PHOTOS` 제외 규칙도 구현되었다.
- 인증 실패 감지 함수가 존재한다.
- 에러 HTML/PNG 저장 함수가 존재한다.
