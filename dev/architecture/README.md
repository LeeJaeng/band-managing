# 아키텍처

## 시스템 구성

```
[Browser] → [Nginx :80]
                ├── /api/*     → [FastAPI :8000] → [PostgreSQL :5432]
                ├── /admin/*   → [Nuxt :3000]    (관리자 페이지)
                └── /*         → [Nuxt :3000]    (사용자 페이지)

[Crawler Bot] → [FastAPI :8000] → [PostgreSQL :5432]
     ↑
  (스케줄러 또는 수동 트리거)
```

## 컨테이너 구성 (예정)

| 서비스 | 역할 |
|--------|------|
| nginx | 리버스 프록시 |
| web | Nuxt 3 SSR (사용자 + 관리자) |
| api | FastAPI (REST API) |
| db | PostgreSQL 16 |
| crawler | 크롤링 봇 (워커) |

## 핵심 모듈

### API (FastAPI)
- 곡 CRUD
- 레퍼런스 CRUD
- 콘티 CRUD
- 관리자 기능 (채널 관리, 크롤링 제어)
- 모든 관리 동작은 API로 노출 (자동화 대비)

### Web (Nuxt 3)
- 콘티 작성/조회 페이지
- 곡 검색/상세 페이지
- 관리자 대시보드

### Crawler
- 유튜브 채널 영상 수집
- 곡 제목 파싱, 곡 매칭
- API를 통해 DB에 저장 (직접 DB 접근 X → 자동화 대비)

## 관련 문서

- [데이터 모델](./data-model.md)
