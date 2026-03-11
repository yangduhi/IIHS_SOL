# 하위 그룹 증거 처분 메모

- snapshot_id: `slide_away_authoritative_2026-03-11`
- generated_at: `2026-03-11`
- authoritative_as_of: `2026-03-11`
- status: `reviewer closure draft`
- primary_db: `data/research/research.sqlite`
- current_window_candidate: `100 ms`
- historic_window_reference: `0-150 ms`

## 처분 초안

- 현재 권고 처분: `accept as structured reviewer evidence`
- 승인 상태: `not approved as operating subgroup rule`
- 적용 대상: `test_side=passenger`, `era=2015-2017`

## 핵심 근거

- `test_side=passenger`
  - proxy adj R^2: `0.3748`
  - interaction adj R^2: `0.3720`
  - bootstrap median adj R^2: `0.4010`
  - p10-p90: `0.1439 - 0.5794`
- `era=2015-2017`
  - proxy adj R^2: `0.3852`
  - interaction adj R^2: `0.4000`
  - bootstrap median adj R^2: `0.4040`
  - p10-p90: `0.2616 - 0.5578`

두 하위 그룹 모두 pooled severity보다 `lower_extremity` domain에서 훨씬 강한 신호를 보입니다.

## 왜 운영 규칙으로 승격하지 않는가

1. 하위 그룹 신호는 아직 `review evidence` 수준입니다.
2. composition check에서 weight quartile과 family concentration이 일부 남아 있습니다.
3. leave-one-family-out, permutation 또는 stricter holdout stability가 아직 reviewer closure 문서로 닫히지 않았습니다.
4. 현재 stronger signal의 중심은 `RI` 단독이 아니라 `seat-response / harshness / lower-ext context`입니다.

## domain sensitivity와의 연결

- `lower_extremity`는 `7/7` score-definition scenario에서 primary domain으로 유지됩니다.
- lower-ext 내부에서는 `foot_only` variant가 overall `0.3366`, passenger `0.5293`, `2015-2017` `0.5574`로 가장 강합니다.
- `thigh_only`는 overall `0.0052`로 약하므로, 현재 subgroup 신호는 `thigh`보다 `foot / lower-ext pulse context`와 더 정합적입니다.

## reviewer 결론

- passenger와 `2015-2017` 신호는 `discard` 대상이 아닙니다.
- 다만 `accepted operating subgroup rule`로 승격하기에는 아직 이릅니다.
- 현재 가장 방어 가능한 처분은 `structured reviewer evidence; not taxonomy rule`입니다.

## 후속 closure 조건

다음 중 하나가 완료되면 하위 그룹 처분을 더 강하게 조정할 수 있습니다.

1. leave-one-family-out 재검증
2. weight proxy 조정 후 재검증
3. permutation 또는 holdout stability memo
4. reviewer가 `signal remains but stays non-operational`로 명시 서명
