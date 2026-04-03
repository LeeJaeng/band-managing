# Band Managing

교회 밴드 실시간 운영 관리 시스템.  
세션(방)을 만들고, 밴드 멤버들에게 실시간으로 메시지를 브로드캐스트할 수 있는 웹 애플리케이션입니다.

## 주요 기능

- **세션 관리** — 방 생성, 참여자 입장, 파트 지정
- **실시간 브로드캐스트** — WebSocket 기반 메시지 전달 (텍스트 오버레이)
- **역할/권한** — LEADER(방장) / MEMBER 역할 분리, 브로드캐스트 권한 관리
- **프리셋** — 자주 사용하는 메시지 템플릿 저장 및 빠른 전송
- **파트 커스터마이징** — 보컬, 피아노, 기타, 드럼 등 세션별 파트 설정

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Nuxt 3 · Vue 3 · TypeScript · SCSS |
| Backend | Python · FastAPI · SQLAlchemy |
| Database | PostgreSQL 16 |
| Realtime | WebSocket |
| Infra | Docker Compose · Nginx |
| Deploy | AWS Lightsail · GitHub Actions |

## 프로젝트 구조

```
band-managing/
├── api/           # FastAPI 백엔드
├── web/           # Nuxt 3 프론트엔드
├── nginx/         # 리버스 프록시 설정
├── .github/       # CI/CD (GitHub Actions)
├── dev/           # 개발 참조 문서
├── ops/           # 기획/운영 문서
└── docker-compose.yml
```

## 빠른 시작

### 요구사항
- Docker & Docker Compose

### 실행

```bash
docker compose up -d --build
```

브라우저에서 `http://localhost` 접속.

### 개별 개발 서버

**API** (Python)
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Web** (Nuxt)
```bash
cd web
pnpm install
pnpm dev
```

## 문서

- [CLAUDE.md](./CLAUDE.md) — 프로젝트 규약 및 핵심 규칙
- [dev/](./dev/) — 개발 참조 문서 (아키텍처, API, 프론트엔드, 인프라)
- [ops/](./ops/) — 기획 및 운영 문서
