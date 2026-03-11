# IIHS SOL Signal Preprocessing Standard

이 문서는 `docs/sol_signal_preprocessing_bible.json`의 규칙을 실제 처리 단계로 내리기 위한 운영 표준이다. 첫 검증 대상은 `filegroup_id=7168`, `test_code=CEN2005`, `2021 Kia Seltos` 이다.

## 1. 레이어 구분

1. `canonical raw-preserving layer`
   - 원본 파일은 수정하지 않는다.
   - `TDMS`는 그대로 보존하고, 열린 분석용 사본은 Parquet로 만든다.
   - 이 레이어의 기준 스크립트는 [`export_signal_parquet.py`](/d:/vscode/IIHS/scripts/export_signal_parquet.py) 이다.
2. `official-known preprocessing layer`
   - IIHS가 명시적으로 규정한 channel family만 포함한다.
   - `TDMS` 안에 이미 존재하는 `DIAdem` 처리 채널을 공식 레이어의 1차 소스로 사용한다.
   - 공식 레이어의 시간축은 TDMS signal `time_track()`를 우선 사용한다. 명시적 `Time axis` 채널은 waveform과 sample-aligned 일 때만 사용한다.
   - 기본값으로 `T0`를 다시 잡지 않는다.
3. `exploratory layer`
   - `T0 alignment`, 비공식 zeroing, 추가 normalization은 여기서만 허용한다.
   - 공식 레이어와 같은 네임스페이스를 사용하지 않는다.

## 2. 소스 우선순위

1. `DTS metadata`
2. `TDMS signal payload`
3. `TDM/TDX via DIAdem export`
4. `CSV sidecar`
5. `legacy BIN/PI/CHN/TLF family`

`CEN2005`는 `DTS`가 없고 `TDMS + CSV`만 있으므로, 이번 표준 검증에서는 `TDMS`가 신호와 메타데이터의 실질적인 기준이다.

## 3. 공식 레이어 포함 범위

다음 family만 이번 표준에 포함한다.

- `vehicle acceleration array`: `CFC 60`
- `seat back deflection`: `CFC 60`
- `foot acceleration`: `CFC 180`

다음은 이번 표준에서 하지 않는다.

- 명시 근거 없는 channel별 `CFC` 추정
- raw signal inplace 수정
- 공식 레이어에서의 `T0` 재정렬

## 4. CEN2005 적용 방식

입력:

- [`CEN2005.tdms`](/d:/vscode/IIHS/data/raw/small-overlap-driver-side/7168-CEN2005/DATA/DIAdem/CEN2005.tdms)
- [`TestEnvironmentalData.csv`](/d:/vscode/IIHS/data/raw/small-overlap-driver-side/7168-CEN2005/DATA/EXCEL/TestEnvironmentalData.csv)

공식 레이어 채널:

- `1_Vehicle/10VEHC0000__ACXD`, `ACYD`, `ACZD`, `ACRD`
- `1_Vehicle/11SEATMI0000DSXD`, `11SEATIN0000DSXD`
- `11_Left_Leg/11FOOTLE00__ACXC`, `11FOOTLE00__ACZC`
- `11_Right_Leg/11FOOTRI00__ACXC`, `11FOOTRI00__ACZC`

원시 참조 채널은 provenance와 진단용으로만 연결한다.

`CEN2005`에서는 명시적 `CEN2005_Raw_Data/Time axis` 채널이 `6001` samples, 실제 waveform 채널은 `6000` samples 이다. 따라서 이번 전처리에서는 `1_Vehicle/10VEHC0000__ACXD.time_track()`를 시간 기준으로 채택했다.

## 5. T0 방식에 대한 판단

다른 프로젝트의 `Anchor & Backtrack` 방식은 참고 가치가 있다. 다만 현재 저장소의 기본 표준으로는 채택하지 않는다.

이유:

- IIHS 기준 문서에는 `50~-40 ms pre-impact mean subtraction`과 family별 `CFC`는 명시되어 있지만, 저장소 기본 시간축을 다시 `T0`로 옮기라는 요구는 없다.
- `CEN2005.tdms`는 이미 `DIAdem` 후처리 채널과 음수 방향 crash pulse 시간축을 포함한다.
- 따라서 `T0 alignment`는 공식 레이어가 아니라 `exploratory layer`로 분리해야 provenance가 유지된다.

이번 파일그룹에서는 비교용으로만 `vehicle_longitudinal_accel_g`에 대해 `T0 proxy` 산출물을 만든다. 이는 기존 공식 filtered 채널을 입력으로 쓰는 비교용 산출물이지, raw+CFC 재처리의 대체물이 아니다.

## 6. 실행

```powershell
python scripts/preprocess_known_signal_families.py --filegroup-id 7168
```

산출물 기본 위치:

- `data/derived/small_overlap/preprocessed_signals/7168-CEN2005/official_known_families_wide.parquet`
- `data/derived/small_overlap/preprocessed_signals/7168-CEN2005/official_known_families_long.parquet`
- `data/derived/small_overlap/preprocessed_signals/7168-CEN2005/exploratory_vehicle_longitudinal_t0_proxy.parquet`
- `data/derived/small_overlap/preprocessed_signals/7168-CEN2005/preprocessing_manifest.json`
