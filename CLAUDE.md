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

### 인증/권한
- JWT 인증 (아이디/비번), 역할: ADMIN / MEMBER
- 읽기 API는 공개 (콘티 공유 링크 지원)
- 곡 등록: 관리자 → 정식곡(MANUAL), 일반유저 → 임시곡(USER, user_id 연결)
- 곡 목록: 정식곡 + 본인 임시곡만 표시
- 곡 삭제/병합: 관리자만
- 콘티: 본인 콘티만 표시 (user_id 필터)

### 코드 컨벤션
- API: FastAPI 라우터, SQLAlchemy ORM, Pydantic 스키마
- Web: `<script setup lang="ts">`, Composition API, file-based routing
- 스타일: SCSS (tokens + base + mixins), 다크 테마 기반
- 테스트: pytest + SQLite in-memory, TestClient

### 배포
- `main` push → GitHub Actions → Lightsail SSH → `docker compose up -d --build --force-recreate`
- Nginx reload 후 헬스 체크
- 헬스 체크: `GET /health`

### 의존성 변경 시 필수 확인
push 전에 반드시 이 세션에서 호환성 테스트:
```bash
# 1. 의존성 설치 테스트
pip install -r api/requirements.txt

# 2. import + 핵심 기능 동작 확인
python -c "from passlib.context import CryptContext; ..."
python -c "from jose import jwt; ..."

# 3. 테스트 실행
DATABASE_URL=sqlite:///./test.db pytest tests/ -v
```
- passlib 1.7.4 + bcrypt는 반드시 bcrypt<5.0.0 (4.2.1 고정)
- python-jose[cryptography]는 cffi 빌드 필요 (Dockerfile에 gcc, libffi-dev)
- 새 패키지 추가 시 Dockerfile 빌드 의존성도 확인

### push 전 필수 체크리스트
1. **백엔드 테스트**: `DATABASE_URL=sqlite:///./test.db pytest tests/ -v` 전체 통과
2. **의존성 호환성**: 새 패키지 추가 시 pip install + import 테스트
3. **프론트엔드 확인**: 모든 페이지의 API 호출에 에러 처리(catch) 있는지
4. **모바일 레이아웃**: 네비, 폼, 카드가 640px 이하에서 깨지지 않는지
5. **API 에러 전파**: load() 함수에서 하나의 API 실패가 전체를 멈추지 않는지
6. **인증 흐름**: 로그인 필요한 페이지가 미인증 시 /login으로 리다이렉트 되는지

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
