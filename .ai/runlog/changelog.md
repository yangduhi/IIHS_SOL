# 변경 이력

## 템플릿
- `[YYYY-MM-DD HH:mm:ss +TZ] 파일: <목록> | 사유: <내용> | 검증: PASS/FAIL (<근거>)`

## 기록
- [2026-03-06 16:20:00 +09:00] 파일: docs/iihs-small-overlap-download-work-instructions.md, docs/field-notes.md, scripts/capture-session.ps1 | 사유: IIHS TechData 로그인, Small Overlap 목록 경로, RSS, 파일 다운로드 인증 조건을 실제 검증하고 문서화함 | 검증: PASS (output/playwright/authenticated-home.md, docs/field-notes.md)
- [2026-03-06 16:25:00 +09:00] 파일: .vscode/settings.json, .vscode/extensions.json, .ai/*, .gitignore | 사유: 상위 워크스페이스의 유용한 편집기 설정과 에이전트 운영 규칙을 현재 IIHS 프로젝트에 맞게 선별 적용함 | 검증: PASS (파일 생성 및 내용 검토)
- [2026-03-06 16:30:00 +09:00] 파일: .gitignore, .ai/runlog/changelog.md, .ai/runlog/failures.md | 사유: `codex /init` 실행 결과를 검토한 뒤, 세션/대화/리포트 자동 생성물이 기존 운영 문서와 의미 중복되고 민감정보를 포함할 수 있어 Git 추적 대상에서 제외함 | 검증: PASS (`/init` 실행 후 생성물 검토 및 민감정보 검색)
