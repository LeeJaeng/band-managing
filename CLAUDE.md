# CLAUDE.md

이 파일은 Claude Code가 프로젝트 작업 시 참조하는 핵심 규약입니다.

## 프로젝트 개요

교회 찬양팀 운영 관리 서비스. 곡 DB + 콘티 작성 + 크롤링 봇.

## 핵심 가치

- 인도자가 콘티를 짤 때 곡 검색~레퍼런스 확인까지 한 곳에서 해결
- 크롤링 봇으로 곡 데이터 자동 수집 (유튜브 기반)
- 관리자의 모든 수동 작업은 API 기반 → 추후 자동화 전환 가능

## 기술 스택

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL 16
- **Frontend**: Nuxt 3, Vue 3, TypeScript, SCSS, pnpm
- **Crawler**: Python (YouTube Data API)
- **Infra**: Docker Compose, Nginx, AWS Lightsail
- **CI/CD**: GitHub Actions (main push → 자동 배포)

## 핵심 규칙

### 설계 원칙
- 크롤러는 API를 통해 DB에 접근 (직접 DB 접근 X)
- 관리자 기능은 모두 REST API로 노출 (자동화 대비)
- MVP에서는 인증 없음, 추후 회원가입 시 추가

### 코드 컨벤션
- API: FastAPI 라우터, SQLAlchemy ORM
- Web: `<script setup lang="ts">`, Composition API, file-based routing
- 스타일: SCSS, 모바일 우선, 다크 테마 기반

### 배포
- `main` push → GitHub Actions → Lightsail SSH → `docker compose up -d --build`
- 헬스 체크: `GET /api/health`

## 문서 참조

- [ops/](./ops/) — 기획/운영 (서비스 개념, MVP 정의, 콘티/곡DB/관리자 상세)
- [dev/](./dev/) — 개발 (아키텍처, 데이터 모델, API, 프론트, 크롤러)
