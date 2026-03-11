# IIHS Small Overlap Dataset Analysis Guide

## 목적

이 문서는 "다운로드된 IIHS 데이터를 어떤 순서와 기준으로 연구용 DB에 적재할 것인가"를 정리한 가이드다. 단순 분석 팁보다 적재 우선순위와 세대별 처리 전략에 초점을 둔다.

## 현재 데이터셋 스냅샷

2026-03-06 기준 `data/analysis/dataset_overview.json` 은 아래를 보여준다.

- 파일그룹 `413`
- `driver-side` `361`, `passenger-side` `52`
- 차량 연식 범위 `2001` ~ `2026`
- 다운로드 완료 파일그룹 `411`, 오류 파일그룹 `2`
- 다운로드 파일 행 `24793`, 제외 파일 행 `148`
- `DTS` 노출 파일그룹 `9`
- `sensor_channels.csv` 채널 수 `485`
- `tdas.ini` 수 `349`

상위 확장자 분포도 현재 우선순위를 잘 보여준다.

- `.bin` `14428`
- `.xlsm` `1606`
- `.pi` `1508`
- `.chn` `1404`
- `.pdf` `472`
- `.tdms` `425`
- `.tdms_index` `428`

즉, 레거시 DAS 비중이 매우 높지만, 바로 분석하기 쉬운 자산은 Excel, PDF, TDMS, DTS 쪽에 더 많다.

## 데이터 구조

안정적인 로컬 구조는 아래다.

- `data/raw/small-overlap-driver-side`
- `data/raw/small-overlap-passenger-side`
- 각 테스트 루트는 `{filegroup_id}-{test_code}`
- 대표 폴더는 `DATA/DAS`, `DATA/DIAdem`, `DATA/EDR`, `DATA/EXCEL`, `REPORTS`

현재 메타데이터 정규화 스크립트:

```powershell
D:\vscode\IIHS_SOL\.venv\Scripts\python.exe D:\vscode\IIHS_SOL\scripts\extract_dataset_metadata.py --manifest data/index/manifest.sqlite --raw-root data/raw --output-dir data/analysis
```

주요 산출물:

- `dataset_overview.json`
- `filegroups.csv`
- `filegroup_assets.csv`
- `vehicle_catalog.csv`
- `file_extensions.csv`
- `folder_profile.csv`
- `tdas_configs.csv`
- `equipment_racks.csv`
- `dts_files.csv`
- `dts_modules.csv`
- `sensor_channels.csv`

## 세대별 적재 전략

### 1. Legacy DAS-heavy tests

주요 파일:

- `*.BIN`
- `*.TLF`
- `*.LOG`
- `tdas.ini`
- `Equipment.ini`
- 일부 `DADISP/*.PI`

전략:

- 먼저 인벤토리와 설정 메타데이터를 잡는다.
- `BIN` 을 곧바로 파싱하지 않는다.
- `tdas.ini`, `Equipment.ini`, `TLF`, `LOG`, DADISP 산출물을 앵커 데이터로 사용한다.

### 2. Mid-generation DIAdem-centric tests

주요 파일:

- `DATA/DIAdem/*.TDM`
- `DATA/DIAdem/*.tdx`
- `DATA/DIAdem/*.tdms`
- Excel 요약 파일

전략:

- 파형은 `TDMS/TDM/TDX` 쪽을 우선 정리한다.
- 차량/결과 지표는 Excel 쪽을 별도 ETL로 뽑는다.

### 3. Recent ROI export tests

주요 파일:

- `*.dts`
- `*.chn`
- `DATA/DIAdem/*.tdms`
- `DATA/DAS/Binary/ROI/_Event Number 01/*`

전략:

1. `*.dts` 로 센서 카탈로그를 만든다.
2. `*.tdms` 로 분석 가능한 시계열을 만든다.
3. `*.chn` 은 `TDMS` 에 없는 정보가 있을 때만 후순위로 본다.

## 메타데이터 소스 우선순위

### 테스트/차량 메타데이터

1. `manifest.sqlite`
2. `filegroups.csv`

핵심 필드:

- `filegroup_id`
- `test_type_code`
- `test_code`
- `vehicle_year`
- `vehicle_make_model`
- `tested_on`

### 센서 및 계측 메타데이터

1. `*.dts`
2. `tdas.ini`
3. `Equipment.ini`

핵심 필드:

- `channel_id`
- `hardware_channel_name`
- `iso_code`
- `channel_group_name`
- `eu`
- `module_sample_rate_hz`

### 파형 데이터

1. `*.tdms`
2. `*.TDM`, `*.tdx`
3. `*.chn`
4. `*.BIN`

`TDMS` 는 바로 Parquet 로 변환하기 좋고, `BIN` 은 가장 나중에 다뤄야 한다.

### 문서형 데이터

1. `*.xlsm`, `*.xlsx`, `*.xls`
2. `*.pdf`

Excel 은 구조화 값 추출에 유리하고, PDF 는 보조 서술과 표 검증에 유리하다.

## DB 적재 우선순위

현재 상태를 기준으로 하면 우선순위는 아래가 맞다.

1. `manifest.sqlite` 와 `data/analysis/*.csv` 기준선 유지
2. `research.sqlite` 기본 카탈로그 재생성 가능 상태 유지
3. `excel_workbooks -> excel_sheets -> extracted_metrics`
4. `pdf_documents -> pdf_pages -> extracted_metrics`
5. `signal_containers -> signal_series`
6. 마지막에 레거시 `BIN` 심화 파싱

이 순서가 효율적인 이유:

- 문서형 자산은 적은 비용으로 구조화 수치를 빨리 얻을 수 있다.
- `TDMS + DTS` 는 최근 테스트에 대해 가장 분석 친화적이다.
- `BIN` 은 비용이 큰 반면 초기에 얻는 정보량 대비 효율이 낮다.

## 권장 조인 키

DB 적재와 분석에서 아래 키를 표준으로 사용한다.

- `filegroup_id`
- `asset_id`
- `test_code`
- `vehicle_id`
- `dts_path`
- `relative_path`

실무 규칙:

- 테스트 단위 조인은 `filegroup_id`
- 파일 단위 조인은 `asset_id` 또는 `relative_path`
- 센서 단위 조인은 `filegroup_id + channel_id` 또는 `dts_path + channel_number`

## 권장 Python 경로

기본 패키지:

```powershell
D:\vscode\IIHS_SOL\.venv\Scripts\python.exe -m pip install pandas openpyxl nptdms pyarrow pdfplumber pypdf
```

최소 TDMS 예시:

```python
from nptdms import TdmsFile

tdms = TdmsFile.read(r"D:\vscode\IIHS_SOL\data\raw\small-overlap-passenger-side\8630-CEP2501\DATA\DIAdem\CEP2501.tdms")
df = tdms.as_dataframe(time_index=True)
```

Excel 권장 규칙:

- 전체 시트 스캔은 `pandas.read_excel(..., sheet_name=None)`
- 대형 파일은 `openpyxl.load_workbook(..., read_only=True, data_only=True)`

## 지금 하지 말아야 할 것

- 레거시 `BIN` 을 전체 프로젝트의 첫 번째 ETL 대상으로 잡는 것
- 모든 세대를 하나의 파서 경로로 통일하려는 것
- 원시 파일 내용을 그대로 SQLite BLOB 로 넣는 것
- 문서에서 얻을 수 있는 수치보다 먼저 파형 역공학에 시간을 쓰는 것

## 다음 액션

1. `excel_sheets` 적재기부터 구현한다.
2. `pdf_pages` 적재기와 페이지 표 추출 전략을 정한다.
3. `TDMS -> Parquet -> signal_series` 흐름을 만든다.
4. 그 다음에도 필요한 값이 남을 때만 레거시 `BIN` 해석 범위를 좁혀 시작한다.
