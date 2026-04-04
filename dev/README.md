# 개발 문서

Band Managing 개발 참조 문서.

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Nuxt 3 · Vue 3 · TypeScript · SCSS |
| Backend | Python 3.12 · FastAPI · SQLAlchemy |
| Database | PostgreSQL 16 |
| Crawler | Python · YouTube Data API v3 |
| Infra | Docker Compose · Nginx · AWS Lightsail |
| CI/CD | GitHub Actions |

## 문서 구조

| 폴더 | 설명 |
|------|------|
| [architecture/](./architecture/) | 시스템 아키텍처, 데이터 모델 |
| [api/](./api/) | 백엔드 API 설계 |
| [web/](./web/) | 프론트엔드 설계 |
| [crawler/](./crawler/) | 크롤링 봇 설계 |

## 테스트

```bash
cd api
DATABASE_URL=sqlite:///./test.db pytest tests/ -v
```

45개 테스트: songs(15), contis(10), admin(9), crawler(11)
