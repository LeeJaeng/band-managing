# CLAUDE.md

이 파일은 Claude Code가 프로젝트 작업 시 참조하는 핵심 규약입니다.

## 프로젝트 개요

교회 밴드 실시간 운영 관리 시스템. 모노레포 구조 (api + web + nginx).

## 디렉토리 구조

- `api/` — Python FastAPI 백엔드
- `web/` — Nuxt 3 (Vue 3 + TypeScript) 프론트엔드
- `nginx/` — 리버스 프록시 설정
- `dev/` — 개발 참조 문서
- `ops/` — 기획/운영 문서

## 기술 스택 요약

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL 16
- **Frontend**: Nuxt 3, Vue 3, TypeScript, SCSS, pnpm
- **Infra**: Docker Compose, Nginx, AWS Lightsail
- **CI/CD**: GitHub Actions (main push → 자동 배포)

## 핵심 규칙

### 코드 컨벤션
- **API**: Python, FastAPI 라우터 패턴, SQLAlchemy ORM
- **Web**: `<script setup lang="ts">`, Composition API, Nuxt file-based routing
- **스타일**: SCSS (tokens + base + mixins 구조), 다크 테마 기반

### 브랜치 전략
- `main` — 프로덕션 (push 시 자동 배포)
- 기능 개발은 별도 브랜치에서 진행 후 main에 머지

### 배포
- `main`에 push하면 GitHub Actions가 Lightsail에 SSH 접속 → `docker compose up -d --build`
- 헬스 체크: `GET /api/health`

### DB
- PostgreSQL 16, 연결 문자열: 환경변수 `DATABASE_URL`
- ORM: SQLAlchemy, 모델 정의: `api/models.py`
- 기본 파트: 보컬, 피아노, 신디, 기타, 베이스, 드럼, 리더, 설교자, 음향, 영상

### 실시간 통신
- WebSocket 경로: `/ws`
- Nginx에서 프록시 (24시간 타임아웃)
- 메시지 타입: JOIN_SESSION, JOINED, USER_JOINED, BROADCAST, PERMISSION_UPDATED, PRESETS_UPDATED, ERROR

### 인증/권한
- 세션 참가 기반 (JWT/OAuth 없음)
- LEADER: 첫 입장자 자동 부여, 브로드캐스트 항상 가능, 권한/프리셋 관리
- MEMBER: 권한 부여 시에만 브로드캐스트 가능

## 로컬 개발

```bash
# 전체 실행
docker compose up -d --build

# API만
cd api && uvicorn main:app --reload --port 8000

# Web만
cd web && pnpm dev
```

## 문서 참조

- [dev/](./dev/) — 개발 상세 문서
- [ops/](./ops/) — 기획/운영 문서
