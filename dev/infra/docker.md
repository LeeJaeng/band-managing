# Docker 구성

## docker-compose.yml

4개 서비스로 구성된 단일 Docker Compose 스택.

```
nginx (:80) ─┬─ web (:3000)  Nuxt SSR
              └─ api (:8000)  FastAPI ──── db (:5432)  PostgreSQL
```

### nginx
- 이미지: `nginx:alpine`
- 역할: 리버스 프록시
- 라우팅: `/api/*` → api, `/ws` → api (WebSocket), `/*` → web
- 설정: `nginx/default.conf`

### web
- 빌드: `web/Dockerfile` (Node 22 Alpine, pnpm)
- 역할: Nuxt 3 SSR 서버
- 포트: 3000 (내부)

### api
- 빌드: `api/Dockerfile` (Python 3.12 slim)
- 역할: FastAPI + WebSocket
- 포트: 8000 (내부)
- 환경변수: `DATABASE_URL`

### db
- 이미지: `postgres:16-alpine`
- 볼륨: `pgdata` (영구 데이터)
- 환경변수: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

## Nginx 설정 (nginx/default.conf)

```
/api/*  → proxy_pass http://api:8000
/ws     → proxy_pass http://api:8000/ws (WebSocket 업그레이드)
/*      → proxy_pass http://web:3000
```

WebSocket 타임아웃: 86,400초 (24시간)
