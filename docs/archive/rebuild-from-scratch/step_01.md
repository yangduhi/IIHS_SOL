# Step 01. 빈 폴더와 런타임 준비

이 단계의 목표는 "코드를 쓰기 전에 실행 환경이 프로젝트 요구조건을 만족하는지" 확인하는 것이다.

## 권장 환경

- 운영체제: Windows 10 또는 Windows 11
- 셸: PowerShell
- Node.js: `24.x` 권장
- npm: Node 설치본 사용
- 네트워크: `https://techdata.iihs.org/` 접속 가능
- 계정: IIHS TechData 로그인 가능 계정 1개 이상

Node 24.x를 권장하는 이유:

- 현재 프로젝트는 `node:sqlite`의 `DatabaseSync`를 사용한다.
- 로컬 기준 실제 동작 버전은 `v24.12.0`이다.
- 더 낮은 버전에서도 될 수 있지만, "동일 시스템 재현" 기준으로는 Node 24.x에 맞추는 편이 안전하다.

## 새 작업 폴더 만들기

예시:

```powershell
New-Item -ItemType Directory -Force D:\work\IIHS_SOL
Set-Location D:\work\IIHS_SOL
```

원하면 바로 Git 저장소도 초기화한다.

```powershell
git init
```

## 선행 확인 명령

```powershell
node -v
npm -v
```

정상 예시:

- `node -v`가 `v24.x.x` 형식으로 출력된다.
- `npm -v`가 정상 숫자를 출력한다.

## PowerShell 실행 정책 확인

`capture-session.ps1`를 실행해야 하므로 최소한 현재 사용자 범위에서 스크립트 실행이 가능해야 한다.

확인:

```powershell
Get-ExecutionPolicy -List
```

필요 시 현재 사용자 범위만 완화:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

주의:

- 조직 정책이 강하면 이 단계에서 보안팀 또는 IT 관리자 승인이 필요할 수 있다.
- 시스템 전체 정책은 바꾸지 말고, 가능한 한 `CurrentUser`만 사용한다.

## IIHS 접근 권한 선확인

이 프로젝트는 로그인 없이 완료되지 않는다. 아래를 먼저 확인한다.

- 브라우저에서 `https://techdata.iihs.org/` 접속 가능
- `Log in to IIHS TechData` 링크 노출
- Microsoft 로그인 화면 진입 가능
- 계정/암호/MFA 완료 가능

## 이 단계 종료 체크리스트

- 새 폴더가 생성되었다.
- `node -v`가 `24.x`다.
- `npm -v`가 정상이다.
- PowerShell에서 `.ps1` 실행이 가능한 상태다.
- IIHS TechData 로그인에 사용할 계정이 준비되었다.
- 이후 단계를 계속 진행할 수 있는 네트워크 상태다.

## 실패 시 조치

- `node:sqlite` 관련 오류가 예상되면 Node 24 LTS 계열로 재설치한다.
- 회사 프록시 때문에 `npm install` 실패가 예상되면 먼저 프록시 설정부터 해결한다.
- IIHS 로그인 자체가 안 되면, 코드 작성보다 계정 문제를 먼저 해결한다.
