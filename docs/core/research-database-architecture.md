# Research Database Architecture

## 목적

이 프로젝트의 연구용 DB는 "모든 파일을 하나의 SQLite 본문 테이블에 넣는 구조"가 아니라, 아래 3계층을 분리하는 구조를 목표로 한다.

1. 다운로드 인벤토리
2. 분석 중간 정규화
3. 연구용 카탈로그 DB

이 구조는 413개 filegroup 전체를 하나의 운영 체계 아래 묶으면서도, 대용량 파형과 문서형 ETL을 단계적으로 확장할 수 있게 만든다.

## 현재 기준선

2026-03-06 22:16:50 +09:00 기준 `data/research/research.sqlite` 상태:

- `filegroups` `413`
- `assets` `24943`
- `signal_containers` `20192`
- `excel_workbooks` `1851`
- `excel_sheets` `0`
- `pdf_documents` `472`
- `pdf_pages` `5361`
- `pdf_page_features` `5361`
- `pdf_layout_assignments` `489`
- `extracted_metrics` `2476`
- `signal_series` `0`

문서형 ETL 관점 해석:

- PDF layout classification과 1차 extractor는 완료 상태다.
- Excel ETL과 waveform normalization은 아직 미구현 상태다.

## 권장 데이터 모델

### Layer 1. Catalog database

SQLite는 현재 단계에 적합하다. 빠른 조회, 경량 운영, 재현 가능한 ETL 추적에 유리하다.

이 레이어가 담당하는 범위:

- 테스트/차량 기준선
- filegroup, folder, asset 인벤토리
- TDAS, equipment, DTS 기반 메타데이터
- Excel/PDF 적재 상태
- 파형 컨테이너와 후속 `Parquet` 시리즈 등록
- 추출 metric 저장

### Layer 2. Waveform lake

대용량 시계열은 DB 본문보다 파일 계층에 두는 것이 맞다.

대상:

- 원본 `BIN`, `TLF`, `CHN`, `TDMS`, `TDM`, `TDX`
- 파생 `Parquet`

DB에는 아래만 남긴다.

- 원본 또는 파생 파일 경로
- 채널 이름과 시리즈 key
- 샘플 수
- 샘플링 레이트
- 단위
- 요약 통계

### Layer 3. Analytics

실제 분석은 DB와 Parquet를 함께 쓴다.

권장 도구:

- Pandas 또는 Polars: ETL
- DuckDB: Parquet 질의
- SQLite: 카탈로그 조인과 상태 관리

## 스키마 개요

### Registry

- `build_runs`
- `test_types`
- `vehicles`
- `filegroups`

이 계층은 "무엇을 수집했고 어떤 테스트인가"를 정의한다.

### Inventory

- `folders`
- `assets`

이 계층은 다운로드 산출물의 전체 목록과 파일 상태를 관리한다.

### DAS and sensor metadata

- `tdas_configs`
- `equipment_racks`
- `dts_files`
- `dts_modules`
- `sensor_channels`

최근형 테스트는 `DTS` 기반 센서 카탈로그가 강하고, 구형은 `tdas.ini`가 중요하다.

### Signal catalog

- `signal_containers`
- `signal_series`

현재 `signal_containers` 는 채워져 있고 `signal_series` 는 비어 있다. 즉 파형 자산은 등록됐지만, 분석 가능한 채널 단위 시리즈 레이어는 아직 생성되지 않았다.

### Document ETL

- `excel_workbooks`
- `excel_sheets`
- `pdf_documents`
- `pdf_pages`
- `pdf_page_features`
- `pdf_extraction_runs`
- `pdf_layout_families`
- `pdf_layout_assignments`
- `extracted_metrics`

현재 상태:

- PDF 관련 확장 테이블은 스키마와 DB 인스턴스 양쪽에 모두 반영됨
- PDF 문서 472건 중 470건은 `done`, 2건은 사용자 승인 하에 `skipped`
- `extracted_metrics` 는 현재 PDF 1차 추출값 2476건으로 채워짐

## PDF 처리 구조

PDF는 "고정 컬럼 보고서 테이블"이 아니라 "원문 + 분류 + provenance + 추출값" 구조로 다뤄야 한다.

현재 파이프라인은 아래 흐름을 따른다.

1. 문서 단위 등록: `pdf_documents`
2. 페이지 텍스트/표 적재: `pdf_pages`
3. 페이지 feature 적재: `pdf_page_features`
4. run 단위 추적: `pdf_extraction_runs`
5. layout family 분류: `pdf_layout_assignments`
6. 1차 metric 추출: `extracted_metrics`

지원 중인 family:

- `report_legacy_crashworthiness`
- `report_modern_small_overlap_v7`
- `report_modern_small_overlap_v8`
- `report_iihs_generic`
- `edr_bosch_cdr`
- `edr_hyundai_g_edr`
- `edr_restraint_control_module`
- `edr_generic`

이 구조 덕분에 시험소/연도별 PDF 양식이 달라도 DB 자체를 다시 갈아엎지 않고 extractor만 점진적으로 고도화할 수 있다.

## 왜 이 구조가 맞는가

### 레거시와 최신 세대를 같이 담을 수 있다

- 레거시 DAS는 `BIN`, `TLF`, `LOG`, `tdas.ini` 중심이다.
- 중간 세대는 `DIAdem` 과 Excel이 강하다.
- 최신 ROI 계열은 `TDMS + DTS + CHN` 조합이 강하다.

하나의 파서 전략으로 모든 연도를 통일하려 하면 실패한다. 카탈로그 DB는 세대별로 다른 적재 경로를 허용해야 한다.

### 재현성과 확장성이 같이 확보된다

- 다운로드 인벤토리와 연구용 DB를 분리했기 때문에 원본 손상 없이 재적재가 가능하다.
- Excel/PDF/파형 ETL은 각자 독립적으로 확장할 수 있다.
- 향후 PostgreSQL 또는 DuckDB 쪽으로 확장하더라도 현재 카탈로그 설계는 그대로 재사용 가능하다.

## 빌드 및 재빌드 절차

분석 중간 산출물 생성:

```powershell
D:\vscode\IIHS_SOL\.venv\Scripts\python.exe D:\vscode\IIHS_SOL\scripts\extract_dataset_metadata.py --manifest data/index/manifest.sqlite --raw-root data/raw --output-dir data/analysis
```

연구용 DB 생성:

```powershell
D:\vscode\IIHS_SOL\.venv\Scripts\python.exe D:\vscode\IIHS_SOL\scripts\init_research_database.py --manifest data/index/manifest.sqlite --analysis-dir data/analysis --schema sql/research_database.sql --output-db data/research/research.sqlite
```

PDF ETL 실행:

```powershell
D:\vscode\IIHS_SOL\.venv\Scripts\python.exe D:\vscode\IIHS_SOL\scripts\process_pdfs.py --all
```

실무 규칙:

- 스키마가 바뀌면 DB 인스턴스가 실제로 따라왔는지 바로 확인한다.
- 원시 파일 경로는 가능한 한 상대적 구조를 유지하고, DB에는 실제 로컬 경로를 함께 저장한다.
- 사용자 승인 없이 `data/raw` 입력 자산을 덮어쓰지 않는다.

## 다음 구현해야 할 ETL

1. Excel ETL
   - `excel_sheets` 채우기
   - intrusion, UMTRI, summary, environmental 시트 정규화
   - 핵심 수치 `extracted_metrics` 적재
2. TDMS to Parquet
   - `signal_series` 채우기
   - 채널별 Parquet 경로와 기본 통계 등록
3. Legacy DAS deep parse
   - 필요 범위에 한해 `BIN`, `TLF`, 일부 `CHN` 보강

## 빠른 검증 질문

이 구조가 유지되면 아래 질문에 즉시 답할 수 있어야 한다.

- 어떤 테스트가 `TDMS` 를 갖는가
- 어떤 차량과 연식이 `EDR` 자산을 갖는가
- 어떤 filegroup이 `DTS` 기반 센서 카탈로그를 갖는가
- Excel ETL과 PDF ETL 중 어느 쪽이 완료 상태인가
- 어떤 파형 컨테이너가 아직 `Parquet` 시리즈로 정규화되지 않았는가
