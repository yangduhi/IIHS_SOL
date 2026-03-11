# 슬라이드 어웨이 최종 연구 개요

- 날짜: `2026-03-11`
- 상태: `hold before final approval`

## 현재 작동 중인 것

- 연구 패키지는 실행 준비가 되어 있습니다.
- `case_master`, `outcomes_v1`, `features_v1`, `window_sweep`, `mode_study`, `ri_vs_safety_map`, `casebook` 아티팩트는 표준 `slide_away` 경로에서 생성되었습니다.
- `signal_ready_flag=406`는 `preprocessing_cases`에서 재현 가능합니다.

## 현재 증거

- 코호트:
  - 표준 사례: `413`
  - 신호 준비: `406`
  - 드라이버: `361`
  - 승객: `52`
- 아웃컴 마트:
  - 평균 품질평가점수: `0.8054`
  - 침입 범위: `329`
  - 헤드 HIC15 적용 범위: `406`
- 시간창 스윕:
  - 현재 최고 운영 기간: `100 ms`
  - 최고의 `k`: `2`
  - 실루엣: `0.7206`
- 창 후보 검토:
  - 역사적인 `0-150 ms` 기준선은 실루엣 `0.7144`에 가깝게 유지됩니다.
  - `100 ms`는 현재 목표에서 약간 더 좋지만 자동 승격에는 충분하지 않습니다.
  - 기능 안정성 관심 목록에는 `foot_resultant_asymmetry_g`, `delta_vx_mps` 및 `seat_twist_peak_mm`가 포함됩니다.
- 모드 분석:
  - 선택된 구조: `2` 모드
  - 크기 분할: `392 / 6`
- 사소한 클러스터 검토:
  - 모든 `6` 케이스는 `driver`입니다.
  - 연도: `2012 - 2013`
- confounding 가능성은 여전히 심각한 우려 사항입니다.
- 결과 연계:
  - RI 대 안전 심각도 상관 관계: `0.0193`
- 확장된 연계 검토:
  - RI 전용 모델 조정 R^2: `-0.0016`
  - RI + harshness + seat-response 프록시 조정 R^2: `0.0748`
  - RI + 상호작용 항 조정 R^2: `0.0703`
  - 이 패스에서 가장 강한 단일 신호: `seat_response_proxy_z`
- 도메인 결과 연계 검토:
  - lower-extremity 프록시 모델 조정 R^2: `0.0877`
  - 구조/침입 프록시 모델 조정 R^2: `0.0379`
  - head-neck-chest 프록시 모델 조정 R^2: `0.0194`
  - 구속/운동학 프록시 모델 조정 R^2: `0.0111`
  - 가장 강력한 하위 그룹 힌트는 lower-extremity 결과에 집중되어 있습니다.
- 사전 등록된 하위 그룹 검증:
  - passenger lower-extremity 프록시 조정 R^2: `0.3748`
  - `2015-2017` era lower-extremity 프록시 조정 R^2: `0.3852`
  - 둘 다 승인 등급 주장이 아닌 검토 증거로 남아 있습니다.
- 교란 sign-off:
  - `6` 케이스 마이너 클러스터는 여전히 `driver`, `2001-2014` 및 `Q2` 가중치 프록시에 집중되어 있습니다.
- 승인 로직 검토:
  - 풀링된 심각도는 요약 전용으로 유지됩니다.
  - lower-extremity는 현재 기본 검토 도메인입니다.
- 도메인 점수 민감도 검토:
  - `lower_extremity`는 테스트한 `7/7` score-definition scenario에서 winning domain으로 유지됩니다.
  - overall best lower-ext variant는 `foot_only`이며 adj R^2는 `0.3366`입니다.
  - `thigh_only`는 overall adj R^2 `0.0052`로 단독 설명력이 매우 약합니다.
- 관찰 중심의 명명 검토:
  - `mode_0 -> bulk moderate / unresolved`
  - `mode_1 -> high-lateral review pocket`
- 확인:
  - `unittest` 적용 범위에는 이제 기능 규칙, 창 선택 및 도메인 가입 동작이 포함됩니다.
  - 현재 연기 결과: `14` 테스트 통과
- reviewer closure pack:
  - data source, window, minor cluster, subgroup, approval frame, naming, test sufficiency 메모가 `reviews/01_governance/04_*`부터 `10_*`까지 작성됨

## 해석

- barrier-relative ETL 스택은 이제 실제적이고 재현 가능합니다.
- 현재 데이터는 아직 안정적인 최종 `slide_away` 모드 표준을 지원하지 않습니다.
- 패키지는 해결되지 않은 모드 표준화를 갖춘 검증된 연구 패키지로 가장 잘 설명됩니다.
- Occupant-compartment `x/y/z` 가속은 다음 패스에 대한 기본 물리적 읽기 계층으로 유지되어야 합니다.
- `x=ride-down`, `y=barrier-relative lateralization` 및 `z=vertical harshness`를 선행 설명 프레임으로 사용합니다.
- `x/y/z`를 독립형 승인 규칙으로 처리하지 마십시오. 승인에는 여전히 도메인 결과와 구획-응답 컨텍스트가 필요합니다.
- 현재 모드 구조는 작업 분류로의 승격을 정당화하기에는 너무 불균형합니다.
- 현재 RI 기반 연결은 너무 약해서 유리하거나 불리한 redirection 주장을 정당화할 수 없습니다.
- 프록시 인식 연결은 RI 단독보다 더 많은 정보를 제공하지만 이득은 대부분 RI 상호 작용 용어보다는 seat-response 및 harshness 컨텍스트에서 비롯됩니다.
- 현재 결과 분리는 단순한 redirection 대 크러시 명명 프레임에 반대되는 lower-extremity 축에서 가장 강력해 보입니다.
- score-definition을 흔들어도 `lower_extremity`가 primary domain으로 유지되므로 domain-first approval frame은 이전보다 더 방어 가능합니다.
- current lower-ext signal의 중심은 `thigh` 단독보다 `foot / lower-ext pulse context`에 더 가깝습니다.

## 운영규칙

- 현재 작업 레이블을 보수적으로 유지하십시오.
- 탐색적 해석을 넘어 `crush-dominant` 또는 `redirection-dominant`로 승격하지 마세요.
- 현재 출력을 해결되지 않은 모드 표준화를 통해 검증된 연구 패키지로 처리합니다.

## 다음 필수 작업

1. 사례 수준 `x/y/z` 근거를 사용하여 운영 창으로 `100 ms`를 수락하거나 거부합니다.
2. `6` 케이스의 높은 측면 포켓에 대한 리뷰어 읽기를 완료하고 혼란으로 인해 거부되는지 여부를 결정합니다.
3. `passenger` 및 `2015-2017` 하위 확장 신호가 계속 탐색적인지 아니면 구조화된 검토자 증거로 받아들여지는지 결정합니다.
4. 도메인 우선 승인 프레임을 승인하거나 거부합니다.
5. 보수적인 관찰 중심 명명 규칙을 승인하거나 거부합니다.
6. 현재 `14` 테스트가 연구 패키지 상태에 충분한지 또는 더 강력한 생산 범위가 필요한지 여부를 결정합니다.
