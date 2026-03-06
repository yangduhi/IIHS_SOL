# runlog 운영 가이드

## 목적
- 실행 이력, 가정, 실패, 검증 증거를 추적 가능하게 유지한다.

## 필수 파일
- `master_status.json`
- `changelog.md`
- `assumptions.md`
- `failures.md`
- `reports/`

## 기록 원칙
- 기존 기록은 삭제하지 않고 append 한다.
- 시간, 범위, 근거를 포함한다.
- 검증 실패는 생략하지 않고 즉시 기록한다.
