# Web (Frontend)

Nuxt 3 기반 프론트엔드. `web/` 디렉토리에 위치.

## 파일 구조

```
web/
├── app/
│   └── app.vue                 # 루트 컴포넌트
├── pages/
│   ├── index.vue               # / — 방 생성
│   ├── join.vue                # /join — 방 입장
│   └── session/
│       └── [id].vue            # /session/:id — 세션 메인
├── composables/
│   ├── useWs.ts                # WebSocket 연결 관리
│   ├── useSessionState.ts      # localStorage 상태 관리
│   └── useClipboard.ts         # 클립보드 유틸
├── assets/scss/
│   ├── main.scss               # 엔트리 (imports)
│   ├── _tokens.scss            # 디자인 토큰 (CSS 변수)
│   ├── _base.scss              # 기본 스타일
│   └── _mixins.scss            # 재사용 믹스인 (card, panel, btn, input)
├── nuxt.config.ts
├── package.json
└── Dockerfile
```

## 실행

```bash
cd web
pnpm install
pnpm dev          # http://localhost:3000
```

## 관련 문서

- [페이지 구조](./pages.md)
- [컴포저블](./composables.md)
