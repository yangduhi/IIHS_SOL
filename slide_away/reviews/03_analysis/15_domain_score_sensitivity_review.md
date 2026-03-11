# 도메인 점수 민감도 검토

- generated_at: `2026-03-11T06:32:43Z`
- 범위: 현재 도메인 우선 승인 프레임이 합리적인 score 정의 변경에 민감한지 검토

## 핵심 요약

- `lower_extremity_score`는 테스트한 `7/7`개 score-definition 시나리오 모두에서 winning domain으로 유지됩니다.
- baseline winner는 `lower_extremity_score`이며 adj R^2는 `0.0877`, 2위 대비 margin은 `0.0498`입니다.
- `leg+foot`만 사용한 lower-ext variant는 adj R^2를 `0.1256`까지 올립니다.
- `foot`만 사용한 lower-ext variant는 adj R^2를 `0.3366`까지 올립니다.
- 테스트한 structure, restraint, head-neck-chest 재정의 중 어느 것도 lower-extremity를 추월하지 못했습니다.

## Lower-Ext 구성요소 판독

- overall best variant는 `foot_only`이고 adj R^2는 `0.3366`입니다.
- passenger best variant는 `foot_only`이고 adj R^2는 `0.5293`입니다.
- `2015-2017` best variant는 `foot_only`이고 adj R^2는 `0.5574`입니다.
- 전체 기준 가장 약한 variant는 `thigh_only`이며 adj R^2는 `0.0052`입니다.
- 현재 신호 위계는 넓은 pooled RI-only 스토리보다 `foot / lower-ext pulse context`와 더 잘 맞습니다.
- `thigh_only`는 도메인을 단독으로 끌고 갈 만큼 약하므로, 현재 lower-ext 신호는 thigh proxy 하나에서 오지 않습니다.

## 해석

- 이번 민감도 검토 이후 현재의 domain-first approval frame은 더 방어 가능해졌습니다.
- `x/y/z + context + domain outcome` 3층 구조는 여전히 맞습니다.
- 몇 가지 합리적인 score 정의를 흔들어도 `lower_extremity`는 primary domain으로 유지됩니다.
- lower-ext domain 내부에서는 `thigh_hip_risk_proxy`보다 `foot_resultant_accel`이 설명력을 더 많이 담당합니다.
- 이는 승인 레이어에서 `seat-response`, `foot asymmetry`, lower-ext context를 유지해야 한다는 근거를 강화합니다.

## 권고

- 현재 primary review domain은 `lower_extremity`로 유지합니다.
- lower-ext 신호가 테스트한 score-definition 변화에 견고하다는 reviewer note를 추가합니다.
- 다음 수동 검토 패스에서는 `foot_resultant_accel`과 관련 lower-ext context를 전면에 둡니다.
- 이 결과만으로 최종 승인으로 해석하지 마십시오. 검증 우려 하나를 줄였을 뿐, 남은 reviewer sign-off를 닫지는 못합니다.

