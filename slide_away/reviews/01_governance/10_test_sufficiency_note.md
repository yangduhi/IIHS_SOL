# 테스트 충분성 메모

- snapshot_id: `slide_away_authoritative_2026-03-11`
- generated_at: `2026-03-11`
- authoritative_as_of: `2026-03-11`
- status: `reviewer closure draft`
- primary_db: `data/research/research.sqlite`
- current_window_candidate: `100 ms`
- historic_window_reference: `0-150 ms`

## 현재 테스트 상태

- 실행 결과: `14 tests passed`
- 명령: `python -m unittest discover -s tests/slide_away -p "test_*.py"`
- 현재 synthetic clustering 관련 `ConvergenceWarning`은 있었으나 실패는 없었습니다.

## 현재 포함 범위

- `test_common.py`
  - side harmonization
  - RI guard
  - `z` 및 resultant metric exposure
- `test_modeling.py`
  - cluster input preparation
  - low coverage row filtering
  - median imputation
- `test_window_and_linkage.py`
  - window sweep selection regression
  - linkage frame에 vertical/resultant harshness 포함 여부
- `test_extended_linkage.py`
  - z-score standardization
  - linear summary sanity check
- `test_domain_outcome_linkage.py`
  - row-wise domain aggregation
- `test_domain_score_sensitivity.py`
  - domain scenario 구성
  - lower-ext variant slicing

## 현재 평가

- 연구 패키지 수준의 regression protection은 `sufficient for reviewer-stage package`
- final operating standard 수준으로는 `not yet sufficient`

## 왜 아직 충분하지 않은가

1. 핵심 pipeline 출력의 snapshot regression이 아직 부족합니다.
2. `build_case_master`, `build_outcome_mart`, `build_barrier_relative_features`의 selected-case numeric regression이 아직 없습니다.
3. `run_window_sweep` 결과를 아티팩트 수준에서 고정하는 regression이 더 필요합니다.
4. 실제 parquet/join output이 바뀌었을 때 바로 감지하는 test wall이 아직 얇습니다.

## reviewer 권고

- 현재 `14`개 테스트는 연구 패키지 검토 단계에서는 승인 가능 범위입니다.
- 다만 final operating approval을 해제하려면 아래를 추가하는 편이 좋습니다.
  1. `build_case_master` snapshot regression
  2. `build_outcome_mart` join regression
  3. `build_barrier_relative_features` selected-case numeric regression
  4. `run_window_sweep` selected window regression

## 현재 결론

- `test sufficiency for research package`: `accepted`
- `test sufficiency for final operating standard`: `not accepted`
