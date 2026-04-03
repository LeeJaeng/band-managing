# 아키텍처

## 전체 구조

모노레포 + Docker Compose 기반 풀스택 애플리케이션.

```
[Browser] → [Nginx :80]
                ├── /api/*  → [FastAPI :8000] → [PostgreSQL :5432]
                ├── /ws     → [FastAPI :8000] (WebSocket)
                └── /*      → [Nuxt SSR :3000]
```

## 컨테이너 구성

| 서비스 | 이미지 | 포트 | 역할 |
|--------|--------|------|------|
| nginx | nginx:alpine | 80 (공개) | 리버스 프록시, 라우팅 |
| web | Nuxt 3 (커스텀) | 3000 (내부) | SSR 프론트엔드 |
| api | FastAPI (커스텀) | 8000 (내부) | REST API + WebSocket |
| db | postgres:16-alpine | 5432 (내부) | 데이터 저장 |

## 통신 흐름

### REST API
```
클라이언트 → Nginx(/api/*) → FastAPI → SQLAlchemy → PostgreSQL
```

### WebSocket (실시간)
```
클라이언트 → Nginx(/ws) → FastAPI ws_hub → 연결된 모든 클라이언트
```

### 상태 관리
```
클라이언트 상태: Vue ref() + localStorage (composables)
서버 상태: PostgreSQL (SQLAlchemy ORM)
실시간 동기화: WebSocket 이벤트
```

## 관련 문서

- [데이터 모델](./data-model.md)
