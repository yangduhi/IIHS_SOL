# 메모리 정책 및 현재 메모

## 작성 규칙
- 허용 타입은 `Decision`, `Assumption`, `Invariant`, `Open Issue`만 사용한다.
- 개인정보, 비밀번호, 인증 토큰은 기록하지 않는다.
- 한 줄 형식만 사용한다.
  `[type] YYYY-MM-DD | scope | content | source`

## 현재 메모
[Decision] 2026-03-06 | auth/session | Playwright CLI persistent profile and storage-state are the canonical reusable session artifacts. | docs/field-notes.md
[Decision] 2026-03-06 | discovery/routes | Driver-side uses `t=25` and passenger-side uses `t=26` on `secure/filegroups.aspx`. | docs/field-notes.md
[Invariant] 2026-03-06 | downloads/auth | `/secure/file.ashx?...` requires authenticated cookies; unauthenticated requests redirect to `/`. | docs/field-notes.md
[Decision] 2026-03-06 | rss | Public RSS endpoint is `https://techdata.iihs.org/rss.ashx`, but historical backfill must not depend on RSS alone. | docs/field-notes.md
[Open Issue] 2026-03-06 | discovery/indexer | Historical crawler for all pages of `t=25` and `t=26` is not implemented yet. | user
[Open Issue] 2026-03-06 | downloader | Folder traversal and file manifest persistence are not implemented yet. | user
