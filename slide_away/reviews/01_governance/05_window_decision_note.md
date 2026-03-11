# 운영 시간창 결정 메모

- snapshot_id: `slide_away_authoritative_2026-03-11`
- generated_at: `2026-03-11`
- authoritative_as_of: `2026-03-11`
- status: `reviewer closure draft`
- primary_db: `data/research/research.sqlite`
- current_window_candidate: `100 ms`
- historic_window_reference: `0-150 ms`

## 결정 초안

- 현재 추천 판단: `100 ms`를 현행 분석 기본창으로 조건부 유지
- historic `0-150 ms`는 즉시 폐기하지 않고 reviewer reference baseline으로 유지
- 최종 상태: `not auto-promoted; manual reviewer sign-off required`

## 근거 요약

- `100 ms`, `k=2`: silhouette `0.7206`
- `150 ms`, `k=2`: silhouette `0.7144`
- 차이는 존재하지만 크지 않으며, 창 변경이 곧바로 naming이나 approval layer를 뒤집는 수준은 아님
- `100 ms`가 현 objective에서는 약간 우세하지만, reviewer sign-off 없이 historic baseline을 retire할 정도의 격차는 아님

## feature stability watchlist

- `delta_vx_mps`
  - paired_count: `406`
  - Pearson r: `0.8717`
  - mean_abs_delta: `2.4635`
- `foot_resultant_asymmetry_g`
  - paired_count: `406`
  - Pearson r: `0.8163`
  - mean_abs_delta: `2.4432`
- `seat_twist_peak_mm`
  - paired_count: `318`
  - Pearson r: `0.9612`
  - mean_abs_delta: `3.3458`

`ax`, `ay`, `az`, `resultant` peak는 높은 상관을 유지하지만, `delta_vx`, `foot asymmetry`, `seat twist`는 창 변화의 영향을 상대적으로 더 받습니다.

## 대표 사례 판독

- `CEN1813` `2019 Chevrolet Silverado 1500 (crew cab)`
  - `ay 26.47 -> 39.12`, `az 62.76 -> 69.14`, `RI 0.462 -> 0.302`
  - 창 선택에 따라 lateral/vertical harshness 해석이 달라질 수 있는 사례
- `CEN1901` `2019 Honda HR-V`
  - `ay 16.76 -> 23.02`, `az 28.59 -> 38.21`, `RI 0.382 -> 0.438`
  - `100 ms`와 `150 ms`가 동일한 physical reading을 주지 않음
- `CEN2102` `2021 Ford Mustang Mach-E`
  - `RI 0.570 -> 1.391`
  - `y` signature 해석이 창에 민감하므로 automatic promotion 근거로 쓰기 어려움
- `CEN1601` `2016 Chevrolet Silverado 1500 (Crew cab)`
  - `seat_twist 252.69 -> 479.59`
  - Level 2 compartment-response 해석이 창 선택에 크게 좌우될 수 있음

## reviewer 판단 기준

다음 네 가지를 함께 만족할 때만 `100 ms`를 historic baseline에서 완전히 승격합니다.

1. 사례 수준 `x/y/z` 판독이 `100 ms`에서 더 안정적일 것
2. domain linkage가 `100 ms`에서 유지될 것
3. naming rule이 `100 ms` 채택으로 불필요하게 바뀌지 않을 것
4. watchlist feature가 reviewer가 납득할 정도로 안정적일 것

## 현재 권고

- ongoing analysis default로는 `100 ms`를 유지합니다.
- review memo에서는 historic `0-150 ms`와의 비교 근거를 함께 제시합니다.
- final approval 전까지 `100 ms adopted as final operating standard`라고 쓰지 않습니다.
