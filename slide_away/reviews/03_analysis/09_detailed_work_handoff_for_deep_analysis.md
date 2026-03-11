# 심층 분석을 위한 상세한 작업 핸드오프

- 날짜: `2026-03-11`
- 상태: `active handoff`
- 현재 승인 상태: `hold`
- 대상 독자: 심층 분석을 계속하고 현재 가정에 도전하거나 최종 모드 분류를 재설계할 차세대 분석가

## 1. 요약

이 저장소 스냅샷은 더 이상 아이디어 단계 연구가 아닙니다.
이제 실행 가능한 ETL, 기능 엔지니어링, 클러스터링, 아티팩트 검토 및 후속 연계 분석을 포함하는 재현 가능한 연구 패키지입니다.

현재 가장 강력한 해석은 다음과 같습니다.

- 패키지가 작동하고 재현 가능합니다.
- `RI`만으로는 공동 승인 신호로 약함
- `harshness` 및 `seat-response` 컨텍스트가 추가되면 연결이 향상됩니다.
- 가장 강력한 현재 도메인은 풀링된 redirection 축이 아닌 `lower-extremity`입니다.
- 현재 증거는 최종 `redirection-dominant` / `crush-dominant` 운영 이름을 정당화하지 않습니다.
- 모드 표준화가 아직 해결되지 않았기 때문에 승인은 `hold`로 유지됩니다.

## 2. 권장 읽기 순서

다음 순서로 `reviews` 폴더를 읽습니다.

1. `reviews/01_governance/01_final_review.md`
2. `reviews/01_governance/02_next_step_plan.md`
3. `reviews/02_execution/01_script_interface_map.md`
4. `reviews/02_execution/02_phase_execution_summary.md`
5. `reviews/03_analysis/03_window_candidate_review.md`
6. `reviews/03_analysis/04_minor_cluster_review.md`
7. `reviews/03_analysis/05_extended_linkage_review.md`
8. `reviews/03_analysis/07_domain_outcome_linkage_review.md`
9. `reviews/03_analysis/09_detailed_work_handoff_for_deep_analysis.md`
10. `reviews/03_analysis/10_xyz_primary_frame_note.md`
11. `reviews/03_analysis/11_preregistered_lower_ext_subgroup_validation.md`
12. `reviews/03_analysis/12_mode_confounding_signoff.md`
13. `reviews/03_analysis/13_domain_approval_logic_review.md`
14. `reviews/03_analysis/14_observation_flavored_naming_review.md`
15. `reviews/04_casebooks/01_matched_pair_casebook.md`

검토 폴더 색인은 다음과 같습니다.

- `reviews/README.md`

## 3. 핵심 연구 프레임

`slide_away` 연구는 현재 다음과 같이 구성됩니다.

- 분석 단위: `filegroup_id`
- 기본 모드: `standard_baseline`
- 감도 모드: `strict_origin`
- 첫 번째 안정적인 기준 코호트: `driver-only`
- 승객 데이터는 barrier-relative 부호 조화 후에만 허용됩니다.
- 기본 창 기록:
  - 과거 운영 기준: `0-150 ms`
  - 현재 window sweep의 최고 후보: `100 ms`
- 견고성 창: `0-250 ms`

주요 물리적 프레임:

- 운전석에서는 `a_y_away = +a_y`를 사용합니다.
- 조수석 쪽은 `a_y_away = -a_y`를 사용합니다.
- `RI`는 barrier-relative 측면 대 세로 방향 Delta-V로 정의됩니다.
- occupant-compartment `x/y/z` 가속은 기본 물리적 읽기 계층입니다.
  - `x`: ride-down 및 종방향 펄스
  - `y`: barrier-relative 측면화 및 redirection
  - `z`: 수직 harshness 및 휠 또는 서스펜션 경로 응답
- 현재 해석은 더 이상 "RI가 지배해야 한다"가 아닙니다.
- 현재 해석은 "RI는 multiaxis 연결 스택 내부의 하나의 구성 요소입니다"입니다.
- 현재 해석은 "x/y/z만으로는 충분하지 않습니다"
- 현재 해석은 "x/y/z가 주요 설명 레이어이고 그 다음 좌석 또는 발 또는 구획 응답, 그 다음 도메인 결과"입니다.

3계층 분석 프레임:

- `Level 1`: 차량 운동학 및 펄스
  - `x/y/z` 가속도, Delta-V, RI, 타이밍, 펄스 지속 시간
- `Level 2`: 구획 및 점유자 응답 컨텍스트
  - 좌석 비틀림, 발 비대칭, 아래쪽 확장 프록시, 구속 타이밍 프록시
- `Level 3`: 승인 및 결과 증거
  - 침입, lower-extremity, 구속/운동학, head-neck-chest

## 4. 소스 데이터 및 종속성 구조

기본 입력:

- `data/research/research.sqlite`
- `output/small_overlap/tables/canonical_small_overlap_tests.csv`
- `data/derived/small_overlap/preprocessed_signals`
- `docs/signals/preprocessing_db_design.md`

직접 사용되는 중요한 데이터베이스 테이블:

- `preprocessing_cases`
  - `signal_ready_flag`를 재현하는 데 사용됨
- `pdf_result_row_catalog`
  - 주요 결과 ETL 소스로 사용됨
- 결과 ETL에 사용되는 PDF 계열:
  - `intrusion`
  - `leg_foot_injury`
  - `restraint_kinematics`
  - `head_injury`
  - `chest_injury`
  - `neck_injury`
  - `thigh_hip_injury`
  - `dummy_clearance`

## 5. 현재 검토 및 분석 폴더 구조

정렬된 검토 구조:

- `slide_away/reviews/01_governance`
  - 승인상태, 최종검토, 다음단계 계획
- `slide_away/reviews/02_execution`
  - 스크립트 인터페이스 클로저, 단계 실행 요약
- `slide_away/reviews/03_analysis`
  - 분석메모, 연계메모, 모드리뷰, 상세핸드오프
- `slide_away/reviews/04_casebooks`
  - matched-pair 사례집 및 구조 코드북

유물 구조:

- `slide_away/artifacts/marts`
  - 쪽모이 세공 마트
- `slide_away/artifacts/tables`
  - 클러스터링, 연결, confounding 및 검토를 위한 표 형식 출력
- `slide_away/artifacts/figures`
  - 요약 수치
- `slide_away/artifacts/logs`
  - 실행 로그

## 6. 파이프라인 개요

구현된 워크플로는 다음과 같습니다.

1. `case_master` 빌드
2. `outcomes_v1` 빌드
3. `features_v1` 및 `features_v1_strict_origin` 빌드
4. `window_sweep`를 실행
5. `mode_study`를 실행
6. `ri_vs_safety_map` 빌드
7. `matched_pair_casebook` 빌드
8. 차단 감소 검토 실행
   - `window candidate review`
   - `minor cluster review`
   - `extended linkage review`
   - `domain outcome linkage review`

기본 래퍼 진입점:

- `scripts/build_case_master.py`
- `scripts/build_outcome_mart.py`
- `scripts/build_barrier_relative_features.py`
- `scripts/run_window_sweep.py`
- `scripts/run_mode_study.py`
- `scripts/build_ri_safety_map.py`
- `scripts/build_mode_casebook.py`
- `scripts/review_window_candidates.py`
- `scripts/review_minor_cluster.py`
- `scripts/review_extended_linkage.py`
- `scripts/review_domain_outcome_linkage.py`

주요 구현 모듈:

- `scripts/tools/slide_away/common.py`
- `scripts/tools/slide_away/modeling.py`
- `scripts/tools/slide_away/build_case_master.py`
- `scripts/tools/slide_away/build_outcome_mart.py`
- `scripts/tools/slide_away/build_barrier_relative_features.py`
- `scripts/tools/slide_away/run_window_sweep.py`
- `scripts/tools/slide_away/run_mode_study.py`
- `scripts/tools/slide_away/build_ri_safety_map.py`
- `scripts/tools/slide_away/build_mode_casebook.py`
- `scripts/tools/slide_away/review_window_candidates.py`
- `scripts/tools/slide_away/review_minor_cluster.py`
- `scripts/tools/slide_away/review_extended_linkage.py`
- `scripts/tools/slide_away/review_domain_outcome_linkage.py`

## 7. 구현된 데이터 구조

### 7.1 `case_master.parquet`

길:

- `slide_away/artifacts/marts/case_master.parquet`

관찰된 모양:

- 행: `413`
- 열: `78`

주요 열 그룹:

- 신원:
  - `filegroup_id`
  - `vehicle_id`
  - `test_code`
  - `title`
- 메타데이터:
  - `vehicle_year`
  - `vehicle_make_model`
  - `test_side`
  - `tested_on`
  - `era`
  - `make_model_family`
  - `analysis_cohort`
- 자산 범위:
  - `pdf_asset_count`
  - `workbook_asset_count`
  - `signalish_asset_count`
  - `pdf_document_count`
  - `excel_workbook_count`
  - `signal_container_count`
- 추출된 보고서 필드:
  - `report_speed_actual_kmh`
  - `report_speed_target_kmh`
  - `report_overlap_actual_pct`
  - `report_overlap_target_pct`
  - `report_curb_weight_kg_measured`
  - `report_test_weight_kg_measured`
- 파이프라인 플래그:
  - `signal_ready_flag`
  - `strict_origin_ready_flag`
  - `pdf_available_flag`
  - `excel_available_flag`
  - `vin_conflict_flag`
- 기원:
  - `standard_preprocessing_case_id`
  - `strict_preprocessing_case_id`
  - `signal_ready_rule`
  - `case_master_version`
  - `generated_at`

### 7.2 `outcomes_v1.parquet`

길:

- `slide_away/artifacts/marts/outcomes_v1.parquet`

관찰된 모양:

- 행: `413`
- 열: `27`

주요 결과 열:

- 구조:
  - `intrusion_max_resultant_cm`
  - `intrusion_footrest_resultant_cm`
  - `intrusion_left_toepan_resultant_cm`
  - `intrusion_brake_pedal_resultant_cm`
- lower-extremity:
  - `leg_foot_index_left`
  - `leg_foot_index_right`
  - `foot_resultant_accel_left_g`
  - `foot_resultant_accel_right_g`
  - `thigh_hip_risk_proxy`
- 구속/운동학:
  - `restraint_event_count`
  - `pretensioner_time_ms`
  - `airbag_first_contact_time_ms`
  - `airbag_full_inflation_time_ms`
- 부상:
  - `head_hic15`
  - `chest_rib_compression_mm`
  - `chest_viscous_criteria_ms`
  - `neck_tension_extension_nij`
- 정리:
  - `dummy_clearance_head_to_roof_mm`
  - `dummy_clearance_knee_to_dash_left_mm`
  - `dummy_clearance_knee_to_dash_right_mm`
  - `dummy_clearance_min_mm`
- QA/출처:
  - `outcome_quality_score`
  - `outcome_source_version`
  - `outcome_provenance_json`

### 7.3 `features_v1.parquet`

길:

- `slide_away/artifacts/marts/features_v1.parquet`

관찰된 모양:

- 행: `406`
- 열: `162`

기능 구조:

- 기본 정체성:
  - `filegroup_id`
  - `preprocessing_case_id`
  - `source_mode`
  - `test_code`
  - `test_side`
  - `era`
  - `make_model_family`
  - `analysis_cohort`
- 기본 기능 세트:
  - `delta_vx_mps`
  - `delta_vy_away_mps`
  - `lr`
  - `lr_100`
  - `ly`
  - `ly_40`
  - `ly_60`
  - `ri`
  - `ri_60`
  - `t_peak_x_ms`
  - `t_peak_y_ms`
  - `t_50_dvx_ms`
  - `max_abs_ax_g`
  - `max_abs_ay_g`
  - `pulse_duration_x_ms`
  - `pulse_duration_y_ms`
  - `seat_twist_peak_mm`
  - `foot_resultant_left_g`
  - `foot_resultant_right_g`
  - `foot_resultant_asymmetry_g`
  - `foot_x_left_right_diff_g`
  - `foot_z_left_right_diff_g`
  - 좌석/발 지연 기능
- 다중 창 열:
  - `window_020_*`
  - `window_040_*`
  - `window_060_*`
  - `window_080_*`
  - `window_100_*`
  - `window_120_*`
  - `window_150_*`
  - `window_250_*`
- 품질관리:
  - `cluster_input_flag`
  - `feature_quality_score`
  - `feature_version`

### 7.4 `features_v1_strict_origin.parquet`

길:

- `slide_away/artifacts/marts/features_v1_strict_origin.parquet`

관찰된 모양:

- 행: `406`
- 열: `162`

역할:

- `strict_origin`를 사용한 기능 마트의 민감도 복사본
- 현재 운영중인 마트로 사용되지 않음

### 7.5 `mode_case_assignments.csv`

길:

- `slide_away/artifacts/tables/mode_case_assignments.csv`

관찰된 모양:

- 행: `398`
- 열: `165`

역할:

- 클러스터링 준비 하위 집합
- 선택한 클러스터링 실행에 대한 대치된 창 기능 열을 포함합니다.
- 다음을 추가합니다:
  - `cluster_id`
  - `working_mode_label`
  - `exploratory_interpretation`

### 7.6 창/모드 요약표

- `slide_away/artifacts/tables/window_sweep_summary.csv`
  - 행: `8`
  - 열:
    - `window_ms`
    - `best_k`
    - `sample_count`
    - `silhouette`
    - `size_ratio`
    - `outcome_eta_sq`
    - `composite_score`
    - `candidate_scores_json`
    - `selected_operating_window`
    - `selected_robustness_window`

- `slide_away/artifacts/tables/mode_study_summary.csv`
  - 행: `3`
  - 열:
    - `k`
    - `sample_count`
    - `silhouette`
    - `inertia`
    - `min_cluster_size`
    - `max_cluster_size`
    - `size_ratio`
    - `selection_score`
    - `selected_flag`

### 7.7 연결 테이블

- `slide_away/artifacts/tables/ri_vs_safety_map.csv`
  - 행: `398`
  - 열: `193`
  - 역할: 풀링된 RI 연계 검토를 위한 기능 + 결과 + 모드 조인

- `slide_away/artifacts/tables/domain_outcome_scores.csv`
  - 행: `406`
  - 열: `12`
  - 역할: 심층 후속 분석을 위한 영역별 결과 점수 프레임
  - 주요 열:
    - `structure_intrusion_score`
    - `lower_extremity_score`
    - `restraint_kinematics_score`
    - `head_neck_chest_score`
    - `ri_100`
    - `harshness_proxy_z`
    - `seat_response_proxy_z`

- `slide_away/artifacts/tables/domain_linkage_model_summary.csv`
  - 행: `12`
  - 열: `13`
  - 역할: 도메인별 모형 적합 요약

## 8. 중요한 구현 규칙 및 예외

이러한 규칙은 해석에 실질적인 영향을 미칩니다.
다음 단계에서 이를 보존하거나 의식적으로 변경해야 합니다.

### 8.1 `signal_ready_flag`

현재 규칙:

- `mode='standard_baseline'`
- `status='done'`
- `harmonized_wide_path IS NOT NULL`

현재 재생 횟수:

- `406`

### 8.2 Barrier-relative 기호 처리

- 운전사:
  - `a_y_away = +a_y`
- 승객:
  - `a_y_away = -a_y`

이는 다음에 직접적인 영향을 미칩니다.

- `delta_vy_away_mps`
- `ly`
- `ri`
- 모든 창이 있는 측면 기능

### 8.3 RI 분모 가드

`common.py`의 현재 규칙:

- `RI = abs_delta_vy / abs_delta_vx`
- `abs_delta_vx >= 0.25`인 경우에만
- 그렇지 않으면 `RI = NaN`

이유:

- 세로 방향 델타 V가 0에 가까울 때 RI가 불안정하거나 폭발하는 것을 방지합니다.

### 8.4 기능 품질 및 클러스터링 적격성

현재 규칙:

- 기본 기능 품질 점수 `>= 0.875`인 경우 `cluster_input_flag = 1`

`modeling.py`의 현재 클러스터링 준비:

- `cluster_input_flag == 1`에서만 시작
- 선택한 창 기능 전체에 걸쳐 행 적용 범위 `>= 0.65`가 필요합니다.
- 중앙값 대치 나머지 누락 창 기능은 열 단위로 표시됩니다.

해석 영향:

- 클러스터링은 더 이상 "완전한 사례에만 해당"되지 않습니다.
- 선택된 클러스터링 샘플은 필터링되고 부분적으로 귀속된 분석 하위 집합입니다.

### 8.5 결과 타당성 필터

`build_outcome_mart.py`의 현재 규칙:

- `leg_foot_index_left > 5.0 -> NaN`
- `leg_foot_index_right > 5.0 -> NaN`

이유:

- 합동 점수 이전에 믿기 어려운 이상값을 억제합니다.

### 8.6 통합 안전 심각도 점수

현재 통합 점수는 다음의 표준화된 구성 요소를 결합합니다.

- 강요
- 다리 지수
- 발 가속
- 헤드 HIC15
- 갈비뼈 압축
- 새로운
- 허벅지 프록시

중요한 주의 사항:

- 이 통합 점수는 광범위한 검토에 유용합니다.
- 더 이상 유일한 승인 대상으로 취급되어서는 안 됩니다.
- 이제 심층 후속 분석을 위해 도메인 분할 점수가 선호됩니다.

## 9. 단계별 작업 완료

### 0단계. 실행 종료

완전한:

- 표준 래퍼 인터페이스가 닫혔습니다.
- 스크립트 인터페이스 맵 작성
- 표준화되고 정렬된 폴더 구조 검토

주요 증거:

- `reviews/02_execution/01_script_interface_map.md`

### 1단계. 케이스 마스터

완전한:

- `case_master.parquet` 구축
- 재현 `signal_ready_flag=406`
- 생성된 코호트, 측면, 시대, 자산 범위, 전처리 출처

주요 결과:

- 표준 사례: `413`
- 신호 준비: `406`
- 드라이버: `361`
- 승객: `52`

### 2단계. 아웃컴 마트

완전한:

- `outcomes_v1.parquet` 구축
- PDF 행 카탈로그를 사례 수준 결과 필드에 결합했습니다.
- 필드당 저장된 출처 규칙

주요 결과:

- 행 수: `413`
- 평균 결과 품질 점수: `0.8054`
- 침입 범위: `329`
- 헤드 HIC15 적용 범위: `406`
- 구속 이벤트 적용 범위: `387`

### 3단계. 피쳐마트

완전한:

- `features_v1.parquet` 구축
- `features_v1_strict_origin.parquet` 구축
- 계산된 다중 창 barrier-relative 신호 기능

주요 결과:

- 표준 기준 행: `406`
- 클러스터 입력 준비 행: `398`
- 평균 기능 품질 점수: `0.965825`

### 4단계. Window Sweep

완전한:

- 스윕 `20/40/60/80/100/120/150/250 ms`
- 저장된 후보자 점수 및 선택된 플래그

주요 결과:

- 현재 최고의 운영 후보: `100 ms`
- 선택한 견고성 창: `250 ms`
- 최고의 `100 ms` 실루엣: `0.7206`
- 역사적인 `150 ms` 실루엣: `0.7144`

중요한 해석:

- `100 ms`는 역사적인 `0-150 ms`보다 약간 앞서 있습니다.
- 현재 증거는 자동 승격에 충분하지 않습니다.

### 5단계. 모드 분석

완전한:

- 비교 `k=2/3/4`
- 엄선된 보수적인 작업 레이블
- 생성된 대표 사례 요약

주요 결과:

- `k=2`를 선택했습니다.
- 크기 분할: `392 / 6`
- `k=3`는 실루엣이 높지만 불균형이 심했습니다.
  - `100 ms`: `[390, 2, 6]`
  - `150 ms`: `[389, 6, 3]`

해석:

- `k=2`는 최종 분류 승격에 비해 여전히 너무 불균형합니다.
- `k=3`는 표준 작동 목적으로는 훨씬 덜 적합합니다.

### 6단계. 통합 결과 연계

완전한:

- `ri_vs_safety_map` 구축
- 풀링된 RI 분산 및 델타-V 위상 플롯 생성

주요 결과:

- 코호트 수준 `RI vs pooled safety severity` 상관관계: `0.0193`

해석:

- RI 전용 풀링 연결은 사실상 약합니다.

### 7단계. 사례집

완전한:

- 내장 matched-pair 사례집
- 구조적 전략 코드북 구축

주요 결과:

- 일치하는 쌍: `12`

### 사후 검토 작업

완전한:

- 창 후보 검토
- 마이너 클러스터 검토
- 확장된 연계 검토
- 도메인 결과 연계 검토

## 10. 주요 검토 결과

### 10.1 창구 후보 검토

원천:

- `reviews/03_analysis/03_window_candidate_review.md`

주요 읽기:

- `100 ms`, `k=2`: 실루엣 `0.7206`
- `150 ms`, `k=2`: 실루엣 `0.7144`
- 현재 최고의 후보는 `100 ms`로 남아 있습니다.
- 역사적인 `0-150 ms`를 자동으로 폐기하지 마십시오

`100 ms`와 `150 ms` 사이의 관심 목록 기능:

- `foot_resultant_asymmetry_g`
- `delta_vx_mps`
- `seat_twist_peak_mm`

### 10.2 소규모 클러스터 검토

원천:

- `reviews/03_analysis/04_minor_cluster_review.md`

주요 읽기:

- 작은 클러스터 크기: `6`
- 모두 `driver`
- 연도: `2012 - 2013`
- 모든 케이스는 소규모 브랜드 모델 세트에 속합니다.

해석:

- 안정적인 모드로 홍보하기에는 너무 혼란스럽습니다.

### 10.3 확장된 연계 검토

원천:

- `reviews/03_analysis/05_extended_linkage_review.md`

모델 결과:

- RI 전용 조정 R^2: `-0.0016`
- RI + harshness + seat-response 프록시 조정 R^2: `0.0748`
- RI + 상호작용 항 조정 R^2: `0.0703`

최고의 단일 신호:

- `seat_response_proxy_z`
- 피어슨 r: `0.2099`
- 상단 대 하단 사분위수 간격: `0.5379`

해석:

- 풀링된 연결은 컨텍스트에 따라 향상됩니다.
- 대부분의 개선은 RI 상호 작용 용어가 아닌 컨텍스트 프록시에서 비롯됩니다.

하위 그룹 힌트:

- 승객 상호작용 모델 조정 R^2: `0.2117`
- 시대 `2015-2017` 상호작용 모델 조정 R^2: `0.2536`

### 10.4 도메인 결과 연계 검토

원천:

- `reviews/03_analysis/07_domain_outcome_linkage_review.md`

도메인 결과:

- 구조/침입:
  - RI 전용 조정 R^2: `0.0013`
  - 프록시 모델 조정 R^2: `0.0379`
  - 가장 강한 신호: `seat_response_proxy_z`
- lower-extremity:
  - RI 전용 조정 R^2: `0.0017`
  - 프록시 모델 조정 R^2: `0.0877`
  - 가장 강한 신호: `seat_response_proxy_z`
- 구속/운동학:
  - RI 전용 조정 R^2: `0.0003`
  - 프록시 모델 조정 R^2: `0.0111`
  - 약하고 현재 의사결정을 내리지 못하고 있음
- head-neck-chest:
  - RI 전용 조정 R^2: `-0.0024`
  - 프록시 모델 조정 R^2: `0.0194`
  - 가장 강한 신호: `harshness_proxy_z`

중요한 하위군 발견:

- 승객 lower-extremity 상호작용 모델 조정 R^2: `0.3720`
- 시대 `2015-2017` lower-extremity 상호작용 모델 조정 R^2: `0.4000`

해석:

- 가장 강력한 현재 도메인은 lower-extremity입니다.
- 현재 하위 그룹 이득은 일반적인 redirection 효과가 아닌 lower-extremity에 집중되어 있습니다.

## 11. 현재의 분석적 해석

현재 가장 좋은 해석은 다음과 같습니다.

- `RI`를 유지해야 합니다.
- `RI`는 선두 설명축에서 강등되어야 합니다.
- `x/y/z` 가속은 물리적 읽기 계층의 중심에 있어야 합니다.
- `seat-response` 및 `harshness`는 현재 더 강력한 실제 설명자입니다.
- 다음 명명 검토는 바이너리가 아닌 multiaxis여야 합니다.

이는 프로젝트가 다음과 같이 더 잘 설명됨을 의미합니다.

- `x/y/z` barrier-relative 운동학, `harshness` 및 `occupant-compartment response`가 결과와 어떻게 결합되는지에 대한 연구

더 이상 다음과 같이 가장 잘 설명되지 않습니다.

- 단일 풀링된 `redirection-dominant` 운영 표준을 증명하는 프로젝트

## 12. 전류 차단제

### 12.1 운영 창이 여전히 로그오프되지 않음

- `100 ms`는 역사적인 `0-150 ms`보다 약간 더 강력합니다.
- 사례 수준의 근거는 여전히 필요합니다

### 12.2 모드 분류가 여전히 취약함

- 선택된 구조 `392 / 6`
- 마이너 클러스터는 측면 및 시대 집중으로 인해 혼란스러워집니다.

### 12.3 연결이 더 좋지만 아직 승인 등급은 아닙니다.

- 풀링된 RI 전용 연결이 약함
- 프록시 인식 연결은 약간만 더 좋습니다.
- 도메인 인식 연결은 더 많은 정보를 제공하지만 최종 인과 관계 이름 지정에는 아직 충분하지 않습니다.

### 12.4 명명 프레임이 더 이상 안정적이지 않습니다.

현재의 증거는 다음과 같은 간단한 주장에 반대합니다.

- `redirection-dominant`
- `mixed`
- `crush-dominant`

최종 운영 분류.

다음 단계에서는 다음과 같이 보다 보수적인 작업 이름을 고려해야 합니다.

- `harsh-pulse dominant`
- `seat-response dominant`
- `kinematics-shifted`
- `mixed / unresolved`

## 13. 테스트 및 검증 상태

현재 연기 테스트:

- `tests/slide_away/test_common.py`
- `tests/slide_away/test_extended_linkage.py`
- `tests/slide_away/test_domain_outcome_linkage.py`

현재 연기 결과:

- `7` 테스트 통과

다루는 내용:

- 제조사/모델 정규화
- 승객 표시 뒤집기 논리
- RI 분모 가드
- 강력한 Z-점수 도우미
- 선형 맞춤 도우미
- 행별 평균 도우미
- 행별 최대 도우미

아직 누락된 사항:

- 완전한 기능을 갖춘 마트 생성을 위한 회귀 방지
- 결과 조인에 대한 회귀 보호
- window sweep 선택 동작에 대한 회귀 보호
- casebook 선택 논리에 대한 회귀 보호

## 14. 추천 다음 심층 분석

이는 현재 상태에서 가장 높은 값의 시퀀스입니다.

1. `x/y/z` 서명 변경 사항을 첫 번째 읽기로 사용하여 사전 등록된 대표 사례 검토로 `100 ms` 운영 창을 검증합니다.
2. 더 강력한 분류법을 주장하기 전에 `6` 케이스 마이너 클러스터의 전체 수동 읽기를 완료하세요.
3. 더 엄격한 하위 그룹 규칙에 따라 `passenger` 및 `2015-2017` lower-extremity가 복제를 얻는지 테스트합니다.
4. 측면, 시대, 제조사 모델 제품군 및 가중치/클래스 프록시에 대해 confounding 검사를 실행합니다.
5. 풀링된 안전 심각도가 승인 로직에 사용되는 도메인 점수와 함께 최상위 요약으로만 유지되어야 하는지 여부를 결정합니다.
6. redirection-versus-crush 대신 multiaxis 컨텍스트 주변의 작업 모드 이름을 재설계합니다.
7. `hold`를 떠나려고 시도하기 전에 더 강력한 회귀 테스트를 추가하세요.

## 15. 다음 분석가를 위한 제안된 질문

이를 명시적인 후속 질문으로 사용하세요.

### 창문

- `100 ms`는 역사적인 `0-150 ms` 교체를 정당화할 만큼 대표적인 사례 해석을 변경합니까?
- `100 ms`와 `150 ms` 사이에서 가장 큰 RI 및 seat-response 변경을 보여주는 사례는 무엇입니까?

### 결합

- lower-extremity가 실제 기본 신호입니까, 아니면 프록시 정의 아티팩트입니까?
- 승객 및 `2015-2017` 하위 그룹 이익은 보다 엄격한 사전 등록 평가를 통과할 수 있습니까?
- 승인 로직의 통합 안전 점수를 대체해야 하는 도메인 상호 작용이 있습니까?

### 우리

- 작업 명명 시스템을 결과 중심 레이블에서 관찰 중심 레이블로 변경해야 합니까?
- 물리적 의미를 압도하지 않는 최소한의 방어 가능한 분류법은 무엇입니까?

### Confounding

- `6` 케이스 마이너 클러스터는 실제 기계 하위 그룹입니까, 아니면 단지 측면/시대/메이크 모델 포켓입니까?
- lower-extremity 이득 중 실제로 가족 또는 시대 계층화는 얼마나 됩니까?

## 16. 결론

이제 저장소는 심층적인 후속 분석을 지원합니다.
패키지는 실제적이고 재현 가능하며 검토 가능합니다.

그러나 현재의 증거는 여전히 다음과 같이 말합니다.

- 최종 운영 표준을 승인하지 않음
- 최종적으로 유리한/불호적인 redirection 주장을 승인하지 않습니다.
- 최종 분류를 단순한 redirection-versus-crush 프레임에 고정하지 마십시오.

가장 방어 가능한 현재 상태는 다음과 같습니다.

- `validated research package with unresolved mode standardization`
