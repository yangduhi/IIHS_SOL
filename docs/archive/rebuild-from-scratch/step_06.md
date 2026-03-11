# Step 06. 인증 세션 캡처 스크립트 작성

이 단계에서는 `scripts/capture-session.ps1`를 만든다.  
이 파일은 IIHS TechData 로그인 후 재사용 가능한 Playwright 프로필과 storage-state를 저장한다.

## 생성할 파일

- `scripts/capture-session.ps1`

## 스크립트가 받아야 하는 입력

- `-Email`
- `-Password`
- `-ProfileDir`
- `-StorageState`

기본값:

- `Email = $env:IIHS_TECHDATA_EMAIL`
- `Password = $env:IIHS_TECHDATA_PASSWORD`
- `ProfileDir = ".auth\\profile"`
- `StorageState = ".auth\\storage-state.json"`

## 스크립트의 필수 동작

1. 이메일과 비밀번호가 없으면 즉시 실패한다.
2. `.auth\profile`, `.auth`, `output\playwright`를 만든다.
3. 환경변수 `IIHS_TECHDATA_EMAIL`, `IIHS_TECHDATA_PASSWORD`에 값을 세팅한다.
4. 기존 Playwright 창을 닫는다.
5. `playwright-cli open`으로 사이트를 persistent profile 모드로 연다.
6. Playwright 코드로 로그인 링크 클릭, 계정 입력, 비밀번호 입력, `Keep me signed in` 체크, `Sign in` 클릭을 수행한다.
7. 로그인 후 페이지가 인증 홈인지 검증한다.
8. `.auth\storage-state.json`을 저장한다.
9. `output\playwright\authenticated-home.md` 스냅샷을 남긴다.

## 반드시 사용할 CLI 형식

Windows 기준 가장 안정적으로 확인된 형식:

```powershell
npx --yes --package @playwright/cli playwright-cli ...
```

`@playwright/cli`는 `package.json`에 직접 선언되어 있지 않지만 운영상 필수다.

## 스크립트 작성 기준

아래 구조와 동일한 흐름으로 구현한다.

```powershell
[CmdletBinding()]
param(
    [string]$Email = $env:IIHS_TECHDATA_EMAIL,
    [string]$Password = $env:IIHS_TECHDATA_PASSWORD,
    [string]$ProfileDir = ".auth\\profile",
    [string]$StorageState = ".auth\\storage-state.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
```

필수 검증:

```powershell
if ([string]::IsNullOrWhiteSpace($Email) -or [string]::IsNullOrWhiteSpace($Password)) {
    throw "Set IIHS_TECHDATA_EMAIL and IIHS_TECHDATA_PASSWORD, or pass -Email and -Password."
}
```

필수 CLI 호출:

```powershell
& npx --yes --package @playwright/cli playwright-cli close-all | Out-Null
& npx --yes --package @playwright/cli playwright-cli open https://techdata.iihs.org/ --persistent --profile $ProfileDir | Out-Null
```

## 로그인 자동화 코드 요구사항

PowerShell 안에서 here-string으로 Playwright 코드를 만들고 `run-code`로 실행한다.

로그인 코드가 반드시 해야 하는 일:

- `Log in to IIHS TechData` 링크 클릭
- `User account` 입력
- `Password` 입력
- `Keep me signed in` 체크
- `Sign in` 버튼 클릭
- 최종 URL이 `https://techdata.iihs.org/` 또는 `default.aspx` 계열인지 대기
- `networkidle` 대기

인증 확인 코드가 반드시 해야 하는 일:

- 본문에서 `downloads`와 `sign out` 문자열 확인
- 둘 중 하나라도 없으면 실패

## 실행 예시

환경변수 방식:

```powershell
$env:IIHS_TECHDATA_EMAIL = "you@example.com"
$env:IIHS_TECHDATA_PASSWORD = "your-password"
powershell -ExecutionPolicy Bypass -File .\scripts\capture-session.ps1
```

파라미터 방식:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\capture-session.ps1 `
  -Email "you@example.com" `
  -Password "your-password"
```

## 실행 후 반드시 확인할 것

- `.auth\profile` 폴더가 생겼는가
- `.auth\storage-state.json`이 생겼는가
- `output\playwright\authenticated-home.md`가 생겼는가
- 스냅샷 내용에 로그인 폼이 아니라 인증된 홈 화면이 보이는가

## 실패 판단 기준

아래 중 하나면 실패로 본다.

- `authenticated-home.md`에 `User account` 입력창이 보인다
- `authenticated-home.md`에 `You are not logged in.`가 보인다
- `.auth\storage-state.json`이 생성되지 않았다
- MFA나 추가 확인 때문에 홈 화면 도달 전 멈췄다

## 실패 시 조치

- 브라우저 창이 열렸는데 로그인 후 튕기면 직접 로그인 후 다시 `state-save`를 시도한다.
- MFA가 매번 뜨면 영속 프로필 `.auth\profile` 유지가 특히 중요하다.
- 스냅샷이 로그인 페이지면 세션 캡처를 다시 수행한다.
