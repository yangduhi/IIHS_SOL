# IIHS 프로젝트 Skill 사용 가이드

## 우선순위
1. `playwright`
2. `shell_command`
3. `js_repl`
4. `web`

## 사용 원칙

### `playwright`
- 로그인, 목록 탐색, 폴더 클릭, 파일 링크 확인에 우선 사용한다.
- 이 프로젝트에서는 Windows 환경에서 `npx --yes --package @playwright/cli playwright-cli ...` 형식을 기본으로 쓴다.
- 드롭다운 선택 후에는 `Submit`까지 눌러야 목록이 갱신된다는 점을 항상 반영한다.

### `shell_command`
- PowerShell 기반 보조 작업, 파일 정리, 세션 파일 확인, Git/venv 초기화에 사용한다.
- 단순 파일 조회나 상태 점검은 우선 `shell_command` 로 처리한다.

### `js_repl`
- RSS 파싱, 매니페스트 정규화, JSONL/SQLite 보조 처리처럼 Node가 편한 작업에 사용한다.
- 브라우저 인증 로직의 주 경로로 쓰지 않는다.

### `web`
- 공개 RSS, 공개 랜딩 페이지, 공개 문서 확인에만 사용한다.
- 인증이 필요한 `secure/*` 본문 확인은 브라우저 세션으로 처리한다.

## 현재 프로젝트에서 피할 것
- 인증 없이 `/secure/file.ashx` 를 직접 두드리는 방식
- RSS만으로 전체 히스토리를 복원하려는 시도
- 비밀번호를 문서나 스크립트에 직접 하드코딩하는 방식
