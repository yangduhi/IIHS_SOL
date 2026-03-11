# 승인 프레임 sign-off 메모

- snapshot_id: `slide_away_authoritative_2026-03-11`
- generated_at: `2026-03-11`
- authoritative_as_of: `2026-03-11`
- status: `reviewer closure draft`
- primary_db: `data/research/research.sqlite`
- current_window_candidate: `100 ms`
- historic_window_reference: `0-150 ms`

## sign-off 초안

- 현재 권고: `domain-first approval frame accepted`
- pooled severity 역할: `summary-only`
- current primary approval domain: `lower_extremity`

## 승인 프레임 정의

- `Level 1`
  - occupant-compartment `x/y/z`, delta-V, RI, timing, duration
  - 역할: `physical reading layer`
- `Level 2`
  - seat twist, foot asymmetry, lower-ext proxy, restraint timing
  - 역할: `context layer`
- `Level 3`
  - intrusion, lower-extremity, restraint/kinematics, head-neck-chest
  - 역할: `approval layer`

이 구조에서 `x/y/z`는 핵심 물리 해석축이지만, 단독 승인축은 아닙니다.

## 근거 요약

- pooled safety proxy adj R^2: `0.0748`
- lower-extremity proxy adj R^2: `0.0877`
- structure/intrusion proxy adj R^2: `0.0379`
- head-neck-chest proxy adj R^2: `0.0194`
- restraint/kinematics proxy adj R^2: `0.0111`
- domain sensitivity:
  - `lower_extremity` winner in `7/7` tested scenarios

## reviewer 해석

- pooled severity는 전체 방향을 보는 summary signal로는 유용합니다.
- 하지만 current mode standardization을 승인하는 primary evidence로는 약합니다.
- 현재 strongest separation은 `lower_extremity` domain과 `foot / lower-ext pulse context` 쪽에서 나옵니다.
- 따라서 approval을 pooled severity 단독으로 묶는 것은 현재 evidence와 맞지 않습니다.

## 현재 승인 규칙

1. pooled severity만으로 taxonomy를 승인하지 않습니다.
2. domain outcome을 primary approval layer로 사용합니다.
3. 현재는 `lower_extremity`를 primary review domain으로 둡니다.
4. `structure/intrusion`, `head-neck-chest`는 secondary support로 사용합니다.
5. `restraint/kinematics`는 supporting evidence로만 사용합니다.

## 현재 결론

- domain-first approval frame은 현재 evidence 기준으로 채택 가능합니다.
- 다만 이는 `final taxonomy approved`를 의미하지 않습니다.
- approval state는 계속 `hold`이며, 이 sign-off는 승인 기준을 정리할 뿐 final approval을 해제하지 않습니다.
