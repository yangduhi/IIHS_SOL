# 도메인 결과 연계 검토

- generated_at: `2026-03-11T05:13:36Z`
- 범위: 결과 연결을 구조, lower-extremity, 구속 및 head-neck-chest 축으로 분해

## 전체 읽기

- `structure/intrusion`: RI 전용 조정 R^2 `0.0013`, 프록시 모델 `0.0379`, 상호 작용 모델 `0.0360`, 가장 강한 신호 `seat_response_proxy_z`(`r=0.1912`)
- `lower-extremity`: RI 전용 조정 R^2 `0.0017`, 프록시 모델 `0.0877`, 상호 작용 모델 `0.0850`, 가장 강한 신호 `seat_response_proxy_z`(`r=0.2327`)
- `restraint/kinematics`: RI 전용 조정 R^2 `0.0003`, 프록시 모델 `0.0111`, 상호 작용 모델 `0.0194`, 가장 강한 신호 `seat_response_proxy_z`(`r=0.1260`)
- `head-neck-chest`: RI 전용 조정 R^2 `-0.0024`, 프록시 모델 `0.0194`, 상호 작용 모델 `0.0195`, 가장 강한 신호 `harshness_proxy_z`(`r=0.1188`)

## 해석

- RI 전용 연결은 모든 결과 영역에서 약한 상태로 유지됩니다.
- 상황 인식 연결은 lower-extremity 축에서 가장 강력하며, 여기서 seat-response는 이 패스에서 지배적인 단일 신호입니다.
- 구조/침입도 컨텍스트 모델에서 개선되지만 lower-extremity보다는 적습니다.
- head-neck-chest 연결은 seat-response보다 harshness에 더 많이 의존합니다.
- 구속/운동학은 여전히 약하며 아직 명명 또는 승인 결정을 내리지 않아야 합니다.

## 하위 그룹 힌트

- 승객 lower-extremity 상호작용 모델: adj R^2 `0.3720` (`n=52`)
- 시대 `2015-2017` lower-extremity 상호작용 모델: adj R^2 `0.4000` (`n=131`)
- 현재 하위 그룹의 이득은 일반적인 redirection 효과보다는 lower-extremity 결과에 집중된 것으로 보입니다.

## 추천

- 연결 스택에 RI를 유지하지만 선행 설명 축에서 강등합니다.
- 다음 명명 검토에서는 seat-response 및 harshness 컨텍스트의 우선순위를 지정합니다.
- 단일 통합 안전 점수에 의존하는 대신 결과 영역별로 향후 승인 논의를 분할합니다.
