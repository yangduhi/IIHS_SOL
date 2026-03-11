# 확장된 결과 연계 검토

- generated_at: `2026-03-11T05:13:37Z`
- 범위: `100 ms` harshness 및 seat-response 프록시를 사용하여 RI 전용 상관 관계를 넘어 연결 확장

## 전체 읽기

- RI 전용 모델: adj R^2 `-0.0016`
- RI + harshness + seat-response 프록시: 조정 R^2 `0.0748`
- RI + 상호작용 항: adj R^2 `0.0703`
- 이 패스에서 가장 강한 단일 신호: Pearson r `0.2099` 및 상하 안전 간격 `0.5379`가 포함된 `seat_response_proxy_z`
- 상호작용 용어는 코호트 수준에서 프록시 전용 모델 외에는 거의 추가되지 않습니다.

## 프록시 정의

- `harshness_proxy_z`: 표준화된 `window_100_max_abs_az_g` 및 `window_100_max_abs_resultant_g`를 의미합니다.
- `seat_response_proxy_z`: 표준화된 `window_100_seat_twist_peak_mm` 및 `window_100_foot_resultant_asymmetry_g`를 의미합니다.
- `ri_x_harshness`: `RI_z * harshness_proxy_z`
- `ri_x_seat_response`: `RI_z * seat_response_proxy_z`

## 하위 그룹 읽기

- 승객 하위 그룹(`n=52`): 상호 작용 모델 조정 R^2 `0.2117`
- era `2015-2017` (`n=131`): 상호작용 모델 조정 R^2 `0.2536`
- 낮은 seat-response 대역(`n=101`): RI 전용 Pearson r `-0.2505`
- 현재 `mode_1` 마이너 클러스터는 안정적인 하위 그룹 모델에 비해 여전히 너무 작습니다.

## 해석

- harshness 및 seat-response 컨텍스트가 포함되면 결과 연결이 향상됩니다.
- 대부분의 이득은 RI 상호 작용 용어가 아닌 컨텍스트 프록시 자체, 특히 seat-response에서 발생합니다.
- 이렇게 하면 RI만 과도하게 읽을 위험이 줄어들지만 여전히 최종적으로 호의적이거나 불리한 redirection 주장을 정당화할 수는 없습니다.

## 추천

- 독립형 승인 신호가 아닌 연결 스택의 하나의 구성 요소로 RI를 유지합니다.
- 다음 리뷰어 패스에 `seat_response_proxy_z` 및 `harshness_proxy_z`를 포함합니다.
- 수동 검토 및 confounding 확인이 완료될 때까지 하위 그룹 신호를 탐색 신호로 처리합니다.
