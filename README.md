# Band Managing

교회 찬양팀 운영 관리 서비스.

곡 DB 자동 수집(크롤링) + 콘티 작성을 한 곳에서.

## 핵심 기능

- **곡 DB** — 유튜브 크롤링으로 CCM/찬양곡 자동 수집 (제목, 레퍼런스, 키, 가사)
- **콘티 작성** — 곡 검색 → 선택 → 순서 배치, 한 화면에서 콘티 완성
- **관리자** — 크롤링 채널 관리, 곡 DB 관리, 검증 큐

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Nuxt 3 · Vue 3 · TypeScript · SCSS |
| Backend | Python · FastAPI · SQLAlchemy |
| Database | PostgreSQL 16 |
| Crawler | Python · YouTube Data API |
| Infra | Docker Compose · Nginx · AWS Lightsail |
| CI/CD | GitHub Actions |

## 프로젝트 구조

```
band-managing/
├── api/           # FastAPI 백엔드 (예정)
├── web/           # Nuxt 3 프론트엔드 (예정)
├── crawler/       # 크롤링 봇 (예정)
├── infra-ref/     # 기존 인프라 설정 참조
├── dev/           # 개발 참조 문서
├── ops/           # 기획/운영 문서
└── .github/       # CI/CD
```

## 문서

- [CLAUDE.md](./CLAUDE.md) — 프로젝트 규약
- [ops/](./ops/) — 기획 문서 (서비스 개념, MVP, 콘티, 곡DB, 관리자)
- [dev/](./dev/) — 개발 문서 (아키텍처, 데이터 모델, API, 크롤러)

## 인프라

- **배포**: AWS Lightsail + GitHub Actions (main push → 자동 배포)
- **서버 경로**: `/home/ubuntu/band-managing/`
- **기존 설정 참조**: `infra-ref/`
