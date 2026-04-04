# 프론트엔드 설계

Nuxt 3 기반 웹 애플리케이션.

## 파일 구조

```
web/
├── app.vue                        # 루트 (네비게이션 바 + NuxtPage)
├── pages/
│   ├── index.vue                  # / — 콘티 목록
│   ├── conti/
│   │   ├── new.vue                # /conti/new — 새 콘티
│   │   └── [id].vue               # /conti/:id — 콘티 편집
│   ├── songs/
│   │   ├── index.vue              # /songs — 곡 DB
│   │   ├── new.vue                # /songs/new — 곡 등록
│   │   └── [id].vue               # /songs/:id — 곡 상세/편집
│   └── admin/
│       └── index.vue              # /admin — 관리자 대시보드
├── composables/
│   └── useApi.ts                  # API 호출 헬퍼
├── assets/scss/
│   ├── main.scss                  # 엔트리
│   ├── _tokens.scss               # CSS 변수 (다크 테마)
│   ├── _base.scss                 # 기본 스타일
│   └── _mixins.scss               # card, btn, input 믹스인
├── nuxt.config.ts
├── package.json
└── Dockerfile
```

## 페이지 상세

### `/` — 콘티 목록
- 전체 콘티 목록 (날짜, 예배명, 작성자, 상태)
- [새 콘티 만들기] → /conti/new

### `/conti/:id` — 콘티 편집
- 곡 목록 표시 (순서, 키, 레퍼런스, 메모)
- 곡 DB에서 검색 → 추가
- 곡 삭제, 콘티 확정

### `/songs` — 곡 DB
- 곡 검색 (제목/가사)
- 레퍼런스 수 표시
- [곡 등록] → /songs/new
- 곡 삭제

### `/songs/:id` — 곡 상세
- 키 복수 표시
- 레퍼런스 목록 (추가/삭제, 유튜브 링크)
- 레퍼런스별 악보
- 가사/송폼
- [편집] → 키 칩 선택, 가사 편집

### `/songs/new` — 곡 등록
- 제목, 기본 키, 가사
- 레퍼런스 복수 추가 (유튜브 URL + 키)

### `/admin` — 관리자
- 채널 관리 (URL 입력 → 자동 ID 변환)
- 크롤링 실행/로그
- 검증 큐 (유사곡 후보, 매칭/새곡/거부)
