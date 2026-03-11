# Slide Away Master Execution Plan

## 1. Purpose

이 문서는 `slide_away` 연구를 실제 작업 단위로 실행하기 위한 단계별 실행안이다.
각 phase는 목적, 입력, 작업, 산출물, 검증, 완료 조건을 갖는다.

## 2. Execution Principle

- 선행 phase의 산출물이 검증되기 전에는 다음 phase로 넘어가지 않는다.
- 모든 단계는 `filegroup_id` 기준으로 provenance를 유지한다.
- 모든 주요 테이블은 `parquet`와 `csv summary`를 함께 남긴다.
- 표준 결론은 `driver-only baseline`에서 먼저 만든다.
- `passenger-side`는 baseline 재현 후 확장한다.

## 3. Standard Output Layout

이 실행안에서 권장하는 출력 구조는 아래와 같다.

- `slide_away/artifacts/marts`
- `slide_away/artifacts/figures`
- `slide_away/artifacts/tables`
- `slide_away/artifacts/logs`
- `slide_away/reviews`

## 4. Required Standard Scripts

아래 스크립트 이름은 본 연구의 표준 인터페이스로 사용한다.
현재 저장소가 동일 기능의 하위 모듈만 갖고 있다면, 아래 이름으로 thin wrapper를 추가하거나
동등한 실행 매핑을 `Phase 0 sign-off`에 기록해야 한다.
wrapper 또는 매핑이 닫히기 전에는 본 실행안이 `execution-ready`로 간주되지 않는다.

- `scripts/build_case_master.py`
- `scripts/build_outcome_mart.py`
- `scripts/build_barrier_relative_features.py`
- `scripts/run_window_sweep.py`
- `scripts/run_mode_study.py`
- `scripts/build_mode_casebook.py`
- `scripts/build_ri_safety_map.py`

## 5. Phase Overview

| Phase | Name | Main Goal | Primary Output |
| --- | --- | --- | --- |
| 0 | Standard Freeze | 표준과 산출물 구조 고정 | standard sign-off |
| 1 | Case Master | cohort 기준 테이블 구축 | `case_master.parquet` |
| 2 | Outcome Mart | PDF 중심 outcome mart 구축 | `outcomes_v1.parquet` |
| 3 | Feature Mart | barrier-relative feature mart 구축 | `features_v1.parquet` |
| 4 | Window Sweep | 시간창 민감도 검증 | `window_sweep_summary.csv` |
| 5 | Mode Study | 2, 3, 4 mode 후보 비교 | `mode_study_summary.csv` |
| 6 | Outcome Linkage | mode와 safety 결과 연결 | `ri_vs_safety_map.*` |
| 7 | Casebook | 대표 사례 및 matched-pair 정리 | `matched_pair_casebook.md` |
| 8 | Final Synthesis | 결론, 제한점, 다음 단계 정리 | `final_study_brief.md` |

## 6. Detailed Phase Plan

### Phase 0. Standard Freeze

목적:

- 본 폴더 문서를 기준 표준으로 고정한다.
- 경로, mart 이름, 좌표계, cohort 규칙을 확정한다.

입력:

- `slide_away/README.md`
- `slide_away/01_work_instruction.md`
- `slide_away/02_execution_plan.md`
- `slide_away/03_phase_checklists.md`

작업:

1. 연구 명칭과 기본 질문을 확정한다.
2. primary cohort를 `driver-only baseline`으로 명시한다.
3. `a_y_away` 부호 규칙을 확정한다.
4. primary window를 `0-150 ms`로 고정한다.
5. 표준 스크립트 이름과 산출 경로를 고정한다.
6. 표준 스크립트 이름과 실제 구현 모듈의 매핑 또는 wrapper 구현을 확정한다.

산출물:

- 표준 문서 4종
- phase sign-off 메모
- script interface map 또는 wrapper 구현 기록

완료 조건:

- 이후 작업자가 해석 기준을 바꾸지 않고 실행 가능해야 한다.

### Phase 1. Case Master

목적:

- 모든 후속 조인의 기준이 되는 case-level master mart를 만든다.

입력:

- `data/research/research.sqlite`
- `output/small_overlap/tables/canonical_small_overlap_tests.csv`
- `output/small_overlap/tables/analysis_cohort_counts.csv`
- `data/derived/small_overlap/preprocessed_signals`
- `docs/signals/preprocessing_db_design.md`

작업:

1. `filegroup_id` 기준으로 기본 case inventory를 수집한다.
2. `vehicle_year`, `vehicle_make_model`, `test_side`, `era`, `detail_url`를 정리한다.
3. PDF, workbook, signal container coverage를 병합한다.
4. `signal_ready_flag`를 `standard_baseline` preprocessing availability 또는 동등 manifest 근거로 생성한다.
5. `analysis_cohort`를 생성한다.
6. `make_model_family` 규칙을 정의한다.
7. `driver-only baseline`, `all-signal-ready`, `passenger-extension` cohort를 분리한다.

권장 구현:

```powershell
python scripts/build_case_master.py `
  --db data/research/research.sqlite `
  --canonical output/small_overlap/tables/canonical_small_overlap_tests.csv `
  --out slide_away/artifacts/marts/case_master.parquet `
  --summary slide_away/artifacts/tables/case_master_summary.csv
```

필수 산출물:

- `slide_away/artifacts/marts/case_master.parquet`
- `slide_away/artifacts/tables/case_master_summary.csv`
- `slide_away/artifacts/logs/case_master_build.log`

QA:

- 중복 `filegroup_id`가 없어야 한다.
- side, era, signal coverage 누락률을 표로 확인한다.
- `signal_ready_flag`의 산정 근거와 쿼리 또는 manifest 기준을 로그에 남긴다.
- `driver=361`, `passenger=52`, `signal-ready=406`를 재현해야 한다.

완료 조건:

- 후속 outcome/feature 조인이 `case_master` 하나로 가능해야 한다.

### Phase 2. Outcome Mart

목적:

- PDF 중심의 case-level safety outcome mart를 만든다.

입력:

- `data/research/research.sqlite`
- `case_master.parquet`

작업:

1. `pdf_result_tables`에서 table type coverage를 다시 확인한다.
2. `intrusion`, `restraint_kinematics`, `leg_foot_injury`, injury table을 추출한다.
3. row-level label을 canonical label로 정규화한다.
4. case-level 집계 규칙을 정의한다.
5. 수치값과 row provenance를 함께 저장한다.
6. `outcome_quality_score`를 계산한다.
7. `outcomes_v1.parquet`를 생성한다.

권장 구현:

```powershell
python scripts/build_outcome_mart.py `
  --db data/research/research.sqlite `
  --case-master slide_away/artifacts/marts/case_master.parquet `
  --out slide_away/artifacts/marts/outcomes_v1.parquet `
  --summary slide_away/artifacts/tables/outcomes_v1_summary.csv `
  --coverage slide_away/artifacts/tables/outcomes_v1_coverage.csv
```

필수 산출물:

- `slide_away/artifacts/marts/outcomes_v1.parquet`
- `slide_away/artifacts/tables/outcomes_v1_summary.csv`
- `slide_away/artifacts/tables/outcomes_v1_coverage.csv`
- `slide_away/artifacts/logs/outcome_mart_build.log`

QA:

- table family별 coverage가 기록되어야 한다.
- `not available`, `missing`, `not extracted`를 구분해야 한다.
- 대표 라벨 20개를 육안 검토해 정규화 오류가 없는지 확인한다.

완료 조건:

- case-level outcome와 provenance를 동시에 조회할 수 있어야 한다.

### Phase 3. Feature Mart

목적:

- barrier-relative kinematics와 occupant proxy를 포함한 feature mart를 만든다.

입력:

- `case_master.parquet`
- `data/derived/small_overlap/preprocessed_signals`
- `standard_baseline`
- `strict_origin`

작업:

1. `standard_baseline` 신호를 로드한다.
2. side별 `a_y_away` sign harmonization을 적용한다.
3. `DeltaVx`, `DeltaVy_away`, `LR`, `LY`, `RI`를 계산한다.
4. timing, peak, pulse duration feature를 계산한다.
5. seat twist, foot resultant, asymmetry feature를 계산한다.
6. `0-20/40/60/80/100/120/150/250 ms` 창 feature를 함께 계산한다.
7. `strict_origin` 기준 민감도 세트를 별도 생성한다.

권장 구현:

```powershell
python scripts/build_barrier_relative_features.py `
  --case-master slide_away/artifacts/marts/case_master.parquet `
  --preprocessed-root data/derived/small_overlap/preprocessed_signals `
  --mode standard_baseline `
  --out slide_away/artifacts/marts/features_v1.parquet `
  --summary slide_away/artifacts/tables/features_v1_summary.csv
```

민감도 구현:

```powershell
python scripts/build_barrier_relative_features.py `
  --case-master slide_away/artifacts/marts/case_master.parquet `
  --preprocessed-root data/derived/small_overlap/preprocessed_signals `
  --mode strict_origin `
  --out slide_away/artifacts/marts/features_v1_strict_origin.parquet `
  --summary slide_away/artifacts/tables/features_v1_strict_origin_summary.csv
```

필수 산출물:

- `slide_away/artifacts/marts/features_v1.parquet`
- `slide_away/artifacts/marts/features_v1_strict_origin.parquet`
- `slide_away/artifacts/tables/features_v1_summary.csv`
- `slide_away/artifacts/tables/features_v1_strict_origin_summary.csv`

QA:

- driver/passenger 동일 물리 거동이 동일 sign으로 표현되는지 샘플 검증한다.
- `DeltaV` 적분 방향이 feature 정의와 일치하는지 10건 이상 확인한다.
- feature missingness profile을 남긴다.

완료 조건:

- mode study에 바로 투입할 수 있는 feature mart가 생성된다.

### Phase 4. Window Sweep

목적:

- 어떤 초기 시간창이 mode separation과 outcome separation에 가장 유리한지 검증한다.

입력:

- `features_v1.parquet`
- `outcomes_v1.parquet`

작업:

1. 각 window에 대해 clustering quality를 계산한다.
2. 각 window에 대해 outcome separation effect를 비교한다.
3. `0-150 ms`와 `0-250 ms`를 반드시 비교한다.
4. phase plot과 summary table을 생성한다.

권장 구현:

```powershell
python scripts/run_window_sweep.py `
  --features slide_away/artifacts/marts/features_v1.parquet `
  --outcomes slide_away/artifacts/marts/outcomes_v1.parquet `
  --out slide_away/artifacts/tables/window_sweep_summary.csv `
  --fig slide_away/artifacts/figures/window_sweep_comparison.png
```

필수 산출물:

- `slide_away/artifacts/tables/window_sweep_summary.csv`
- `slide_away/artifacts/figures/window_sweep_comparison.png`

QA:

- 성능 기준이 clustering metric 하나에만 의존하지 않는지 확인한다.
- selected window와 rejected window의 이유를 문서화한다.
- `0-150 ms`는 operating baseline window로만 선언하고, 최종 정책 여부는 outcome linkage 이후 다시 확인한다.

완료 조건:

- operating primary window와 robustness window가 공식 지정된다.

### Phase 5. Mode Study

목적:

- 2, 3, 4 mode 후보를 비교하고 대표 사례를 선택한다.

입력:

- `features_v1.parquet`
- `window_sweep_summary.csv`

작업:

1. 2, 3, 4 cluster 후보를 비교한다.
2. cluster size imbalance를 점검한다.
3. representative case를 뽑는다.
4. 30-50건 수동 라벨링을 수행한다.
5. `redirection-dominant`, `mixed`, `crush-dominant` 해석 가능성을 검토한다.
6. mode naming은 outcome linkage 전까지 `label hypothesis`로 유지한다.

권장 구현:

```powershell
python scripts/run_mode_study.py `
  --features slide_away/artifacts/marts/features_v1.parquet `
  --window 0.15 `
  --clusters 2 3 4 `
  --out-summary slide_away/artifacts/tables/mode_study_summary.csv `
  --out-cases slide_away/artifacts/tables/mode_representative_cases.csv `
  --out-fig slide_away/artifacts/figures/mode_study_overview.png
```

필수 산출물:

- `slide_away/artifacts/tables/mode_study_summary.csv`
- `slide_away/artifacts/tables/mode_representative_cases.csv`
- `slide_away/artifacts/figures/mode_study_overview.png`
- `slide_away/reviews/03_analysis/02_manual_mode_label_review.md`

QA:

- representative case는 각 cluster에서 최소 5건 이상 확보한다.
- outlier와 cluster core를 분리해 기록한다.
- 소수 cluster를 곧바로 독립 물리 mode로 단정하지 않는다.
- final selected mode count의 이유를 명시한다.

완료 조건:

- provisional mode definition이 문서와 표로 정리된다.

### Phase 6. Outcome Linkage

목적:

- mode 또는 continuous RI와 safety outcome의 관계를 분석한다.

입력:

- `features_v1.parquet`
- `outcomes_v1.parquet`
- `mode_study_summary.csv`

작업:

1. `RI_60`와 주요 safety outcome의 관계를 계산한다.
2. continuous view와 discrete mode view를 둘 다 본다.
3. side, era, make/model family를 통제한 분석을 수행한다.
4. `RI vs safety` 2D map을 작성한다.
5. favorable and unfavorable redirection을 나누는 조건을 기술한다.

권장 구현:

```powershell
python scripts/build_ri_safety_map.py `
  --features slide_away/artifacts/marts/features_v1.parquet `
  --outcomes slide_away/artifacts/marts/outcomes_v1.parquet `
  --out-table slide_away/artifacts/tables/ri_vs_safety_map.csv `
  --out-fig slide_away/artifacts/figures/ri_vs_safety_map.png
```

필수 산출물:

- `slide_away/artifacts/tables/ri_vs_safety_map.csv`
- `slide_away/artifacts/figures/ri_vs_safety_map.png`
- `slide_away/artifacts/figures/delta_vx_delta_vy_phase_plot.png`

QA:

- `high RI = always good` 같은 단순 결론을 금지한다.
- intrusion과 restraint mismatch를 분리해서 본다.
- 결론마다 confounding 가능성을 적는다.

완료 조건:

- mode x outcome 2차원 해석이 가능해야 한다.

### Phase 7. Casebook

목적:

- 대표 사례와 동일 모델 전후 사례를 메커니즘 관점에서 묶는다.

입력:

- `mode_representative_cases.csv`
- `case_master.parquet`
- `outcomes_v1.parquet`
- 대표 사례의 PDF 및 signal plots

작업:

1. representative case를 good, bad, ambiguous로 나눈다.
2. 동일 모델 전후 redesign 사례를 묶는다.
3. 구조 전략 codebook을 작성한다.
4. 사례별 가설을 남긴다.

구조 전략 codebook 필수 항목:

- `occupant compartment reinforcement`
- `barrier engagement structure`
- `additional load path`
- `wheel-motion modification`
- `restraint modification`

권장 구현:

```powershell
python scripts/build_mode_casebook.py `
  --case-master slide_away/artifacts/marts/case_master.parquet `
  --features slide_away/artifacts/marts/features_v1.parquet `
  --outcomes slide_away/artifacts/marts/outcomes_v1.parquet `
  --out slide_away/reviews/04_casebooks/01_matched_pair_casebook.md
```

필수 산출물:

- `slide_away/reviews/04_casebooks/01_matched_pair_casebook.md`
- `slide_away/reviews/04_casebooks/02_structure_strategy_codebook.csv`

QA:

- 최소 12건 이상의 사례를 포함한다.
- 같은 model family의 전후 비교 사례를 우선한다.
- 사례마다 signal view와 outcome view를 동시에 적는다.

완료 조건:

- 메커니즘 해석이 narrative 형태로 정리된다.

### Phase 8. Final Synthesis

목적:

- 연구 결론, 제한점, 다음 단계 제안을 표준 형태로 정리한다.

입력:

- 모든 phase 산출물

작업:

1. 연구 질문별 답을 정리한다.
2. final mode framing을 정리한다.
3. favorable and unfavorable redirection 조건을 요약한다.
4. 제한점과 리스크를 적는다.
5. 차기 CAE 또는 실차 검증 제안을 적는다.

필수 산출물:

- `slide_away/final_study_brief.md`
- `slide_away/final_decision_log.md`

완료 조건:

- 다음 작업자가 전체 흐름을 재시작 없이 이어받을 수 있어야 한다.

## 7. MVP Path

4주 MVP는 아래 범위로 제한한다.

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5의 대표 사례 라벨링 초안
6. Phase 6의 `RI vs safety` 초안

MVP 종료 기준:

- `2-mode vs 3-mode`의 1차 판단이 가능하다.
- `redirection`이 leg and foot, seat proxy, restraint proxy와 어떤 방향으로 연결되는지 초안이 나온다.

## 8. Full Study Path

12주 Full Study는 아래 cadence를 따른다.

- Week 1-2: Phase 1
- Week 3-4: Phase 2
- Week 5-6: Phase 3
- Week 7: Phase 4
- Week 8: Phase 5
- Week 9-10: Phase 6
- Week 11: Phase 7
- Week 12: Phase 8

## 9. Hard Rules

- unresolved join issue가 남아 있으면 modeling 금지
- outcome canonicalization이 끝나지 않으면 safety map 작성 금지
- side harmonization 검증 전 pooled feature 생성 금지
- make/model family grouped split 없이 prediction reporting 금지
- passenger-side를 baseline conclusion으로 사용 금지
