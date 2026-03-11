# Step 13. 운영 규칙, 알려진 함정, 인계 메모

이 단계는 코드를 더 쓰는 단계가 아니라, 프로젝트를 안정적으로 운영하기 위한 마감 단계다.

## 운영 순서 표준안

매번 아래 순서로 실행한다.

1. 인증 세션 유효성 확인
2. 필요하면 `capture-session.ps1` 재실행
3. `npm run discover`
4. `node .\scripts\download-filegroup.mjs --pending --limit=소량`로 스모크 체크
5. 문제 없으면 `npm run download:pending`

## 현재 저장소에서 실제 확인된 함정

### 1. 세션은 영구적이지 않다

실제 로그에서 중간에 `Authenticated session is no longer valid.`가 반복적으로 발생했다.  
따라서 대량 실행 시 세션 재확보 절차가 필수다.

### 2. `PHOTOS` 범위는 최종 완료 상태 기준 제외로 확정됐다

현재 확인된 사실은 다음과 같다.

- 과거 성공 산출물에는 `PHOTOS`가 존재한다.
- 최종 `manifest.sqlite`에는 `photo-folder`, `photo-extension` 제외가 기록돼 있다.
- 현재 `data/raw`에는 `PHOTOS` 디렉터리가 남아 있지 않다.

인계 기준:

- "현재 성공적으로 내려받고 있는 시스템"을 재현하려면 `PHOTOS 제외, VIDEO 제외`를 기준으로 삼는다.
- 과거 중간 산출물의 흔적은 참고 정보일 뿐, 재구축 기준은 최종 완성 상태다.

### 3. RSS 증분 동기화는 아직 구현되지 않았다

기존 상위 문서에는 RSS 계획이 있지만, 현재 저장소에는 `sync-rss.mjs`가 없다.  
빈 폴더 재구축 지시서도 여기서는 discovery + download까지만 완성 범위로 본다.

### 4. root 폴더 파일을 잊기 쉽다

실제 로그에서 `info.txt`, `README.txt`, `TestEnvironmentalData.csv`가 root에 존재한다.  
`DATA`, `REPORTS`만 있다고 가정해도 root 파일을 놓치면 누락이 생긴다.

### 5. 최종 완료 상태에서도 예외 2건은 별도 관리가 필요하다

현재 최종 스냅샷 기준:

- filegroup `2344`의 `CEN1438 Driver Door`는 `HTTP 400`
- filegroup `7961`의 `5A65DF20`도 `HTTP 400`

따라서 완료 판정은 "상식적인 재시도 후에도 사이트가 직접 실패시키는 파일은 예외로 문서화" 기준을 포함해야 한다.

### 6. zero-byte 파일을 무조건 오류로 보면 안 된다

현재 최종 스냅샷 기준:

- filegroup `1726`의 `ROOT\TestEnvironmentalData.csv`는 원본 `size_label`이 `0 bytes`다.

즉, 검증은 "zero-byte 없음"이 아니라 "허용되지 않은 zero-byte 없음"이어야 한다.

## 새 담당자에게 넘길 때 같이 전달할 것

- 현재 단계 문서 폴더 전체
- 현재 확인된 type code 25/26 정보
- IIHS 계정 발급/승인 절차
- 자격증명 보관 방식
- 인증 만료 시 재실행 절차
- 데이터 적재 위치와 백업 정책

## 최소 인수인계 체크리스트

- 새 담당자가 `capture-session.ps1`를 직접 실행할 수 있다.
- 새 담당자가 `npm run discover`를 실행할 수 있다.
- 새 담당자가 단건 다운로드를 재현할 수 있다.
- 새 담당자가 인증 만료 로그를 보고 복구할 수 있다.
- 새 담당자가 `manifest.sqlite`를 질의해 상태를 확인할 수 있다.

## 다음 확장 작업 후보

현재 시스템과 동일성 유지가 끝난 뒤에만 검토한다.

- `sync-rss.mjs` 구현
- rate limit 및 backoff
- 장기 실행용 lock file
- 주기 스케줄러
- 사이트 `HTTP 400` 파일에 대한 대체 다운로드 경로 조사

## 최종 메모

이 프로젝트의 핵심은 "스크립트 자체"보다 "인증 세션 유지 + ASP.NET postback 처리 + manifest 일관성"이다.  
빈 폴더에서 재구축할 때도 이 세 가지를 먼저 만족시키면, 나머지 세부 구현은 안정적으로 따라온다.
