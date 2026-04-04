# 개발 문서

Band Managing 개발 참조 문서.

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Nuxt 3 · Vue 3 · TypeScript · SCSS |
| Backend | Python · FastAPI · SQLAlchemy |
| Database | PostgreSQL 16 |
| Crawler | Python (유튜브 데이터 수집) |
| Infra | Docker Compose · Nginx · AWS Lightsail |
| CI/CD | GitHub Actions |

## 문서 구조

| 폴더 | 설명 |
|------|------|
| [architecture/](./architecture/) | 시스템 아키텍처, 데이터 모델 |
| [api/](./api/) | 백엔드 API 설계 |
| [web/](./web/) | 프론트엔드 설계 |
| [crawler/](./crawler/) | 크롤링 봇 설계 |

## 인프라 참조

기존 인프라 설정은 `infra-ref/`에 보관되어 있음.
- Docker Compose, Nginx, Dockerfile 등
- 새 프로젝트에 맞게 재구성 예정
