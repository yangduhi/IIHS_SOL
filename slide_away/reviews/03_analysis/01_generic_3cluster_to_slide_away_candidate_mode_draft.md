# 탐색적 슬라이드 어웨이 해석 가설

- 초안 날짜: `2026-03-11`
- 상태: `exploratory only`
- 소스 기준:
  - `standard_baseline`
  - `official_known_harmonized_v3_window015`
  - `kmedoids_multiview_v3_window015`
  - `0-150 ms`

## 목적

이 메모는 기존 일반 신호 `3 cluster`에 대한 신중한 해석 레이어를 기록합니다.
최종 `slide_away` 모드 맵이 아닙니다.

현재 일반 클러스터는 다중 뷰 신호 형태 배치에서 나옵니다.
전용 barrier-relative `slide_away` 기능 마트에서 구축되지 않았습니다.

## 현재 일반 클러스터 스냅샷

- 총 건수: `406`
- 선택한 클러스터 수: `3`
- 실루엣: `0.2696`
- 클러스터 크기:
  - `cluster 0`: `359`
  - `cluster 1`: `23`
  - `cluster 2`: `24`

## 안전한 작업 해석

| 일반 클러스터 | 현재 안전한 작업 명칭 | 탐색적 slide_away 해석 | 신뢰 | 이유 |
| --- | --- | --- | --- | --- |
| `cluster 0` | `bulk moderate / mixed holding bucket` | `mixed` 후보 | 중간 | 지배적인 벌크 클러스터; 여전히 둘 이상의 물리적 하위 유형이 포함되어 있을 가능성이 높습니다. |
| `cluster 1` | `occupant-compartment-response dominant` | `crush-dominant` 후보 | 낮은 | 분리는 차량 펄스 크기보다 좌석 및 lower-extremity 응답에 의해 더 많이 구동됩니다. |
| `cluster 2` | `harsh-pulse dominant` | `redirection-dominant` 후보 | 낮은 | 분리는 차량 결과/측면/수직 harshness에 의해 구동되지만 barrier-relative redirection는 아직 직접 설정되지 않았습니다. |

## 클러스터 메모

### 클러스터 0

- 현재 대량 보유 버킷으로 가장 잘 취급됩니다.
- `mixed`는 여전히 최종 클래스가 아닌 임시 이름입니다.
- 이 클러스터에는 나중에 barrier-relative 마트에서 분할할 수 있는 여러 하위 유형이 포함될 가능성이 높습니다.

### 클러스터 1

- 현재 안전 판독값: `occupant-compartment-response dominant`
- 탐색 참고 사항: 나중에 `crush-dominant` 하위 그룹과 정렬될 수 있습니다.
- 제한:
  - 이 클러스터를 `failed crush management`로 승격하지 마세요.
  - 현재 레이블을 최종 물리적 모드로 취급하지 마십시오.

### 클러스터 2

- 현재 안전 판독값: `harsh-pulse dominant`
- 탐색 참고 사항: 나중에 `redirection-dominant` 하위 그룹과 정렬될 수 있습니다.
- 제한:
  - 이 클러스터를 `favorable redirection`로 승격하지 마세요.
  - 현재 레이블을 최종 물리적 모드로 취급하지 마십시오.

## 이것이 최종이 아닌 이유

일반 `3 cluster`는 네 가지 이유로 인해 여전히 최종 `slide_away` 모드가 아닙니다.

1. Barrier-relative 측면 기호 조화는 일반 클러스터에 직접 적용되지 않습니다.
2. `RI`, `LY`, 시트 비틀림 및 발 비대칭은 특징 축을 정의하지 않습니다.
3. 결과 연결은 클러스터링 단계에 구축되지 않습니다.
4. `359 / 23 / 24` 크기 불균형이 너무 심해서 작은 클러스터를 최종 물리적 클래스로 승격할 수 없습니다.

## 현재 근무 규칙

현재 운영 중인 사용은 아래의 안전한 작업 이름으로 제한됩니다.

- `cluster 0` -> `bulk moderate / mixed holding bucket`
- `cluster 1` -> `occupant-compartment-response dominant`
- `cluster 2` -> `harsh-pulse dominant`

아래 탐색 메모는 검토 문서에 기록될 수 있지만 현재 작업 라벨로 사용되지는 않습니다.

- `cluster 1`는 나중에 `crush-dominant`와 일치할 수 있습니다.
- `cluster 2`는 나중에 `redirection-dominant`와 일치할 수 있습니다.

## 승격규칙

다음 사항이 완료된 후에만 프로모션을 다시 방문하세요.

1. barrier-relative 기능 마트 생성
2. 창 감도 검토
3. 결과 연계 검토
4. 측면 / 시대 / 메이크 모델 confounding 리뷰
5. 대표사례 매뉴얼 검토
