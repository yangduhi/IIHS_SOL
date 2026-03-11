# IIHS Database Build Playbook

## 목적

이 문서는 현재 프로젝트의 단일 운영 진입점이다. 이미 내려받은 IIHS Small Overlap 데이터를 기준으로, 연구용 DB를 재현 가능하게 구축하고 검증하는 절차를 정리한다.

## 현재 상태

2026-03-06 22:16:50 +09:00 기준 현재 기준선:

- 파일그룹 `413`
- 폴더 `3117`
- 자산 `24943`
- 다운로드 완료 `24793`
- 제외 `148`
- 다운로드 오류 `2`
- `signal_containers` `20192`
- `excel_workbooks` `1851`
- `excel_sheets` `0`
- `pdf_documents` `472`
- `pdf_pages` `5361`
- `pdf_page_features` `5361`
- `pdf_layout_assignments` `489`
- `extracted_metrics` `2476`
- `signal_series` `0`
- PDF 상태 `done 470`, `skipped 2`

해석:

- 다운로드 인벤토리와 연구용 카탈로그는 구축됨
- PDF layout 분류와 1차 extractor는 완료됨
- `excel_sheets` 와 `signal_series` 는 아직 비어 있으므로 다음 단계 ETL이 남아 있음

## 기준선 레이어

### Layer 1. Download inventory

- `data/index/manifest.sqlite`
- `data/index/filegroups.jsonl`
- `data/index/folders.jsonl`
- `data/index/files.jsonl`

역할:

- 어떤 테스트와 파일을 받았는지 기록하는 기준선

### Layer 2. Analysis staging

- `data/analysis/*.csv`
- `data/analysis/dataset_overview.json`

역할:

- 파서 친화적인 중간 정규화 층
- DB 적재 전 메타데이터 검증 층

### Layer 3. Research catalog

- `sql/research_database.sql`
- `scripts/init_research_database.py`
- `scripts/process_pdfs.py`
- `data/research/research.sqlite`

역할:

- 연구용 조회
- 적재 상태 추적
- 후속 ETL의 공통 조인 기준

## 표준 실행 순서

### 1. 분석 중간 산출물 재생성

```powershell
D:\vscode\IIHS_SOL\.venv\Scripts\python.exe D:\vscode\IIHS_SOL\scripts\extract_dataset_metadata.py --manifest data/index/manifest.sqlite --raw-root data/raw --output-dir data/analysis
```

확인 포인트:

- `dataset_overview.json` 생성 여부
- `tdas_configs.csv`, `dts_files.csv`, `sensor_channels.csv` 갱신 여부

### 2. 연구용 DB 초기화 또는 갱신

```powershell
D:\vscode\IIHS_SOL\.venv\Scripts\python.exe D:\vscode\IIHS_SOL\scripts\init_research_database.py --manifest data/index/manifest.sqlite --analysis-dir data/analysis --schema sql/research_database.sql --output-db data/research/research.sqlite
```

확인 포인트:

- `filegroups`, `assets`, `signal_containers`, `excel_workbooks`, `pdf_documents` 카운트가 기대치에 맞는지
- PDF 관련 확장 테이블이 실제 DB에도 반영됐는지

### 3. PDF ETL 재실행 또는 검증

```powershell
D:\vscode\IIHS_SOL\.venv\Scripts\python.exe D:\vscode\IIHS_SOL\scripts\process_pdfs.py --all
```

옵션:

- 미리보기까지 다시 만들려면 `--render-previews`
- 특정 문서만 다시 돌리려면 `--pdf-document-id=<id>`

확인 포인트:

- `pdf_pages = 5361`
- `pdf_page_features = 5361`
- `extracted_metrics > 0`
- `pdf_documents` 상태가 `done` 또는 `skipped` 만 남는지

주의:

- 현재 `skipped` 2건은 사용자 승인 하에 제외된 케이스다.
- 대상 문서:
  - `pdf_document_id = 18`
  - `pdf_document_id = 318`
- 이유:
  - 원본 PDF 대신 로그인 HTML이 저장된 손상 다운로드
  - 현재 completeness target에서 제외

## 카운트 검증

최소 검증 기준:

- `filegroups = 413`
- `assets = 24943`
- `signal_containers = 20192`
- `excel_workbooks = 1851`
- `pdf_documents = 472`
- `pdf_pages = 5361`
- `pdf_page_features = 5361`
- `pdf_documents(done) = 470`
- `pdf_documents(skipped) = 2`

현재 비어 있어도 정상인 테이블:

- `signal_series`
- `excel_sheets`

현재 비어 있으면 안 되는 테이블:

- `pdf_pages`
- `pdf_page_features`
- `pdf_layout_assignments`
- `extracted_metrics`

## 현재 PDF ETL 결과

- PDF extractor run:
  - sample run `pdf_extraction_run_id = 1`
  - full run `pdf_extraction_run_id = 2`
- latest full run scope: `all=True`
- latest full run result: `processed 472`, `success 470`, `error 2`
- 이후 운영 판단으로 `error 2` 는 `skipped 2` 로 전환

현재 확인된 family 분포는 아래와 같다.

- `report_iihs_generic` `300`
- `report_modern_small_overlap_v7` `73`
- `report_legacy_crashworthiness` `59`
- `edr_bosch_cdr` `45`
- `edr_hyundai_g_edr` `5`
- `report_modern_small_overlap_v8` `5`
- `edr_generic` `1`
- `edr_restraint_control_module` `1`

## 다음 우선순위

### 1순위. Excel ETL

이유:

- 워크북 수가 많고 구조화 가치가 높다.
- intrusion, UMTRI, summary, environmental 데이터가 직접 분석값으로 연결된다.

목표 테이블:

- `excel_sheets`
- `extracted_metrics`

### 2순위. TDMS to Parquet

이유:

- 최근 테스트의 시계열 분석 경로를 가장 빨리 열 수 있다.
- `DTS` 와 결합해 센서 메타데이터를 자연스럽게 붙일 수 있다.

목표 테이블:

- `signal_series`

### 3순위. Legacy DAS deep parse

이유:

- 비용이 가장 크고, 문서형 ETL과 최근형 TDMS ETL보다 우선순위가 낮다.

대상:

- `BIN`
- `TLF`
- 일부 `CHN`

### 4순위. Optional source-side recovery

이유:

- 현재 `skipped` 2건은 운영 목표를 막지 않지만, 필요하면 나중에 원본 사이트에서 다시 복구 시도할 수 있다.

## 운영 규칙

- `data/raw` 는 입력 자산이며 수정하지 않는다.
- DB에는 원본 바이너리를 넣지 말고 경로와 메타데이터만 넣는다.
- 스키마를 바꾸면 문서와 초기화 스크립트를 같이 바꾼다.
- 세대가 다른 자산을 한 파서로 억지로 통일하지 않는다.
- 상태값은 문서보다 DB에 먼저 남긴다.

## 완료 기준

아래 조건이 맞으면 현재 단계의 DB 구축 문서와 운영 체계가 정리된 것으로 본다.

- 누가 봐도 `manifest -> analysis -> research DB -> document ETL` 순서를 따라갈 수 있다.
- 어떤 ETL이 완료됐고 어떤 ETL이 남았는지 즉시 보인다.
- PDF ETL 상태가 `done/skipped` 기준으로 닫혀 있다.
- 다음 구현 범위가 `Excel ETL` 과 `TDMS -> Parquet` 로 명확히 좁혀져 있다.
