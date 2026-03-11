# 도메인 점수 민감도 작업 요약

- generated_at: `2026-03-11T06:28:26Z`
- 상태: `completed`

## 작업 범위

- current domain-first approval frame이 score 정의 변화에 민감한지 점검
- `lower_extremity`가 reasonable score-definition perturbation에서도 primary domain으로 남는지 검토
- lower-ext 내부에서 어떤 구성요소가 실제 설명력을 주도하는지 분해

## 생성 산출물

- `slide_away/artifacts/tables/domain_score_sensitivity_summary.csv`
- `slide_away/artifacts/tables/lower_ext_component_sensitivity.csv`
- `slide_away/artifacts/figures/domain_score_sensitivity_overview.png`
- `slide_away/reviews/03_analysis/15_domain_score_sensitivity_review.md`

## 핵심 결과

- `lower_extremity_score`는 테스트한 `7/7` scenario에서 winning domain으로 유지됨
- baseline lower-ext adj R^2: `0.0877`
- `leg_foot_only` lower-ext adj R^2: `0.1256`
- `foot_only` lower-ext adj R^2: `0.3366`
- passenger `foot_only` adj R^2: `0.5293`
- `2015-2017` era `foot_only` adj R^2: `0.5574`
- `thigh_only` overall adj R^2: `0.0052`

## 의미

- domain-first approval frame은 이번 sensitivity pass 이후 더 방어 가능해짐
- current lower-ext signal은 `thigh`보다 `foot / lower-ext pulse context`에 더 많이 실림
- lower-ext primary-domain 결론은 proxy 정의 변화에 쉽게 무너지지 않음
- 다만 이 결과만으로 최종 approval을 닫을 수는 없고, 남은 reviewer sign-off는 계속 필요함
