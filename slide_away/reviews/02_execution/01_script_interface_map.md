# 슬라이드 어웨이 스크립트 인터페이스 맵

- 날짜: `2026-03-11`
- 상태: `closed`

## 표준 인터페이스

| 예정된 스크립트 | 래퍼 경로 | 실행 모듈 | 단계 |
| --- | --- | --- | --- |
| `build_case_master.py` | `scripts/build_case_master.py` | `scripts/tools/slide_away/build_case_master.py` | 1 |
| `build_outcome_mart.py` | `scripts/build_outcome_mart.py` | `scripts/tools/slide_away/build_outcome_mart.py` | 2 |
| `build_barrier_relative_features.py` | `scripts/build_barrier_relative_features.py` | `scripts/tools/slide_away/build_barrier_relative_features.py` | 3 |
| `run_window_sweep.py` | `scripts/run_window_sweep.py` | `scripts/tools/slide_away/run_window_sweep.py` | 4 |
| `run_mode_study.py` | `scripts/run_mode_study.py` | `scripts/tools/slide_away/run_mode_study.py` | 5 |
| `build_ri_safety_map.py` | `scripts/build_ri_safety_map.py` | `scripts/tools/slide_away/build_ri_safety_map.py` | 6 |
| `build_mode_casebook.py` | `scripts/build_mode_casebook.py` | `scripts/tools/slide_away/build_mode_casebook.py` | 7 |

## 지원 모듈

- `scripts/tools/slide_away/common.py`
  - 경로 상수
  - `signal_ready_flag` 규칙
  - barrier-relative 신호 측정항목
  - 안전 심각도 도우미
- `scripts/tools/slide_away/modeling.py`
  - 창 기능 선택
  - 클러스터링
  - 중심 거리 도우미

## 지원 스크립트 검토

| 검토 스크립트 | 래퍼 경로 | 실행 모듈 | 목적 |
| --- | --- | --- | --- |
| `review_window_candidates.py` | `scripts/review_window_candidates.py` | `scripts/tools/slide_away/review_window_candidates.py` | `100 ms`와 과거 `0-150 ms` 비교 |
| `review_minor_cluster.py` | `scripts/review_minor_cluster.py` | `scripts/tools/slide_away/review_minor_cluster.py` | `6` 케이스 마이너 클러스터 및 confounding 프로파일링 |
| `review_extended_linkage.py` | `scripts/review_extended_linkage.py` | `scripts/tools/slide_away/review_extended_linkage.py` | RI 전용 상관관계를 넘어 연계 확장 |
| `review_domain_outcome_linkage.py` | `scripts/review_domain_outcome_linkage.py` | `scripts/tools/slide_away/review_domain_outcome_linkage.py` | 결과 도메인 간 연결 분할 |
| `review_preregistered_lower_ext_subgroups.py` | `scripts/review_preregistered_lower_ext_subgroups.py` | `scripts/tools/slide_away/review_preregistered_lower_ext_subgroups.py` | 고정 검토자 규칙에 따라 하위 하위 그룹 검사를 다시 실행합니다. |
| `review_mode_confounding.py` | `scripts/review_mode_confounding.py` | `scripts/tools/slide_away/review_mode_confounding.py` | 프로듀스 측, 시대, 가문, 비중 confounding sign-off |
| `review_approval_logic.py` | `scripts/review_approval_logic.py` | `scripts/tools/slide_away/review_approval_logic.py` | pooled 요약과 도메인 인식 승인 로직 비교 |
| `review_observation_flavored_naming.py` | `scripts/review_observation_flavored_naming.py` | `scripts/tools/slide_away/review_observation_flavored_naming.py` | 계속 보수적이고 관찰에 기반한 이름을 지정하세요. |
| `review_domain_score_sensitivity.py` | `scripts/review_domain_score_sensitivity.py` | `scripts/tools/slide_away/review_domain_score_sensitivity.py` | lower-ext primary-domain 판단이 score-definition 변화에 견디는지 검토 |

## 실행된 명령

```powershell
python scripts/build_case_master.py
python scripts/build_outcome_mart.py
python scripts/build_barrier_relative_features.py --mode standard_baseline
python scripts/build_barrier_relative_features.py --mode strict_origin
python scripts/run_window_sweep.py
python scripts/run_mode_study.py --window 0.10
python scripts/build_ri_safety_map.py
python scripts/build_mode_casebook.py
python scripts/review_window_candidates.py
python scripts/review_minor_cluster.py
python scripts/review_extended_linkage.py
python scripts/review_domain_outcome_linkage.py
python scripts/review_preregistered_lower_ext_subgroups.py
python scripts/review_mode_confounding.py
python scripts/review_approval_logic.py
python scripts/review_observation_flavored_naming.py
python scripts/review_domain_score_sensitivity.py
```

## 폐쇄 참고 사항

- `signal_ready_flag`는 파일 시스템 추론이 아닌 `preprocessing_cases`에서 제공됩니다.
- 결과 ETL은 `filegroup_id` 그레인의 `pdf_result_row_catalog`에 고정됩니다.
- Barrier-relative 기능 ETL은 `preprocessing_cases`의 `harmonized_wide.parquet`에 고정됩니다.
- Barrier-relative 기능 ETL에는 이제 `x/y/z`와 다운스트림 검토를 위한 결과 harshness 지표가 포함됩니다.
- 이제 모든 필수 래퍼 경로가 존재하고 이 저장소 스냅샷에서 실행됩니다.
- 이제 초기 패키지 빌드 후 차단 감소 작업을 위한 검토 지원 스크립트가 존재합니다.
