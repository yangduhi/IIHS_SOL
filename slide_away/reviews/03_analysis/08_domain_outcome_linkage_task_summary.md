# 도메인 결과 연계 작업 요약

- 날짜: `2026-03-11`
- 범위: 풀링된 안전 심각도에만 의존하는 대신 결과 도메인 전체에 걸쳐 `slide_away` 연결을 분할합니다.
- 상태: `completed with approval state still on hold`

## 추가된 내용

- 새 검토 진입점: `scripts/review_domain_outcome_linkage.py`
- 새로운 실행 모듈: `scripts/tools/slide_away/review_domain_outcome_linkage.py`
- 새 리뷰 메모: `reviews/03_analysis/07_domain_outcome_linkage_review.md`
- 새 테이블:
  - `artifacts/tables/domain_outcome_scores.csv`
  - `artifacts/tables/domain_linkage_signal_summary.csv`
  - `artifacts/tables/domain_linkage_model_summary.csv`
  - `artifacts/tables/domain_linkage_subgroup_summary.csv`
- 새로운 그림:
  - `artifacts/figures/domain_linkage_overview.png`
- 새로운 연기 범위:
  - `tests/slide_away/test_domain_outcome_linkage.py`

## 주요 결과

- RI 전용 연결은 모든 도메인에서 약한 상태로 유지됩니다.
- lower-extremity는 컨텍스트 인식 연결을 위한 가장 강력한 현재 도메인입니다.
  - 프록시 모델 조정 R^2: `0.0653`
- 구조/침입은 개선되지만 강도는 약해집니다.
  - 프록시 모델 조정 R^2: `0.0361`
- head-neck-chest는 seat-response보다 harshness에 더 잘 맞습니다.
  - 프록시 모델 조정 R^2: `0.0501`
- 구속/운동학은 여전히 약함
  - 프록시 모델 조정 R^2: `0.0138`

## 하위 그룹 읽기

- 승객 lower-extremity 상호작용 모델 조정 R^2: `0.3105`
- 시대 `2015-2017` lower-extremity 상호작용 모델 조정 R^2: `0.3980`
- 현재 읽은 내용:
  - 유망하지만 여전히 탐색적임

## 결정 영향

- RI는 연결 스택에 남아 있어야 하지만 선행 설명 축으로 남아서는 안 됩니다.
- seat-response 및 harshness 컨텍스트는 이제 풀링된 redirection 전용 스토리보다 더 강력하게 지원됩니다.
- 이름 지정은 단순한 redirection-versus-crush 프레임이 아닌 multiaxis 프레임으로 이동해야 합니다.
- 승인 상태는 `hold`로 유지됩니다.
