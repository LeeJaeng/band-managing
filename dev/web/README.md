# 프론트엔드 설계

Nuxt 3 기반 웹 애플리케이션.

## 페이지 구조 (예정)

### 사용자 페이지
```
/                           홈 (콘티 목록)
/conti/new                  새 콘티 작성
/conti/:id                  콘티 상세/편집
/songs                      곡 검색/탐색
/songs/:id                  곡 상세 (레퍼런스, 가사, 악보)
```

### 관리자 페이지
```
/admin                      관리자 대시보드
/admin/songs                곡 DB 관리
/admin/songs/:id            곡 상세 편집
/admin/channels             크롤링 채널 관리
/admin/crawl                크롤링 상태/로그
/admin/review               검증 큐
```

## UI 방향

- 모바일 우선 (찬양팀원들이 폰/태블릿으로 접근)
- 콘티 작성 시 곡 검색이 핵심 UX
- 다크 테마 기반 (기존 스타일 참고)
