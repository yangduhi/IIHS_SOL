# 슬라이드 어웨이 authoritative snapshot 메모

- 날짜: `2026-03-11`
- 상태: `active`

## 목적

중간 rerun 문서와 최종 rerun 문서가 혼재할 때 어떤 데이터 소스와 어떤 문서를 authoritative snapshot으로 볼지 고정합니다.

## authoritative source of truth

- 기본 DB: `data/research/research.sqlite`
- canonical cohort reference: `output/small_overlap/tables/canonical_small_overlap_tests.csv`
- 최종 rerun 산출물: `slide_away/artifacts/*`
- 최종 rerun review evidence: `slide_away/reviews/*`

## 문서 우선순위

수치나 문장이 충돌하면 아래 순서로 해석합니다.

1. `reviews/01_governance/01_final_review.md`
2. `reviews/01_governance/03_authoritative_snapshot_note.md`
3. `reviews/01_governance/02_next_step_plan.md`
4. `reviews/03_analysis/10_xyz_primary_frame_note.md`
5. `reviews/03_analysis/11_preregistered_lower_ext_subgroup_validation.md`
6. `reviews/03_analysis/13_domain_approval_logic_review.md`
7. `reviews/03_analysis/14_observation_flavored_naming_review.md`
8. `reviews/03_analysis/15_domain_score_sensitivity_review.md`
9. `final_study_brief.md`
10. `final_decision_log.md`

초기 설계 문서와 중간 task summary는 provenance 용도로 유지하되, 최종 판단이나 최신 수치의 authoritative source로는 사용하지 않습니다.

## 현재 authoritative snapshot

- canonical `filegroups`: `413`
- signal-ready cohort: `406`
- driver: `361`
- passenger: `52`
- feature mart rows: `406`
- cluster-ready rows: `398`
- current best window candidate: `100 ms`
- selected mode structure: `k=2`, `392 / 6`
- pooled RI vs safety correlation: `0.0193`
- proxy-aware pooled linkage adj R^2: `0.0748`
- current primary domain: `lower_extremity`
- lower-ext proxy model adj R^2: `0.0877`
- domain score sensitivity result: `lower_extremity` winner in `7/7` tested score-definition scenarios

## 해석 규칙

- `x/y/z`는 authoritative physical reading frame입니다.
- `RI`는 그 안의 구성요소로 유지하되 standalone approval axis로 읽지 않습니다.
- 최종 approval layer는 pooled severity가 아니라 domain-aware outcome입니다.
- 현재 `hold`의 의미는 package 미완성이 아니라 validation weakness와 unresolved mode standardization입니다.
