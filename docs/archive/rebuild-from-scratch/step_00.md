# Step 00. 목표 상태와 기준선 확정

이 폴더의 문서는 `D:\vscode\IIHS_SOL`와 동일한 목적의 IIHS TechData 수집 프로젝트를 빈 폴더에서 다시 만들기 위한 작업지시서다.  
대상 독자는 사람 개발자이거나, 빈 폴더에서 프로젝트를 생성해야 하는 다른 코딩 에이전트다.

## 이 문서가 재현하려는 최종 상태

- Windows PowerShell 기반 프로젝트여야 한다.
- Node.js 기반 스크립트 3개가 있어야 한다.
- 인증 세션을 확보하는 PowerShell 스크립트 1개가 있어야 한다.
- IIHS TechData의 아래 2개 시험유형만 다뤄야 한다.
  - `Small overlap frontal: driver-side`
  - `Small overlap frontal: passenger-side`
- 파일그룹 목록을 수집해 `manifest.sqlite`와 JSONL 스냅샷으로 저장해야 한다.
- 각 파일그룹 상세 페이지를 열어 폴더/파일 목록을 저장하고, 실제 파일을 내려받아 `data/raw` 아래에 적재해야 한다.
- 최종 완성본 기준 다운로드 범위는 `DATA*`, `REPORTS`, `ROOT` 파일이며 `PHOTOS`, `VIDEO`, 사진 확장자, 영상 확장자는 제외한다.
- 장시간 실행 중 인증이 만료될 수 있으므로, 실패 후 재실행이 가능해야 한다.
- 로그는 `output/logs`에 남아야 하고, 인증 실패 등 페이지 오류는 `output/playwright/errors`에 HTML/PNG로 남아야 한다.

## 현재 저장소에서 확인한 기준선

아래 값은 2026-03-06 현재 워크스페이스에서 확인한 참조값이다.  
실제 사이트 데이터는 시간이 지나면 바뀔 수 있으므로, 빈 폴더에서 재구축할 때는 "검증 기준"으로만 사용한다.

- IIHS 로그인은 Microsoft `iihspublic.onmicrosoft.com` 경유다.
- 목록 URL은 다음 2개다.
  - 드라이버측: `https://techdata.iihs.org/secure/filegroups.aspx?t=25&r=released`
  - 조수석측: `https://techdata.iihs.org/secure/filegroups.aspx?t=26&r=released`
- 2026-03-06 관찰 기준 페이지 수는 다음과 같다.
  - 드라이버측: 15 page
  - 조수석측: 3 page
- 현재 매니페스트 기준 파일그룹 수는 다음과 같다.
  - `25`: 361개
  - `26`: 52개
- 현재 다운로드 성공 샘플은 다음과 같다.
  - `1472-CF09004`
  - `1473-CF09005`
  - `1474-CF09006`
  - `1475-CF09007`
  - `1476-CF09008`
  - `8630-CEP2501`
- 최종 처리 스냅샷은 다음과 같다.
  - 전체 파일그룹: `413`
  - `downloaded`: `411`
  - `error`: `2`
  - 다운로드 파일: `24,793`
  - 제외 파일: `148`
  - 허용된 zero-byte 원본: `1`
- 현재 `data/raw` 기준 `PHOTOS` 디렉터리 수는 `0`, `VIDEO` 디렉터리 수도 `0`이다.

## 중요한 기준 결정

이 저장소는 중간 과정과 최종 완료 상태가 다르다.

- 과거 중간 산출물에는 `PHOTOS` 파일이 존재했던 시점이 있었다.
- 그러나 최종 완료 상태의 `manifest.sqlite`, 최신 다운로드 로그, 현재 `data/raw` 구조는 `PHOTOS`와 `VIDEO`를 모두 제외하는 방향으로 수렴했다.

빈 폴더에서 "현재 성공적으로 내려받고 있는 시스템"을 재현하려면 아래 원칙을 따른다.

- `VIDEO`를 제외한다.
- `PHOTOS`도 제외한다.
- 사진 확장자와 영상 확장자를 모두 제외한다.
- `ROOT`의 텍스트/CSV 파일은 허용한다.
- `size_label`이 `0 bytes`인 원본은 로컬 파일 길이 `0`이어도 정상으로 본다.
- 반복 재시도 후에도 사이트가 `HTTP 400`을 반환하는 항목은 예외 목록에 기록된 잔여 오류로 관리한다.

## 현재 구현 범위

이 저장소에서 실제 구현된 범위는 아래까지다.

- `scripts/capture-session.ps1`
- `scripts/discover-small-overlap.mjs`
- `scripts/download-filegroup.mjs`
- `scripts/lib/logging.mjs`
- `scripts/lib/db.mjs`
- `scripts/lib/iihs-techdata.mjs`

아직 구현되지 않은 항목:

- `sync-rss.mjs`
- 주기 배치 스케줄링
- 고급 재시도 큐
- 분산 실행

따라서 이 문서는 "현재 구현 범위와 동일한 시스템"을 만드는 지시서로 작성한다.

## 전체 진행 순서

1. 빈 폴더를 만들고 런타임 조건을 맞춘다.
2. 디렉터리 구조와 기본 파일을 만든다.
3. `package.json`과 의존성을 맞춘다.
4. 공통 라이브러리 파일 3개를 만든다.
5. 인증 세션 확보 스크립트를 만든다.
6. discovery 스크립트를 만든다.
7. download 스크립트를 만든다.
8. 인증 세션을 실제로 확보한다.
9. 파일그룹 목록을 수집한다.
10. 일부 파일그룹부터 다운로드를 시작한다.
11. 인증 만료, 중복, 실패 로그를 보고 재실행 전략을 정착시킨다.
12. 최종 검증 후 운영 기준을 문서화한다.

## 각 단계에서 반드시 지킬 원칙

- 자격증명은 Git에 커밋하지 않는다.
- `.auth/`, `output/`, `data/raw/`, `node_modules/`는 버전관리에서 제외한다.
- 먼저 인증 세션을 만든 뒤 discovery/download를 실행한다.
- 한 번에 전체 백필을 돌리지 말고, 작은 제한값으로 먼저 검증한다.
- 인증 실패 시 억지로 재시도하지 말고 세션을 다시 캡처한다.
- `manifest.sqlite`가 프로젝트의 사실원장이다. JSONL은 스냅샷이다.
- 스크립트에서 사용하는 CSS selector, ASP.NET postback 동작, 파일 URL 패턴을 임의로 바꾸지 않는다.
- 최종 완료 판정은 "정상 다운로드 가능 항목 전부 확보 + 예외 항목 명시" 기준으로 내린다.
