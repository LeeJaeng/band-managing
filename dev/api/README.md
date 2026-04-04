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

### 곡 (/api/songs)
```
GET    /api/songs?q=&limit=&offset=     곡 목록 (검색, ref_count 포함)
GET    /api/songs/:id                   곡 상세 (refs, sheets, keys 포함)
POST   /api/songs                       곡 등록
PUT    /api/songs/:id                   곡 수정 (title, keys[], lyrics)
DELETE /api/songs/:id                   곡 삭제 (FK 정리)
POST   /api/songs/merge?source_id&target_id  곡 병합
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
POST   /api/admin/crawl/:channel_id     개별 크롤링
POST   /api/admin/crawl/all             전체 크롤링
GET    /api/admin/crawl/logs            크롤링 로그
GET    /api/admin/review-queue          검증 큐 (유사곡 후보 포함)
POST   /api/admin/review/:id/approve    승인 (기존곡 매칭 or 새곡)
POST   /api/admin/review/:id/reject     거부
```
