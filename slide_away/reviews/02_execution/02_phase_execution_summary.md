# 슬라이드 어웨이 단계 실행 요약

- 날짜: `2026-03-11`
- 상태: `completed through Phase 8 with final approval still on hold`

## 0단계

- 표준 래퍼 인터페이스가 닫혔습니다.
- `reviews/02_execution/01_script_interface_map.md`에 문서화된 스크립트 맵

## 1단계

- `case_master.parquet` 내장
- 표준 사례: `413`
- 신호 준비 케이스: `406`

## 2단계

- `outcomes_v1.parquet` 내장
- 평균 결과 품질 점수: `0.8054`
- 침입 범위: `329`

## 3단계

- `features_v1.parquet` 및 `features_v1_strict_origin.parquet` 내장
- 표준 기준 기능 행: `406`
- 클러스터 입력 준비 행: `398`

## 4단계

- `window_sweep_summary.csv` 내장
- 현재 최고 운영 기간: `100 ms`
- 최고의 `k`: `2`
- `x/y/z` 기능 새로 고침 후의 실루엣: `0.7206`

## 5단계

- `mode_study_summary.csv` 내장
- 선택한 모드 개수: `2`
- 클러스터 분할: `392 / 6`
- 결과는 잠정적으로만 남아 있음

## 6단계

- `ri_vs_safety_map.csv` 및 피규어 제작
- 현재 RI 대 안전 심각도 상관관계: `0.0193`

## 7단계

- `04_casebooks/01_matched_pair_casebook.md` 내장
- `04_casebooks/02_structure_strategy_codebook.csv` 내장
- 쌍 수: `12`

## 8단계

- `final_study_brief.md` 내장
- `final_decision_log.md` 내장
- 최종 승인 상태는 `hold`로 유지됩니다.

## 사후 차단제 검토

- `03_analysis/03_window_candidate_review.md` 내장
- `03_analysis/04_minor_cluster_review.md` 내장
- `03_analysis/05_extended_linkage_review.md` 내장
- `03_analysis/07_domain_outcome_linkage_review.md` 내장
- `03_analysis/11_preregistered_lower_ext_subgroup_validation.md` 내장
- `03_analysis/12_mode_confounding_signoff.md` 내장
- `03_analysis/13_domain_approval_logic_review.md` 내장
- `03_analysis/14_observation_flavored_naming_review.md` 내장
- `03_analysis/15_domain_score_sensitivity_review.md` 내장
- `100 ms`는 현재 최고의 후보로 남아 있지만 역사적 `0-150 ms`는 아직 폐기되지 않았습니다.
- confounding가 여전히 그럴듯하기 때문에 `6` 사례 마이너 클러스터는 검토 전용으로 유지됩니다.
- 프록시 인식 연결은 RI 단독보다 우수하지만 상호 작용 이득은 여전히 미미합니다.
- 도메인 연결은 가장 강력한 현재 신호가 lower-extremity 결과에 있음을 보여줍니다.
- 사전 등록된 하위 그룹 검증은 `passenger` 및 `2015-2017` 하위 힌트를 승인 등급 주장이 아닌 검토 증거로 유지합니다.
- 승인 로직은 이제 pooled 심각도를 요약 전용으로 처리하고 lower-extremity를 기본 검토 도메인으로 처리합니다.
- 도메인 점수 민감도 검토에서는 `lower_extremity`가 테스트한 `7/7` scenario에서 primary domain으로 유지됩니다.
- 관찰 중심의 명명에서는 이제 `bulk moderate / unresolved` 및 `high-lateral review pocket`를 사용합니다.
- `unittest` 적용 범위에는 이제 기능 규칙, 창 선택 및 도메인 가입 동작이 포함됩니다.
- 연기 결과: `14` 테스트 통과
