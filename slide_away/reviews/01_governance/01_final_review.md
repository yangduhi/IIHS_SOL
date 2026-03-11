# 슬라이드 어웨이 최종 검토

- 검토 날짜: `2026-03-11`
- 상태: `hold before final approval`
- 범위: `slide_away` 표준 패키지, 저장소 구현, 실행된 아티팩트 및 `research.sqlite` 기준 스냅샷

## 요약

이제 `slide_away`가 실행 준비가 되었습니다.
표준 스크립트 인터페이스는 닫혀 있고, `signal_ready_flag=406`는 `preprocessing_cases`에서 재현 가능하며, 1~7단계 아티팩트는 `slide_away/artifacts` 및 `slide_away/reviews` 아래에 존재합니다.

승인 상태는 이전과 다른 이유로 `hold`로 유지됩니다.
나머지 차단 요소는 더 이상 패키지 불완전성이 아닙니다. 검증 약점입니다.
가장 정확한 현재 설명은 해결되지 않은 모드 표준화가 포함된 검증된 연구 패키지입니다.
다음 패스에 대한 활성 물리적 판독 프레임은 occupant-compartment `x/y/z` 가속과 구획 응답 컨텍스트 및 도메인 결과입니다.

## 마감된 항목

1. 표준 스크립트 인터페이스 클로저
   - 다음을 위해 구현된 래퍼 및 실행 모듈:
     - `build_case_master`
     - `build_outcome_mart`
     - `build_barrier_relative_features`
     - `run_window_sweep`
     - `run_mode_study`
     - `build_mode_casebook`
     - `build_ri_safety_map`
2. `signal_ready_flag` 재현성
   - 다음과 같이 재현됩니다.
     - `mode='standard_baseline'`
     - `status='done'`
     - `harmonized_wide_path IS NOT NULL`
   - 재현 횟수 : `406`
3. 아티팩트 및 QA 종료
   - `case_master.parquet`
   - `outcomes_v1.parquet`
   - `features_v1.parquet`
   - `features_v1_strict_origin.parquet`
   - `window_sweep_summary.csv`
   - `mode_study_summary.csv`
   - `ri_vs_safety_map.csv`
   - `matched_pair_casebook.md`
   - 수치와 로그

## 현재 조사 결과

- 1단계 코호트 스냅샷:
  - 표준 사례: `413`
  - 신호 준비: `406`
  - PDF 사용 가능: `410`
  - Excel 사용 가능: `413`
- 2단계 결과 마트:
  - 평균 품질평가점수: `0.8054`
  - 침입 범위: `329`
  - 헤드 HIC15 적용 범위: `406`
  - 구속 이벤트 적용 범위: `387`
- 4단계 window sweep:
  - 현재 최고 운영 기간: `100 ms`
  - 최고의 `k`: `2`
  - 실루엣: `0.7206`
- 5단계 모드 분석:
  - `k=2`를 선택했습니다.
  - 클러스터 크기: `392 / 6`
  - 해석은 잠정적이다
- 창 후보 검토:
  - `100 ms`, `k=2`: 실루엣 `0.7206`
  - 역사적인 `0-150 ms`, `k=2`: 실루엣 `0.7144`
  - 현재 증거는 자동 승인 표준이 아닌 `100 ms`를 최고의 후보로 지원합니다.
- 사소한 클러스터 검토:
  - 모든 `6` 케이스는 `driver`입니다.
  - 연도: `2012 - 2013`
  - 모델 집중도는 confounding가 여전히 타당할 만큼 충분히 높습니다.
- 6단계 결과 연계:
  - RI 대 안전 심각도 상관 관계: `0.0193`
  - 현재 연속 RI 신호는 아직 자체적으로 설득력 있는 안전 분리를 생성하지 않습니다.
- 확장된 연계 검토:
  - RI 전용 모델 조정 R^2: `-0.0016`
  - RI + harshness + seat-response 프록시 조정 R^2: `0.0748`
  - RI + 상호작용 항 조정 R^2: `0.0703`
  - 이 패스에서 가장 강한 단일 신호: `seat_response_proxy_z`
  - 승객 및 `2015-2017` 하위 그룹 신호는 흥미롭지만 여전히 탐색적입니다.
- 도메인 결과 연계 검토:
  - lower-extremity 프록시 모델 조정 R^2: `0.0877`
  - 구조/침입 프록시 모델 조정 R^2: `0.0379`
  - head-neck-chest 프록시 모델 조정 R^2: `0.0194`
  - 구속/운동학 프록시 모델 조정 R^2: `0.0111`
  - 승객 및 `2015-2017` 하위 그룹 이익은 lower-extremity 결과에 계속 집중되어 있습니다.
  - 다음 분석 단계에서는 프레임을 RI로만 줄이는 대신 `x=ride-down`, `y=barrier-relative lateralization` 및 `z=vertical harshness`를 함께 읽어야 합니다.
- 도메인 점수 민감도 검토:
  - `lower_extremity`는 테스트한 `7/7` score-definition scenario에서 winning domain으로 유지됩니다.
  - overall best lower-ext variant는 `foot_only` adj R^2 `0.3366`입니다.
  - `thigh_only`는 overall adj R^2 `0.0052`로 단독 설명력이 거의 없습니다.
- 사전 등록된 하위 그룹 검증:
  - 승객 프록시 조정 R^2: `0.3748`
  - 시대 `2015-2017` 프록시 조정 R^2: `0.3852`
  - 둘 다 검토자가 처분할 때까지 탐색 상태를 유지합니다.
- 교란 sign-off:
  - 마이너 클러스터 강화는 `driver`, `2001-2014` 및 `Q2` 가중치 프록시에서 가장 강력합니다.
- 승인 로직 검토:
  - 풀링된 심각도는 요약 전용입니다.
  - lower-extremity는 현재 기본 검토 도메인입니다.
- 네이밍 리뷰:
  - 현재 안전한 작업 이름은 `bulk moderate / unresolved` 및 `high-lateral review pocket`입니다.
- 유효성 검사 상태:
  - 이제 공유 도우미, 기능 규칙, 창 선택 및 도메인 가입 논리에 대한 회귀 적용 범위가 존재합니다.
  - 연기 결과: `14` 테스트 통과
  - 기능/창/조인 논리에 대한 회귀 보호가 아직 불완전합니다.

## 남은 승인 방해 요소

1. 모드 타당성은 여전히 약하다
   - 선택한 `k=2`는 불균형이 매우 심합니다.
   - 마이너 클러스터에는 `6` 케이스만 있습니다.
   - 마이너 클러스터도 측면 및 시대에 집중되어 있습니다.
   - 이는 작업 표준 모드 분류로 승인하기에 충분히 강하지 않습니다.
2. 결과 연계성은 여전히 약하다
   - 현재 RI-안전 관계는 코호트 수준에서 거의 0에 가깝습니다.
   - 프록시 인식 연결은 RI 단독보다 낫지만 대부분의 이점은 컨텍스트 프록시에서 비롯됩니다.
   - 도메인 연결은 풀링된 redirection 축이 아닌 lower-extremity에서 가장 강력합니다.
   - score-definition 민감도 검토는 lower-ext primary-domain 판단을 강화하지만 reviewer sign-off를 대체하지는 못합니다.
   - `x/y/z`는 기본 설명 레이어로 유지되어야 하지만 유일한 승인 레이어는 아닙니다.
   - 현재 마트에서는 검토를 지지하지만 최종 인과관계 주장은 지지하지 않습니다.
3. 운영 기간 승격이 승인되지 않았습니다.
   - `100 ms`는 과거 `0-150 ms`를 약간 능가합니다.
   - 현재 증거는 검토자가 승인한 운영 기간 변경이 아직 부족합니다.
4. 최종 명명이 정당하지 않음
   - `crush-dominant` 및 `redirection-dominant`는 탐색적 메모로만 유지됩니다.
   - 현재 증거는 단순한 redirection 대 충돌 프레임보다 multiaxis 프레임을 더 지원합니다.
   - 안정적인 최종 `slide_away` 모드 개수는 아직 선언되지 않아야 합니다.

## 승격규칙

다음 사항이 충족된 후에만 `hold`에서 승격하세요.

1. 선택한 창은 새로운 운영 표준으로 수동으로 승인되거나 이론적 근거에 따라 명시적으로 거부됩니다.
2. 불균형 검토 및 confounding 검사 후에도 모드 구조는 해석 가능한 상태로 유지됩니다.
3. 프록시 인식 연결은 관련 결과 영역 전반에 걸쳐 실질적으로 분리되어 하위 그룹 및 confounding 검토를 유지합니다.
4. 회귀 적용 범위는 공유 도우미를 넘어 핵심 기능/창/조인 논리로 확장됩니다.
5. `final_decision_log.md`는 최종 운영 표준에 대한 승인 기준을 기록합니다.
