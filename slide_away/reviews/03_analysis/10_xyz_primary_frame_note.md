# XYZ 기본 프레임 참고

- 날짜: `2026-03-11`
- 상태: `active framing note`

## 목적

이 노트는 다음 `slide_away` 분석 패스에 대한 의도된 판독 프레임을 수정합니다.
연구에서는 기본 물리적 해석 계층으로 occupant-compartment `x/y/z` 가속을 우선시해야 합니다.
이는 `x/y/z`가 유일한 승인 기준이라는 의미는 아닙니다.
이는 `x/y/z`가 물리적 판독을 주도해야 하며 구획 응답 컨텍스트 및 도메인 결과는 승인을 위해 계속 필요함을 의미합니다.

## 1차 통역

- `x`
  - ride-down
  - 종방향 델타-V 컨텍스트
  - 순방향 축의 타이밍 및 펄스 지속 시간
- `y`
  - barrier-relative 편측화
  - redirection 컨텍스트
  - 측면 조화 `away` 해석
- `z`
  - 수직 harshness
  - 휠 또는 서스펜션 경로 반응
  - 잠재적인 lower-extremity 및 상체의 가혹한 상황 상황

## 이 프레임이 유지되는 이유

- IIHS Small Overlap 연구 논리는 `x`만으로는 잘 표현되지 않습니다.
- barrier-relative 측면 이동 및 redirection 판독에는 `y`가 필요합니다.
- 현재 연결 작업에서 harshness가 여전히 정보를 제공하므로 `z`를 삭제해서는 안 됩니다.
- 현재 패키지 증거는 RI 전용 또는 바이너리 redirection 대 충돌 프레임보다 multiaxis 운동학 프레임과 더 일치합니다.

## 제한

- 이러한 신호는 occupant-compartment 펄스 및 운동학 프록시로 가장 잘 처리됩니다.
- 직접적인 차량-글로벌 에너지 회계로 제시되어서는 안됩니다.
- 그 자체로 최종 승인을 받기에 충분한 것으로 간주되어서는 안 됩니다.
- 최종 승인에는 여전히 도메인 인식 결과 증거와 구획 응답 컨텍스트가 필요합니다.

## 3중 구조 작동

1. `Level 1: kinematics and pulse`
   - `x/y/z` 가속
   - 델타-V
   - RI
   - 타이밍 및 기간 기능
2. `Level 2: compartment and occupant-response context`
   - 좌석 트위스트
   - 발 비대칭
   - lower-extremity 프록시
   - 구속 타이밍 프록시
3. `Level 3: approval and outcome evidence`
   - 강요
   - lower-extremity 결과
   - 구속 및 운동학 결과
   - head-neck-chest 결과

## 다음 작업에 대한 즉각적인 영향

1. `100 ms` 대 과거 `0-150 ms` 검토는 RI 단독이 아닌 먼저 `x/y/z` 서명 변경을 기준으로 대표적인 사례를 비교해야 합니다.
2. 마이너 클러스터 수동 검토에서는 모드 의미를 할당하기 전에 `x/y/z` 펄스 용어로 클러스터를 읽어야 합니다.
3. 하위 그룹 재테스트에서는 동일한 `x/y/z + context + domain outcome` 구조를 유지해야 합니다.
4. Confounding 검토에서는 관찰된 `x/y/z` 차이가 측면, 시대, 제조사 모델 제품군 또는 가중치 클래스 슬라이싱에서 붕괴되는지 여부를 명시적으로 테스트해야 합니다.
5. 명명 재설계는 관찰 중심으로 유지되어야 하며 현재 증거를 초과해서는 안 됩니다.

## 현재 안전 위치

가장 안전한 현재 해석은 다음과 같습니다.

- 물리적 읽기 계층의 중앙에 `x/y/z`를 유지합니다.
- `RI`를 유일한 리드 축이 아닌 하나의 구성 요소로 유지하십시오.
- seat-response 및 harshness를 필수 컨텍스트로 유지
- 도메인 결과를 승인 계층으로 유지
- 나머지 차단기가 닫힐 때까지 최종 모드 명명을 보수적으로 유지하십시오.
