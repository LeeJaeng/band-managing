# 크롤링 봇 설계

유튜브에서 CCM/찬양곡 데이터를 수집하는 봇. `api/crawler.py`에 구현.

## 현재 구현

### 수집 방식
- **YouTube Data API v3** 사용
- `playlistItems` API로 채널 업로드 재생목록(UU...) 조회
- `videos` API로 duration + snippet 조회

### 파이프라인
```
채널 등록 (관리자, URL만 입력)
  ↓ URL → @handle → UC... 자동 변환 (channels API)
크롤링 실행 (수동 트리거)
  ↓ playlistItems로 영상 ID 수집 (페이지 제한 없음, 채널 전체)
  ↓ 이미 수집된 영상 만나면 조기 종료 (증분 수집, 최신순)
  ↓ videos로 duration + snippet 조회
필터링
  ↓ 60초 이하 → Shorts로 간주, 무시
  ↓ 10분(600초) 초과 → 무시
  ↓ 예배실황/연주/inst/MR 등 → 무시
  ↓ 곡 합쳐진 영상 (+, 메들리 등) → 무시
  ↓ DB 등록 추가 필터 키워드 → 무시
  ↓ 이미 수집된 영상 → 스킵
제목 파싱
  ↓ [대괄호], (Official), | 뒤 등 제거
  ↓ 사역팀 이름 제거 (마커스워십, 어노인팅 등)
  ↓ 키 정보 추출 (Key: G 등)
곡 매칭
  ├─ DB에 같은 곡 있음 → 레퍼런스 추가
  └─ 없음 → 검증 큐 등록 (유사곡 후보 자동 표시)
```

### 필터링 규칙
- **시간**: 60초 이하(Shorts) 무시, 10분(600초) 초과 무시
- **키워드 제외**: inst, instrumental, 연주, MR, 반주, AR, 드럼캠, 기타캠, 베이스캠, making, shorts, teaser, interview, 예배실황, 주일예배, 설교
- **합쳐진 곡**: +, &, medley, 메들리, 모음, 연속 듣기, playlist, worship set
- **DB 추가 키워드**: 관리자가 `/api/admin/filter-keywords`로 동적 추가 가능

### 제목 파싱 (팀 이름 제거)
```
입력: "거룩 영원히 (Holy Forever) - 마커스워십 𝑳𝒊𝒗𝒆 𝑪𝒍𝒊𝒑"
1단계: 패턴 제거 → "거룩 영원히 (Holy Forever) - 마커스워십"
2단계: 팀 이름 제거 → "거룩 영원히 (Holy Forever)"
3단계: 정리 → "거룩 영원히 (Holy Forever)"
```

제거 대상 팀 이름: 마커스워십, 어노인팅, 아이자야씩스티원, 위러브, 잔치공동체, 피아워십, 기프티드, 사운드오브워십, 예람워십, CIY, CGN

### 크롤링 우선 사역팀
- 마커스워십, 어노인팅, 아이자야씩스티원, 위러브
- 잔치공동체, 피아워십, 기프티드

### API 사용량
- playlistItems: 1 unit/호출 (50개씩, 페이지 제한 없음 → 채널 전체, 증분 수집으로 조기 종료)
- videos: 1 unit/호출 (50개씩 배치)
- channels: 1 unit (채널 ID 변환)
- 일일 무료 할당량: 10,000 units

### 에러 처리
- 크롤링 실패 시 DB rollback 후 별도 실패 로그 기록
- API 레벨에서도 예외 catch → 500 대신 에러 메시지 반환
- 프론트에서 alert으로 결과/에러 표시

### DB 마이그레이션
- `api/main.py`의 `MIGRATIONS` 리스트
- 앱 시작 시 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 자동 실행
- 새 컬럼 추가 시 이 리스트에 SQL 추가
