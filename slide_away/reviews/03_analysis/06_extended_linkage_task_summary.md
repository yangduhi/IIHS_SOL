# 확장된 연결 작업 요약

- 날짜: `2026-03-11`
- 범위: RI 전용 상관관계를 넘어 `slide_away` 결과 연계 확장
- 상태: `completed with approval state still on hold`

## 추가된 내용

- 새 검토 진입점: `scripts/review_extended_linkage.py`
- 새로운 실행 모듈: `scripts/tools/slide_away/review_extended_linkage.py`
- 새 리뷰 메모: `reviews/03_analysis/05_extended_linkage_review.md`
- 새 테이블:
  - `artifacts/tables/extended_linkage_signal_summary.csv`
  - `artifacts/tables/extended_linkage_model_summary.csv`
  - `artifacts/tables/extended_linkage_subgroup_summary.csv`
- 새로운 그림:
  - `artifacts/figures/extended_linkage_overview.png`
- 새로운 연기 범위:
  - `tests/slide_away/test_extended_linkage.py`

## 사용된 링키지 스택

- `RI_100`
- `harshness_proxy_z`
  - 표준화된 `window_100_max_abs_ax_g`를 의미합니다.
  - 표준화된 `window_100_max_abs_ay_g`를 의미합니다.
- `seat_response_proxy_z`
  - 표준화된 `window_100_seat_twist_peak_mm`를 의미합니다.
  - 표준화된 `window_100_foot_resultant_asymmetry_g`를 의미합니다.
- 상호작용 조건:
  - `RI_z x harshness_proxy_z`
  - `RI_z x seat_response_proxy_z`

## 주요 결과

- RI 전용 모델 조정 R^2: `-0.0016`
- RI + harshness + seat-response 프록시 조정 R^2: `0.0689`
- RI + 상호작용 항 조정 R^2: `0.0654`
- 가장 강한 단일 신호: `seat_response_proxy_z`
  - 피어슨 r: `0.2099`
  - 상단 대 하단 4분위수 안전 격차: `0.5379`

## 하위 그룹 읽기

- 승객 하위 그룹:
  - `n=52`
  - 상호작용 모델 조정 R^2: `0.2677`
- `2015-2017`였습니다:
  - `n=131`
  - 상호작용 모델 조정 R^2: `0.2736`
- 현재 해석:
  - 흥미롭지만 여전히 탐구적이다

## 결정 영향

- 결과 연결은 RI 단독보다 컨텍스트가 더 강합니다.
- 대부분의 이득은 RI 상호 작용 용어가 아닌 harshness 및 seat-response 컨텍스트에서 발생합니다.
- 이는 RI를 연결 스택의 한 구성 요소로 유지하는 것을 지원합니다.
- 이는 최종적으로 호의적이거나 불리한 redirection 주장을 정당화하지 않습니다.
- 승인 상태는 `hold`로 유지됩니다.
