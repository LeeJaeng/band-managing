# CLAUDE.md

이 파일은 Claude Code가 프로젝트 작업 시 참조하는 핵심 규약입니다.

## 프로젝트 개요

교회 찬양팀 운영 관리 서비스. 곡 DB + 콘티 작성 + 크롤링 봇.

## 핵심 가치

- 콘티 작성이 핵심 — 곡 검색~키 설정(키업 포함)~레퍼런스 확인까지 한 곳에서 해결
- 콘티 공유 — 텍스트 복사(카톡/밴드) 또는 링크 공유로 팀원에게 전달
- 크롤링 봇으로 곡 데이터 자동 수집 (유튜브 기반)
- 관리자의 모든 수동 작업은 API 기반 → 추후 자동화 전환 가능

## 기술 스택

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL 16
- **Frontend**: Nuxt 3, Vue 3, TypeScript, SCSS, pnpm
- **Crawler**: Python (YouTube Data API v3, playlistItems API)
- **Infra**: Docker Compose, Nginx, AWS Lightsail
- **CI/CD**: GitHub Actions (main push → 자동 배포)

## 핵심 규칙

### 설계 원칙
- 크롤러는 API를 통해 DB에 접근 (직접 DB 접근 X)
- 관리자 기능은 모두 REST API로 노출 (자동화 대비)
- JWT 인증 (아이디/비번), 역할: ADMIN / MEMBER
- 읽기 API는 공개 (콘티 공유 링크 지원)

### 코드 컨벤션
- API: FastAPI 라우터, SQLAlchemy ORM, Pydantic 스키마
- Web: `<script setup lang="ts">`, Composition API, file-based routing
- 스타일: SCSS (tokens + base + mixins), 다크 테마 기반
- 테스트: pytest + SQLite in-memory, TestClient

### 배포
- `main` push → GitHub Actions → Lightsail SSH → `docker compose up -d --build --force-recreate`
- Nginx reload 후 헬스 체크
- 헬스 체크: `GET /health`

### DB
- PostgreSQL 16, 연결: 환경변수 `DATABASE_URL`
- ORM: SQLAlchemy, 모델: `api/models.py`
- 테이블: songs, song_references, song_sheets, contis, conti_items, conti_members, crawl_channels, crawl_logs, review_queue, users, team_members
- 마이그레이션: `api/main.py`의 `MIGRATIONS` 리스트에 ALTER TABLE 추가 (앱 시작 시 자동 실행)

### 크롤링
- YouTube Data API v3 (playlistItems + videos)
- 채널 업로드 재생목록(UU...)에서 영상 수집
- 10분 초과 영상 무시, 예배실황/연주/inst/MR 등 필터링
- 곡 합쳐진 영상 필터 (+, &, 메들리, 모음, worship set)
- 곡 제목에서 사역팀 이름 자동 제거
- @handle → UC... 채널 ID 자동 변환
- 곡 매칭: 제목 유사도 → 매칭되면 레퍼런스 추가, 안 되면 검증 큐

### 캐시
- Nginx: HTML은 no-cache, /_nuxt/ 에셋은 immutable (해시 기반)
- 프론트 API 호출 시 timestamp 쿼리로 캐시 방지

## 테스트

```bash
cd api
DATABASE_URL=sqlite:///./test.db pytest tests/ -v
```

테스트 (songs, contis, admin, crawler, auth, team)

## 문서 참조

- [ops/](./ops/) — 기획/운영 (서비스 개념, MVP 정의, 콘티/곡DB/관리자 상세)
- [dev/](./dev/) — 개발 (아키텍처, 데이터 모델, API, 프론트, 크롤러)
