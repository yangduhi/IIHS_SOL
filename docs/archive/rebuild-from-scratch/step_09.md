# Step 09. 인증 세션 실제 확보와 검증

이 단계는 "코드 작성"이 아니라 "실제 로그인 가능한 세션 확보" 단계다.  
앞 단계에서 스크립트를 만들었더라도, 이 단계를 통과하지 못하면 discovery와 download는 모두 실패한다.

## 실행 전 준비

- IIHS 계정 이메일
- IIHS 계정 비밀번호
- MFA 또는 추가 승인 수단

## 권장 실행 방법

환경변수를 사용하는 방식이 가장 단순하다.

```powershell
$env:IIHS_TECHDATA_EMAIL = "you@example.com"
$env:IIHS_TECHDATA_PASSWORD = "your-password"
powershell -ExecutionPolicy Bypass -File .\scripts\capture-session.ps1
```

## 성공 시 생겨야 하는 파일

- `.auth\profile\...`
- `.auth\storage-state.json`
- `output\playwright\authenticated-home.md`

## 성공 판정 규칙

다음 4가지를 모두 만족해야 성공으로 본다.

1. `.auth\storage-state.json` 존재
2. 파일 크기가 0이 아님
3. `authenticated-home.md`가 존재
4. 스냅샷에 로그인 폼이 아니라 인증 홈 정보가 보임

## 스냅샷 확인 명령

```powershell
Get-Content .\output\playwright\authenticated-home.md -TotalCount 80
```

정상일 때 기대하는 단어:

- `downloads`
- `sign out`
- `RSS`

비정상일 때 자주 보이는 단어:

- `User account`
- `Password`
- `You are not logged in.`

## storage-state 확인

```powershell
Get-Item .\.auth\storage-state.json | Select-Object FullName,Length,LastWriteTime
```

## 실패 패턴과 대응

### 1. 스냅샷이 로그인 화면이다

의미:

- 로그인 자동화가 끝나기 전에 저장했거나
- 세션이 제대로 생성되지 않았거나
- MFA/추가 승인이 남아 있다

대응:

- 스크립트를 다시 실행한다.
- 필요하면 브라우저가 열린 상태에서 수동 로그인까지 마친 뒤 storage-state를 다시 저장한다.

### 2. 브라우저는 열렸지만 스크립트가 멈춘다

의미:

- MFA 또는 계정 잠금
- 로그인 DOM이 예상과 달라짐

대응:

- 브라우저에서 직접 로그인 완료 후 다시 시도한다.
- 필요하면 `capture-session.ps1`의 Playwright locator를 점검한다.

### 3. discovery/download 중간에 `Authenticated session is no longer valid.` 발생

의미:

- storage-state는 있었지만 이미 만료되었거나
- 장시간 실행 중 세션이 만료되었다

대응:

- 이 단계로 돌아와 세션을 다시 캡처한다.
- 이후 `download-filegroup.mjs --pending`로 재개한다.

## 이 단계 종료 체크리스트

- `.auth\profile`이 존재한다.
- `.auth\storage-state.json`이 존재한다.
- `authenticated-home.md`가 로그인 페이지가 아니다.
- 수집 작업에 사용할 실제 인증 세션이 확보되었다.
