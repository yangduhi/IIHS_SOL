# 실패 기록

## 템플릿
- `[YYYY-MM-DD HH:mm:ss +TZ] 단계: <단계> | 실패: <내용> | 원인: <원인> | 조치: <조치>`

## 기록
- [2026-03-06 16:05:00 +09:00] 단계: auth-discovery | 실패: Playwright MCP 브라우저 launch 실패 | 원인: 이 환경에서 persistent Chrome launch가 불안정함 | 조치: Playwright MCP 대신 `playwright-cli` 경로를 기본 사용 경로로 전환
- [2026-03-06 16:30:00 +09:00] 단계: codex-init-review | 실패: `codex /init` 자동 생성물에 대화 로그와 세션 캐시가 포함되어 민감정보가 저장될 수 있음 | 원인: `/init` 가 workspace 문서화 과정에서 세션 기반 보고서와 대화 산출물을 생성함 | 조치: `docs/changes/`, `docs/conversations/`, `docs/sessions/`, `docs/reports/` 를 Git 추적에서 제외하고 생성 파일은 삭제
