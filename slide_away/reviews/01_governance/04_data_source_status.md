# 데이터 소스 상태 메모

- snapshot_id: `slide_away_authoritative_2026-03-11`
- generated_at: `2026-03-11`
- authoritative_as_of: `2026-03-11`
- status: `active reviewer reference`
- primary_db: `data/research/research.sqlite`
- deprecated_db_placeholder: `data/research.sqlite`
- current_window_candidate: `100 ms`
- historic_window_reference: `0-150 ms`

## 목적

다음 분석자와 리뷰어가 어떤 DB와 어떤 산출물을 authoritative source로 읽어야 하는지 고정합니다.
이 메모는 `research.sqlite` 경로 혼동과 rerun 스냅샷 혼동을 닫기 위한 provenance note입니다.

## 현재 경로 상태

- `data/research/research.sqlite`
  - 상태: `authoritative`
  - 크기: `404,312,064 bytes`
  - 역할: `slide_away` 재실행과 review evidence 생성에 사용된 실제 연구 DB
- `data/research.sqlite`
  - 상태: `deprecated placeholder`
  - 크기: `0 bytes`
  - 역할: 과거 경로 흔적만 남아 있으며, 현재 rerun이나 review 판단에 사용하지 않음

## authoritative chain

1. 원천 DB: `data/research/research.sqlite`
2. canonical cohort reference: `output/small_overlap/tables/canonical_small_overlap_tests.csv`
3. rerun mart 및 summary: `slide_away/artifacts/*`
4. reviewer evidence: `slide_away/reviews/*`
5. 최종 상태 판단: `reviews/01_governance/*`, `final_study_brief.md`, `final_decision_log.md`

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

## reviewer 해석 규칙

- `data/research/research.sqlite`만 authoritative DB로 취급합니다.
- `data/research.sqlite`는 비어 있으므로 source of truth로 사용하지 않습니다.
- 수치가 충돌하면 `reviews/01_governance/01_final_review.md`와 `reviews/01_governance/03_authoritative_snapshot_note.md`를 먼저 따릅니다.
- 중간 task summary 문서는 provenance용으로 유지하되, 최종 승인 수치의 authoritative source로 사용하지 않습니다.

## 현재 판단

- 데이터 원천 자체는 현재 승인 blocker가 아닙니다.
- blocker는 DB 경로가 아니라 validation weakness와 unresolved mode standardization입니다.
- 이후 review memo는 모두 이 메모와 동일한 DB 기준을 명시해야 합니다.
