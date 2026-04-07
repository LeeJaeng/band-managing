# API 설계

Python FastAPI 백엔드. 모든 기능은 REST API로 노출.

## 파일 구조

```
api/
├── main.py              # FastAPI 앱, lifespan, 헬스체크
├── models.py            # SQLAlchemy ORM 모델 (8 테이블)
├── db.py                # DB 엔진, 세션 팩토리
├── crawler.py           # 유튜브 크롤링 모듈
├── routers/
│   ├── songs.py         # 곡/레퍼런스/악보 CRUD
│   ├── contis.py        # 콘티/항목 CRUD
│   └── admin.py         # 채널 관리, 크롤링, 검증큐
├── tests/
│   ├── conftest.py      # SQLite 테스트 DB 설정
│   ├── test_songs.py    # 곡 CRUD 테스트 (15개)
│   ├── test_contis.py   # 콘티 테스트 (10개)
│   ├── test_admin.py    # 관리자 테스트 (9개)
│   └── test_crawler.py  # 크롤러 단위 테스트 (11개)
├── requirements.txt
└── Dockerfile
```

## API 엔드포인트

### 헬스체크
```
GET /health → { ok, service }
```

### 공개 (/api)
```
GET    /api/channels                    채널(팀) 목록 (곡 필터용, 인증 불필요)
```

### 곡 (/api/songs)
```
GET    /api/songs?q=&limit=&offset=&key_filter=&no_key=&tempo=&no_tempo=&channel_id=&source=
                                        곡 목록 (검색, 키/빠르기/채널/소스 필터,
                                        refs_by_team[] = [{channel_id,channel_name,count}] 포함)
GET    /api/songs/:id                   곡 상세 (refs, sheets, keys 포함)
POST   /api/songs                       곡 등록
PUT    /api/songs/:id                   곡 수정 (title, keys[], lyrics, tempo)
DELETE /api/songs/:id                   곡 삭제 (FK 정리)
```

### 레퍼런스 (/api/songs/:id/references)
```
GET    /api/songs/:id/references        레퍼런스 목록
POST   /api/songs/:id/references        레퍼런스 추가
PUT    /api/songs/references/:id        레퍼런스 수정
DELETE /api/songs/references/:id        레퍼런스 삭제
```

### 악보 (/api/songs/:id/sheets)
```
GET    /api/songs/:id/sheets            악보 목록
POST   /api/songs/:id/sheets            악보 업로드
DELETE /api/songs/sheets/:id            악보 삭제
```

### 콘티 (/api/contis)
```
GET    /api/contis                      콘티 목록
GET    /api/contis/:id                  콘티 상세 (항목+곡+레퍼런스)
POST   /api/contis                      콘티 생성
PUT    /api/contis/:id                  콘티 수정
DELETE /api/contis/:id                  콘티 삭제
PUT    /api/contis/:id/confirm          콘티 확정
POST   /api/contis/:id/items            항목 추가
PUT    /api/contis/items/:id            항목 수정
DELETE /api/contis/items/:id            항목 삭제
PUT    /api/contis/:id/reorder          항목 순서 변경
```

### 관리자 (/api/admin)
```
GET    /api/admin/channels              채널 목록
POST   /api/admin/channels              채널 등록
PUT    /api/admin/channels/:id          채널 수정
DELETE /api/admin/channels/:id          채널 삭제 (FK 정리)
GET    /api/admin/channels/resolve-id   @handle → UC... 변환
POST   /api/admin/crawl/:channel_id     개별 크롤링 (단곡 영상)
POST   /api/admin/crawl/all             전체 크롤링
POST   /api/admin/crawl-setlists/:channel_id  세트리스트 크롤링 (예배 실황 description 파싱)
POST   /api/admin/crawl-setlists/all    전체 채널 세트리스트 크롤링
GET    /api/admin/crawl/logs            크롤링 로그
DELETE /api/admin/crawl/reset           크롤링 + 곡 데이터 전체 삭제 (TRUNCATE)

GET    /api/admin/review-queue          검증 큐 (유사곡 후보 포함, 페이지네이션 10개)
GET    /api/admin/review-queue/export   검증 큐 전체 내보내기 (JSON)
POST   /api/admin/review/reparse-titles PENDING 항목의 parsed_song_title을 현재 parser로 재계산
POST   /api/admin/review/auto-approve   자동 승인 (블랙리스트/문장형 휴리스틱 통과 항목)
POST   /api/admin/review/batch          일괄 처리 (approve/reject ids 배열)
POST   /api/admin/review/:id/approve    개별 승인 (기존곡 매칭 or 새곡)
POST   /api/admin/review/:id/reject     개별 거부

GET    /api/admin/songs/duplicate-candidates  중복 곡 후보 그룹 (정확/접두 정규화 일치)
POST   /api/admin/songs/merge           곡 병합 (source_ids[] + target_id, target_title 옵션)
POST   /api/admin/songs/bulk-update     선택 곡 일괄 수정 (키 추가, tempo 설정)

GET    /api/admin/filter-keywords       크롤링 필터 키워드 목록
POST   /api/admin/filter-keywords       키워드 추가
DELETE /api/admin/filter-keywords/:id   키워드 삭제
```
