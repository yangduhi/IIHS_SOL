# 슬라이드 어웨이 작업 지침

## 1. 문서 현황

- 문서 이름: `slide_away` 작업 지침
- 상태: `active standard`
- 발효일: `2026-03-11`
- 적용 대상: `slide_away` 연구에 따라 수행된 모든 분석, ETL, 모델링 및 사례 연구 작업

## 2. 프로젝트 정의

### 2.1 공식 연구 제목

`IIHS Small Overlap Front 시험에서 barrier-relative vehicle kinematics와 safety outcome의 연관성 및 설계 인자 분석`

### 2.2 작업 명칭

`slide_away`

### 2.3 핵심 질문

IIHS small overlap front 시험에서 초기 barrier-relative kinematics가 어떤 형태로 나타나는지, 그 거동이 구조, lower leg and foot, restraint and kinematics, intrusion 결과와 어떻게 연결되는지를 규명한다.

## 3. 연구직위

### 3.1 이 연구는 무엇인가

- `slide_away`라는 감각적 표현을 `barrier-relative kinematics`로 물리적으로 재정의하는 연구다.
- `redirection-dominant`, `mixed`, `crush-dominant`를 포함할 수 있는 연속체 기반 연구다.
- `mode`와 `safety outcome`을 함께 해석하는 2차원 연구다.
- 초기 주제는 `occupant-compartment pulse`와 `compartment-level response`다.

### 3.2 이 연구가 아닌 것

- 단순한 `2개 타입 고정 분류` 연구가 아니다.
- 전체 차량의 정확한 총 에너지 분배를 직접 계산하는 연구가 아니다.
- side, year, era, class를 무시한 pooled correlation 연구가 아니다.
- rating 자체를 단일 숫자로 압축해 끝내는 연구가 아니다.

## 4. 필수 연구 가정

### 4.1 분석단위

- 기본 분석 단위는 `filegroup_id`다.
- 하나의 case는 하나의 `filegroup_id`에 대응한다.
- 동일 모델의 전후 비교는 별도의 matched-pair 레이어에서 수행한다.

### 4.2 기본 데이터 도메인

- 카탈로그 및 결과 정보 소스:
  - `data/research/research.sqlite`
- 코호트 및 메타데이터 제어:
  - `output/small_overlap/tables/canonical_small_overlap_tests.csv`
- 진실의 신호 소스:
  - `data/derived/small_overlap/preprocessed_signals`
- 전처리 정책 소스:
  - `docs/signals/preprocessing_db_design.md`

### 4.3 정규 신호 모드

- 기본 모드: `standard_baseline`
- 감도 모드: `strict_origin`
- `exploratory_t0`는 본 연구의 표준 결론 산출 모드가 아니다.
- `standard_baseline_full_tdms`는 coverage extension 또는 보조 분석용이다.

### 4.4 코호트 정책

- 원시 카탈로그 모집단: `413`
- 신호 준비 인구: `406`
- 첫 번째 기준 코호트: `driver-side 361`
- Passenger-side cohort는 phase 6 이후 확장 분석으로 다룬다.

### 4.5 통제 정책

아래 변수는 통제 없이 해석하지 않는다.

- `side`
- `era`
- `vehicle year`
- `make/model family`
- 가능하면 `weight/class`

### 4.6 학습 및 검증 분할 정책

- random split 금지
- `make/model family` 기준 grouped split 사용
- 동일 모델의 facelift, redesign, 동일 nameplate가 서로 다른 split에 섞이지 않도록 관리

## 5. 물리 및 좌표 표준

### 5.1 Barrier-relative 측면 표시

Driver와 passenger를 하나의 해석 프레임으로 묶기 위해 아래를 강제한다.

- Driver-side:
  - `a_y_away = +a_y`
- Passenger-side:
  - `a_y_away = -a_y`

이 변환 전의 raw lateral sign으로 pooled feature를 만들지 않는다.

### 5.2 필수 운동학적 변수

다음 파생량은 표준 feature set에 반드시 포함한다.

- `DeltaVx(T) = integral[a_x(t) dt, 0..T]`
- `DeltaVy_away(T) = integral[a_y_away(t) dt, 0..T]`
- `LR_60 = abs(DeltaVx(60 ms)) / V0`
- `LR_100 = abs(DeltaVx(100 ms)) / V0`
- `LY_40 = abs(DeltaVy_away(40 ms)) / V0`
- `LY_60 = abs(DeltaVy_away(60 ms)) / V0`
- `RI_60 = abs(DeltaVy_away(60 ms)) / (abs(DeltaVx(60 ms)) + eps)`
- `t_peak_y`
- `t_50_DeltaVx`
- `max_abs_ax`
- `max_abs_ay`
- `pulse_duration_x`
- `pulse_duration_y`

### 5.3 점유자 응답 프록시 변수

다음 feature는 1차 연구의 필수 occupant-response proxy다.

- `seat_twist_peak = max abs(seat_inner_deflection - seat_mid_deflection)`
- `foot_resultant_left`
- `foot_resultant_right`
- `foot_resultant_asymmetry`
- `foot_x_left_right_diff`
- `foot_z_left_right_diff`
- 차량 펄스-발/좌석 지연 기능

### 5.4 창구 정책

- 기본 운영 기준 기간: `0-150 ms`
- 표준 비교 창:
  - `20 ms`
  - `40 ms`
  - `60 ms`
  - `80 ms`
  - `100 ms`
  - `120 ms`
  - `150 ms`
- 견고성 창: `0-250 ms`

`0-150 ms`는 현 시점의 운영 baseline window다.
최종 정책은 Phase 4의 window sensitivity 검토와 Phase 6의 outcome linkage 검토를 통과한 뒤에만 확정한다.
모든 결론은 최소 `0-150 ms`와 `0-250 ms` 두 창에서 비교 검토한다.

## 6. 결과기준

### 6.1 결과 축

본 연구는 다음 outcome 축을 표준으로 사용한다.

- `structure and intrusion`
- `leg and foot exposure`
- `restraint and kinematics`
- `injury measurements`

### 6.2 결과 소스 우선순위

우선순위는 아래와 같다.

1. `pdf_result_tables` + `pdf_result_rows`
2. `extracted_metrics`
3. Excel 통합 문서 ETL
4. Web backfill 또는 수동 coding

### 6.3 필수 사례 수준 결과 그룹

`outcomes_v1`에는 아래 그룹이 반드시 있어야 한다.

- `intrusion`
- `restraint_kinematics`
- `leg_foot_injury`
- `head_injury`
- `neck_injury`
- `chest_injury`
- `thigh_hip_injury`
- `dummy_clearance`

### 6.4 결과 모델링 목표

최종 해석의 기본 틀은 아래 4사분면이다.

1. 유리한 redirection
2. 불리한 redirection
3. 성공적인 crush management
4. 실패한 crush management

## 7. 필수 데이터 마트

### 7.1 `case_master.parquet`

목적: cohort 제어와 모든 후속 조인의 기준 테이블

필수 컬럼:

- `filegroup_id`
- `vehicle_id`
- `test_code`
- `vehicle_year`
- `vehicle_make_model`
- `test_side`
- `tested_on`
- `era`
- `detail_url`
- `download_status`
- `signal_ready_flag`
- `pdf_available_flag`
- `excel_available_flag`
- `signal_container_count`
- `pdf_document_count`
- `excel_workbook_count`
- `primary_pdf_layout_family`
- `vin_conflict_flag`
- `make_model_family`
- `analysis_cohort`

### 7.2 `outcomes_v1.parquet`

목표: 사례 수준 결과표

필수 컬럼:

- `filegroup_id`
- `intrusion_max_resultant_cm`
- `intrusion_footrest_resultant_cm`
- `intrusion_left_toepan_resultant_cm`
- `intrusion_brake_pedal_resultant_cm`
- `leg_foot_index_left`
- `leg_foot_index_right`
- `foot_resultant_accel_left_g`
- `foot_resultant_accel_right_g`
- `restraint_event_count`
- `pretensioner_time_ms`
- `airbag_first_contact_time_ms`
- `airbag_full_inflation_time_ms`
- `head_hic15`
- `chest_rib_compression_mm`
- `chest_viscous_criteria_ms`
- `neck_tension_extension_nij`
- `thigh_hip_risk_proxy`
- `outcome_quality_score`
- `outcome_source_version`

필수 추가 규칙:

- 각 수치는 raw row provenance를 잃지 않도록 row locator를 별도 보존한다.
- 결측과 `not available`를 구분한다.
- 좌우 값은 가급적 분리 저장하고, 별도 파생 컬럼에서만 요약한다.

### 7.3 `features_v1.parquet`

목적: barrier-relative feature mart

필수 컬럼:

- `filegroup_id`
- `source_mode`
- `window_s`
- `v0_mps`
- `delta_vx_mps`
- `delta_vy_away_mps`
- `lr`
- `ly`
- `ri`
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
- `cluster_input_flag`
- `feature_quality_score`
- `feature_version`

## 8. 모드 정의 정책

### 8.1 초기 모드 언어

초기 해석 언어는 아래 세 범주를 사용한다.

- `redirection-dominant`
- `mixed`
- `crush-dominant`

### 8.2 최종 모드 개수 선언 규칙

최종 mode 개수는 아래 조건을 모두 보고 결정한다.

- 클러스터링 측정항목
- 클러스터 크기 안정성
- 대표적인 사례 해석성
- 결과 분리 유틸리티
- 측면과 시대의 견고성

단지 silhouette 하나만으로 최종 결론을 선언하지 않는다.

### 8.3 현재 잠정 기준선

현재 기준에서는 `0-150 ms`, `standard_baseline`, `v3_window015`에서 `3-cluster` 후보가 가장 유망하다.
다만 이는 `provisional baseline`이며, outcome 연결 검증 전까지 확정 결론이 아니다.
군집 불균형, confounding, representative case 해석 검토 전까지는 안정적 물리 mode가 아니라 `baseline candidate` 또는 `label hypothesis`로 다룬다.

## 9. 필수 결과물

본 연구에서 최종적으로 반드시 남겨야 하는 산출물은 아래와 같다.

- `case_master.parquet`
- `outcomes_v1.parquet`
- `features_v1.parquet`
- `mode_study_summary.csv`
- `mode_representative_cases.csv`
- `ri_vs_safety_map.csv`
- `ri_vs_safety_map.png`
- `delta_vx_delta_vy_phase_plot.png`
- `matched_pair_casebook.md`
- `final_study_brief.md`
- `final_decision_log.md`

## 10. 업무규칙

아래 규칙은 필수다.

- raw signal이나 source document를 직접 덮어쓰지 않는다.
- 파생 테이블은 항상 version suffix를 둔다.
- feature engineering 전에 side harmonization을 먼저 수행한다.
- outcome ETL 전에 table family coverage를 먼저 점검한다.
- random threshold를 미리 고정하지 않는다.
- `driver-only baseline` 검증 전 passenger 통합 모델을 최종 결론으로 사용하지 않는다.
- 동일 모델 전후 비교는 case study 레이어로 분리한다.
- 구조 설계 인자 coding은 전수 자동화 대상으로 가정하지 않는다.

## 11. 완료의 정의

아래 조건을 만족해야 본 연구의 1차 분석 완료로 본다.

- `case_master`, `outcomes_v1`, `features_v1`가 모두 생성된다.
- `driver-only baseline`에서 2개 또는 3개 mode 후보가 재현된다.
- primary window와 robustness window 결과가 비교 표로 정리된다.
- `RI vs safety` 2D map이 생성된다.
- representative case 검토 결과가 문서화된다.
- confounding risk와 open issue가 명시된다.

## 12. 정지 조건

아래 상황에서는 다음 phase로 진행하지 않는다.

- barrier-relative sign harmonization 검증이 끝나지 않은 경우
- `case_master` 조인 충돌이 남아 있는 경우
- outcome 품질 점검 없이 모델링으로 넘어가려는 경우
- make/model family split 규칙이 없는 경우
- driver와 passenger를 부호 조정 없이 합치려는 경우
