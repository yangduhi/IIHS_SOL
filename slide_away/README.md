# 슬라이드 어웨이 연구 표준

## 목적

이 폴더는 IIHS Small Overlap 프로젝트의 `slide_away` 연구를 위한 작업 표준입니다.
연구 프레임, 필요한 데이터 마트, 실행 순서 및 단계 게이트를 동결합니다.

이 패키지는 아래 순서대로 읽고 따라야 합니다.

1. `01_work_instruction.md`
2. `02_execution_plan.md`
3. `03_phase_checklists.md`

## 현재 기준선 스냅샷

참조 스냅샷 날짜: `2026-03-11`

- `filegroups`: `413`
- `vehicles`: `368`
- `signal-ready cohort`: `406`
- `driver-side`: `361`
- `passenger-side`: `52`
- `standard_baseline`: `406`
- `strict_origin`: `406`
- `standard_baseline_full_tdms`: `400`
- `pdf_documents`: `472`
- `pdf_result_tables`: `3337`
- `pdf_result_rows`: `37073`
- `extracted_metrics`: `216506`

`research.sqlite`에서 관찰된 현재 PDF 결과 테이블 적용 범위:

- `intrusion`: `340` 문서 / `340` 테이블
- `restraint_kinematics`: `399` 문서 / `452` 테이블
- `leg_foot_injury`: `421` 문서 / `421` 테이블
- `head_injury`: `419` 문서 / `472` 테이블
- `neck_injury`: `418` 문서 / `418` 테이블
- `chest_injury`: `422` 문서 / `422` 테이블
- `thigh_hip_injury`: `348` 문서 / `348` 테이블
- `dummy_clearance`: `412` 문서 / `464` 테이블

## 현재 검토 상태

검토 날짜: `2026-03-11`

- 상태: `hold before final approval`
- 연구 프레임, 측면 조화 규칙 및 결과 축은 구조적으로 일관성을 유지합니다.
- 이제 표준 스크립트 인터페이스 클로저, `signal_ready_flag` 증거 및 단계 아티팩트가 저장소에 존재합니다.
- 나머지 보류 사유는 포장이 아닌 검증입니다.
- 현재 window sweep는 `100 ms`를 선호하지만 해당 운영 창 승격은 여전히 수동 승인이 필요합니다.
- 창 검토에서는 `100 ms`가 과거 `0-150 ms` 기준선보다 약간 앞선 것으로 표시되므로 이전 기준선은 아직 폐기되지 않았습니다.
- 현재 모드 분석에서는 불균형이 심한 `k=2`(`392 / 6`)를 선택하므로 최종 모드 표준이 승인되지 않습니다.
- 마이너 클러스터 검토에 따르면 `6` 사례 클러스터는 모두 `driver`이고 `2012 - 2013`로 제한되므로 confounding 가능성은 여전히 타당합니다.
- 현재 RI-안전 연결은 약하며 유리한 redirection 주장을 정당화하지 않습니다.
- 확장된 연결 검토에서는 프록시 인식 연결이 RI만 사용하는 것보다 낫다는 것을 보여주지만 그 이득은 대부분 harshness 및 seat-response 컨텍스트에서 비롯됩니다.
- 도메인 결과 연결은 가장 강력한 현재 신호가 풀링된 redirection 축이 아닌 lower-extremity 결과에 있음을 보여줍니다.
- 사전 등록된 하위 그룹 검증은 `passenger` 및 `2015-2017` 하위 신호를 검토자 증거로만 유지합니다.
- 이제 승인 로직은 pooled 심각도를 요약 전용으로 처리하고 lower-extremity를 기본 검토 도메인으로 처리합니다.
- 도메인 점수 민감도 검토에서는 `lower_extremity`가 테스트한 `7/7` score-definition scenario에서 winning domain으로 유지됩니다.
- 관찰 중심의 명명에서는 이제 `bulk moderate / unresolved` 및 `high-lateral review pocket`를 사용합니다.
- 기본 `unittest` 적용 범위에는 이제 기능 규칙, 창 선택 및 도메인 가입 동작이 포함되지만 검증 깊이는 여전히 최종 운영 표준보다 낮습니다.
- 현재 패키지는 해결되지 않은 모드 표준화를 갖춘 검증된 연구 패키지로 가장 잘 처리됩니다.

## 동결 연구 결정

- 연구 프레임은 고정된 이진 유형 분류가 아닙니다.
- 기본 프레임은 연속체의 `barrier-relative kinematics`이고 두 번째 축은 `safety outcome`입니다.
- 첫 번째 연구 대상은 전체 차량 에너지 회계가 아닌 `occupant-compartment pulse and kinematics`입니다.
- 기본 물리적 읽기 계층은 occupant-compartment `x/y/z` 가속입니다.
  - `x`: ride-down 및 종방향 펄스
  - `y`: barrier-relative 측면화 및 redirection
  - `z`: 수직 harshness 및 휠 또는 서스펜션 경로 응답
- 작동하는 운동학 프레임은 `x+y` 단독이 아닌 `x+y+z`입니다.
- `x/y/z`는 독립형 승인 규칙이 아닌 주요 설명 레이어입니다.
- 좌석이나 발 또는 구획 반응 신호는 상황 및 증폭 역할을 합니다.
- 도메인 결과는 승인 계층으로 유지됩니다.
- `standard_baseline`는 표준 분석 모드입니다.
- `strict_origin`는 민감도 확인에만 사용됩니다.
- barrier-relative 표지판이 조화되기 전에는 운전석과 조수석이 합쳐져서는 안 됩니다.
- 기본 검색 창은 `0-150 ms`입니다.
- 견고성 창은 `0-250 ms`입니다.
- 첫 번째 안정적인 기준 코호트는 `driver-side only`입니다.
- Passenger-side 분석은 driver-side 기준선이 검증된 후의 확장 계층입니다.
- 결과 강화는 이미 `data/research/research.sqlite`에 있는 PDF 결과 테이블에서 시작됩니다.

## 폴더 내용

- `README.md`
  - 인덱스 및 고정 결정
- `01_work_instruction.md`
  - 권위 있는 학습 지도
- `02_execution_plan.md`
  - 세부 단계별 실행계획
- `03_phase_checklists.md`
  - 각 단계의 진입, 퇴출 및 QA 체크리스트
- `reviews/01_governance/01_final_review.md`
  - 현재 승인현황 및 폐쇄사항
- `reviews/01_governance/03_authoritative_snapshot_note.md`
  - 최신 rerun 기준 문서와 authoritative snapshot 규칙
- `reviews/02_execution/01_script_interface_map.md`
  - 실행된 스크립트 인터페이스 클로저
- `reviews/03_analysis/03_window_candidate_review.md`
  - `100 ms` 대 역사적인 `0-150 ms` 비교 메모
- `reviews/03_analysis/04_minor_cluster_review.md`
  - `6` 사례 마이너 클러스터에 대한 수동 검토 메모
- `reviews/03_analysis/05_extended_linkage_review.md`
  - RI, harshness, seat-response 및 하위 그룹 연결 메모
- `reviews/03_analysis/07_domain_outcome_linkage_review.md`
  - 구조, lower-extremity, 제한, head-neck-chest 전반에 걸친 도메인 분할 연계 메모
- `reviews/03_analysis/11_preregistered_lower_ext_subgroup_validation.md`
  - 승객 및 `2015-2017` 하위 외부 신호에 대한 고정 규칙 하위 그룹 검증
- `reviews/03_analysis/12_mode_confounding_signoff.md`
  - 선택한 모드 구조에 대한 측면, 시대, 계열 및 가중치 프록시 sign-off
- `reviews/03_analysis/13_domain_approval_logic_review.md`
  - 풀링된 메모와 도메인 인식 승인 결정 메모
- `reviews/03_analysis/14_observation_flavored_naming_review.md`
  - 현재 선택된 구조에 대한 보수적인 작업 이름
- `reviews/03_analysis/15_domain_score_sensitivity_review.md`
  - domain-first approval frame의 score-definition 민감도 검토
- `reviews/01_governance/02_next_step_plan.md`
  - 현재 `hold` 상태에서 우선 순위가 지정된 차단 감소 계획
- `reviews/README.md`
  - 폴더 색인 및 카테고리 구조 검토
- `final_study_brief.md`
  - 현재 연구 결과 및 해석
- `final_decision_log.md`
  - 최종 승인 결정 및 승격 조건

## 필수 소스 경로

- `data/research/research.sqlite`
- `data/analysis/filegroups.csv`
- `output/small_overlap/tables/canonical_small_overlap_tests.csv`
- `output/small_overlap/tables/analysis_cohort_counts.csv`
- `output/small_overlap/tables/signal_feature_summary__standard_baseline__official_known_harmonized_v3_window015.json`
- `data/derived/small_overlap/preprocessed_signals`
- `docs/signals/preprocessing_db_design.md`

참고:

- `signal_ready_flag`는 `research.sqlite` `preprocessing_cases` 적용 범위 또는 `data/derived/small_overlap/preprocessed_signals`의 동등한 매니페스트에서 재현 가능해야 합니다.

## 업데이트 규칙

향후 변경으로 인해 연구 범위, 좌표 규칙, 기능 정의, 코호트 정책 또는 단계 게이트가 수정되는 경우 이 폴더의 네 가지 핵심 문서를 함께 업데이트하세요.
`README.md`, `01_work_instruction.md`, `02_execution_plan.md` 및 `03_phase_checklists.md`.
하나의 파일만 업데이트하고 다른 파일은 일관성이 없는 상태로 두지 마십시오.
