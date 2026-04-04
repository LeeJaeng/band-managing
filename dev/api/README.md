# API 설계

Python FastAPI 백엔드. 모든 기능은 REST API로 노출.

## 설계 원칙

- 관리자 기능 포함 모든 동작을 API로 제공 (자동화 대비)
- 크롤러도 API를 통해 DB에 접근 (직접 DB 접근 X)
- MVP에서는 인증 없음, 추후 회원가입 시 인증 레이어 추가

## API 그룹

### 곡 (Songs)
```
GET    /api/songs                    곡 목록 (검색, 필터)
GET    /api/songs/:id                곡 상세 (레퍼런스, 악보 포함)
POST   /api/songs                    곡 등록
PUT    /api/songs/:id                곡 수정
DELETE /api/songs/:id                곡 삭제
POST   /api/songs/merge              곡 병합 (중복 처리)
```

### 레퍼런스 (References)
```
GET    /api/songs/:id/references     곡의 레퍼런스 목록
POST   /api/songs/:id/references     레퍼런스 추가
PUT    /api/references/:id           레퍼런스 수정
DELETE /api/references/:id           레퍼런스 삭제
```

### 악보 (Sheets)
```
GET    /api/songs/:id/sheets         곡의 악보 목록
POST   /api/songs/:id/sheets         악보 업로드
DELETE /api/sheets/:id               악보 삭제
```

### 콘티 (Contis)
```
GET    /api/contis                   콘티 목록
GET    /api/contis/:id               콘티 상세 (항목 포함)
POST   /api/contis                   콘티 생성
PUT    /api/contis/:id               콘티 수정
DELETE /api/contis/:id               콘티 삭제
PUT    /api/contis/:id/confirm       콘티 확정
```

### 콘티 항목 (Conti Items)
```
POST   /api/contis/:id/items         항목 추가
PUT    /api/conti-items/:id          항목 수정 (키, 메모, 레퍼런스 변경)
DELETE /api/conti-items/:id          항목 삭제
PUT    /api/contis/:id/reorder       항목 순서 변경
```

### 크롤링 관리 (Admin - Crawl)
```
GET    /api/admin/channels           채널 목록
POST   /api/admin/channels           채널 등록
PUT    /api/admin/channels/:id       채널 수정
DELETE /api/admin/channels/:id       채널 삭제
POST   /api/admin/crawl/:channel_id  특정 채널 크롤링 실행
POST   /api/admin/crawl/all          전체 크롤링 실행
GET    /api/admin/crawl/logs         크롤링 로그 조회
```

### 검증 큐 (Admin - Review)
```
GET    /api/admin/review-queue       검증 대기 목록
POST   /api/admin/review/:id/approve 승인 (곡 매칭 확정)
POST   /api/admin/review/:id/reject  거부 (삭제)
```

### 헬스 체크
```
GET    /api/health                   서비스 상태
```
