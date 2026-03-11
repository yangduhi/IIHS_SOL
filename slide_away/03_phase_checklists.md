# Slide Away Phase Checklists

## Usage Rule

각 phase는 아래 checklist를 통과해야만 다음 단계로 진행한다.
체크 결과는 `slide_away/reviews` 아래에 날짜와 함께 저장한다.

## Phase 0. Standard Freeze

### Entry checklist

- `slide_away` 폴더가 생성되어 있다.
- core document 4종이 모두 존재한다.
- primary cohort, window, signal mode가 문서에 명시되어 있다.

### Exit checklist

- `driver-only baseline`이 공식 baseline으로 적혀 있다.
- `a_y_away` sign rule이 명시되어 있다.
- mart 이름과 출력 경로가 문서에 적혀 있다.
- 표준 스크립트 인터페이스와 실제 구현 또는 wrapper 매핑이 기록되었다.
- 현재 승인 상태와 closure item이 review 메모에 남아 있다.

## Phase 1. Case Master

### Entry checklist

- `research.sqlite`가 읽힌다.
- `canonical_small_overlap_tests.csv`가 존재한다.
- `standard_baseline` availability를 판정할 수 있는 `preprocessing_cases` 또는 manifest 근거가 확인되었다.
- source row count가 현재 기준선과 크게 어긋나지 않는다.

### Execution checklist

- `filegroup_id`가 유일한지 확인했다.
- `test_side`와 `era`를 생성했다.
- `signal_ready_flag`를 생성했다.
- `signal_ready_flag` 산정 기준을 쿼리 또는 manifest 규칙으로 문서화했다.
- `make_model_family` 규칙을 정의했다.
- `analysis_cohort`를 생성했다.

### Exit checklist

- `case_master.parquet`가 생성되었다.
- `driver=361`, `passenger=52`, `signal-ready=406`이 재현된다.
- 누락 및 충돌 요약표가 존재한다.

## Phase 2. Outcome Mart

### Entry checklist

- `case_master.parquet`가 존재한다.
- `pdf_result_tables`, `pdf_result_rows` 접근이 가능하다.
- table type coverage를 확인했다.

### Execution checklist

- `intrusion`을 별도 group으로 추출했다.
- `restraint_kinematics`를 별도 group으로 추출했다.
- `leg_foot_injury`를 별도 group으로 추출했다.
- `head`, `neck`, `chest`, `thigh_hip` injury를 추출했다.
- row-level provenance를 저장했다.
- `outcome_quality_score`를 계산했다.

### Exit checklist

- `outcomes_v1.parquet`가 생성되었다.
- coverage summary가 존재한다.
- canonical label review가 기록되었다.

## Phase 3. Feature Mart

### Entry checklist

- `standard_baseline` 신호 접근이 가능하다.
- side harmonization 규칙이 고정되어 있다.
- outcome mart 없이도 feature mart 독립 생성이 가능하다.

### Execution checklist

- `a_y_away` 변환을 적용했다.
- `DeltaVx`, `DeltaVy_away`, `RI`를 계산했다.
- seat twist를 계산했다.
- foot resultant와 asymmetry를 계산했다.
- multi-window feature를 생성했다.
- `strict_origin` sensitivity set을 별도로 생성했다.

### Exit checklist

- `features_v1.parquet`가 생성되었다.
- `features_v1_strict_origin.parquet`가 생성되었다.
- feature missingness summary가 존재한다.
- 표본 case sign audit가 기록되었다.

## Phase 4. Window Sweep

### Entry checklist

- feature mart가 생성되어 있다.
- 주요 outcome mart가 생성되어 있다.
- primary와 robustness window 후보가 정의되어 있다.

### Execution checklist

- `20/40/60/80/100/120/150/250 ms`를 모두 비교했다.
- clustering quality를 기록했다.
- outcome separation 지표를 기록했다.
- selected window와 rejected window의 이유를 적었다.

### Exit checklist

- `window_sweep_summary.csv`가 존재한다.
- operating primary window가 공식 지정되었다.
- robustness window가 공식 지정되었다.

## Phase 5. Mode Study

### Entry checklist

- selected window가 확정되었다.
- representative feature set이 지정되었다.

### Execution checklist

- `2/3/4 cluster` 후보를 비교했다.
- cluster size imbalance를 기록했다.
- representative case를 추출했다.
- 30-50건 수동 리뷰를 수행했다.
- provisional mode naming을 적용했다.
- named mode를 outcome linkage 전까지 `label hypothesis`로 유지했다.

### Exit checklist

- `mode_study_summary.csv`가 존재한다.
- `mode_representative_cases.csv`가 존재한다.
- 수동 리뷰 메모가 존재한다.

## Phase 6. Outcome Linkage

### Entry checklist

- feature mart와 outcome mart가 조인된다.
- mode candidate가 정의되어 있다.

### Execution checklist

- continuous `RI` 분석을 수행했다.
- discrete mode 분석을 수행했다.
- side, era, family control을 수행했다.
- `RI vs safety` 2D map을 생성했다.
- 단순 방향 해석과 반례를 함께 기록했다.

### Exit checklist

- `ri_vs_safety_map.csv`가 존재한다.
- `ri_vs_safety_map.png`가 존재한다.
- phase plot이 존재한다.

## Phase 7. Casebook

### Entry checklist

- representative cases가 정리되어 있다.
- same model family pair를 조회할 수 있다.

### Execution checklist

- good, bad, ambiguous 사례를 분리했다.
- redesign 또는 facelift 전후 사례를 묶었다.
- structure strategy codebook을 작성했다.
- 사례별 signal and outcome interpretation을 적었다.

### Exit checklist

- `matched_pair_casebook.md`가 존재한다.
- `structure_strategy_codebook.csv`가 존재한다.
- 최소 12건 사례가 포함되었다.

## Phase 8. Final Synthesis

### Entry checklist

- 모든 주요 mart와 figure가 생성되었다.
- 대표 사례 review가 완료되었다.

### Execution checklist

- 연구 질문별 결론을 정리했다.
- favorable and unfavorable redirection 조건을 정리했다.
- 제한점과 confounding을 정리했다.
- 다음 단계 제안을 작성했다.

### Exit checklist

- `final_study_brief.md`가 존재한다.
- `final_decision_log.md`가 존재한다.
- 다른 작업자가 재현 가능한 수준으로 문서화되었다.
