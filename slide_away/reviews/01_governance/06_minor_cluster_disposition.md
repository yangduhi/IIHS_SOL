# 마이너 클러스터 처분 메모

- snapshot_id: `slide_away_authoritative_2026-03-11`
- generated_at: `2026-03-11`
- authoritative_as_of: `2026-03-11`
- status: `reviewer closure draft`
- primary_db: `data/research/research.sqlite`
- current_window_candidate: `100 ms`
- historic_window_reference: `0-150 ms`

## 처분 초안

- 현재 권고 처분: `retain as rare review pocket`
- 승인 상태: `not approved as working mode`
- 현재 안전한 working name: `high-lateral review pocket`

## 왜 최종 모드가 아닌가

1. cluster size가 `6`으로 매우 작습니다.
2. 전 케이스가 `driver`입니다.
3. 전 케이스가 `2012-2013`에 집중되어 있습니다.
4. make-model family가 좁고, confounding 검토에서도 `driver`, `2001-2014`, `Q2` weight proxy 쏠림이 확인됐습니다.
5. 따라서 현재는 `interpretable signal`보다 `rare pocket under confounding risk`로 읽는 편이 안전합니다.

## 현재 관측 특징

- 평균 `DeltaVy_away`: `51.983`
- 평균 `RI`: `4.156`
- 평균 `ay`: `175.28`
- 평균 `az`: `23.91`
- 평균 `seat_twist`: `12.19`
- 평균 `foot_asym`: `26.43`

즉 이 pocket은 `seat-response dominant`라기보다 `high-lateral x/y signature` 쪽으로 읽히지만, 현재 증거만으로 stable physical mode라 단정할 수는 없습니다.

## 케이스 목록

- `CEN1219` `2012 Hyundai Sonata`
  - `DeltaVy_away 43.671`, `RI 5.352`, `ay 269.69`, intrusion `28.0`
- `CEN1229` `2013 Honda Accord 4-door`
  - `DeltaVy_away 57.750`, `RI 4.539`, `ay 164.86`, intrusion `17.0`
- `CEN1234` `2013 Honda Accord 2-door`
  - `DeltaVy_away 69.762`, `RI 5.112`, `ay 132.00`, intrusion `16.0`
- `CEN1301` `2013 Honda Civic 2-door`
  - `DeltaVy_away 59.887`, `RI 4.242`, `ay 156.84`, intrusion `9.0`
- `CEN1302` `2013 Honda Civic 4-Door`
  - `DeltaVy_away 59.631`, `RI 4.523`, `ay 158.70`, intrusion `15.0`
- `CEN1304` `2013 Volvo XC 60`
  - `DeltaVy_away 70.307`, `RI 5.250`, `ay 169.60`, intrusion `6.0`

## reviewer 판정 옵션

- `reject as confounded`
  - confounding risk가 과도하다고 판단될 때
- `retain as rare review pocket`
  - 현재 추천
- `retain as interpretable rare kinematic subgroup`
  - 수기 case review에서 공통 기계적 signature가 더 명확히 닫힐 때만 고려

## 현재 권고

- taxonomy에는 포함하지 않습니다.
- casebook과 수기 검토에서는 별도 watch pocket으로 유지합니다.
- reviewer sign-off 전까지 `redirection-dominant` 또는 다른 최종 mode name으로 승격하지 않습니다.
