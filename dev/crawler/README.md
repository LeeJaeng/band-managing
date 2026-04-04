# 크롤링 봇 설계

유튜브에서 CCM/찬양곡 데이터를 수집하는 봇. `api/crawler.py`에 구현.

## 현재 구현

### 수집 방식
- **YouTube Data API v3** 사용
- `playlistItems` API로 채널 업로드 재생목록(UU...) 조회 (search API 대비 안정적, quota 절약)
- `videos` API로 duration 확인

### 파이프라인
```
채널 등록 (관리자)
  ↓ URL → @handle → UC... 자동 변환
크롤링 실행 (수동)
  ↓ playlistItems로 영상 ID 수집 (최대 250개)
  ↓ videos로 duration + snippet 조회
필터링
  ↓ 20분 초과 → 무시
  ↓ 예배실황/연주/inst/MR 등 → 무시
  ↓ 이미 수집된 영상 → 스킵
제목 파싱
  ↓ [대괄호], (Official), | 뒤 등 제거
  ↓ 키 정보 추출 (Key: G 등)
곡 매칭
  ├─ DB에 같은 곡 있음 → 레퍼런스 추가
  └─ 없음 → 검증 큐 등록
```

### 필터링 규칙
- **시간**: 20분(1200초) 초과 무시
- **키워드 제외**: inst, instrumental, 연주, MR, 반주, AR, 드럼캠, 기타캠, 베이스캠, making, shorts, teaser, interview, 예배실황, 주일예배, 설교

### 제목 파싱
```
입력: "[마커스 4집] 주만 바라볼찌라 | 마커스워십 (Official)"
제거: [대괄호], | 뒤 텍스트, (Official)
결과: "주만 바라볼찌라"
```

### API 사용량
- playlistItems: 1 unit/호출 (50개씩, 최대 5페이지 = 5 units)
- videos: 1 unit/호출 (50개씩 배치)
- channels: 1 unit (채널 ID 변환)
- 일일 무료 할당량: 10,000 units
