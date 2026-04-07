# 크롤링 봇 설계

유튜브에서 CCM/찬양곡 데이터를 수집하는 봇. `api/crawler.py`에 구현.

## 현재 구현

### 수집 방식
- **YouTube Data API v3** 사용
- `playlistItems` API로 채널 업로드 재생목록(UU...) 조회
- `videos` API로 duration + snippet 조회

### 파이프라인 — 단곡 크롤링 (`crawl_channel`)
```
채널 등록 (관리자, URL만 입력)
  ↓ URL → @handle → UC... 자동 변환 (channels API)
크롤링 실행 (수동 트리거 / cron)
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
제목 파싱 (parse_song_title)
  ↓ [대괄호], (Official), | 뒤 등 제거
  ↓ 사역팀 이름 제거 (마커스워십, 어노인팅 등)
  ↓ 인도자 표기 제거: (소진영 인도) / - 심종호 인도
  ↓ 한글 제목 + 영문 부제 → 영문 부제 제거 (Holy God 등)
  ↓ 키 정보 추출 (Key: G / 키: G / G장조)
곡 매칭
  ├─ DB에 같은 곡 있음 → 레퍼런스 추가
  │     + description에서 가사/악보 링크 추출 → song.lyrics / SongSheet 보강
  │     + ref.key 외에 song.keys[]에도 누적 (default_key 보존)
  └─ 없음 → 검증 큐 등록 (유사곡 후보 자동 표시)
```

### 파이프라인 — 세트리스트 크롤링 (`crawl_setlists`)
예배 실황(60분 이상) 영상의 description에서 타임스탬프+곡명+키를 자동 추출.
```
대상 채널의 긴 영상(>10분, 예배 키워드 매칭) 수집
  ↓ description의 라인별 SETLIST_TIMESTAMP 매칭
  ↓ 각 라인에서 SETLIST_KEY 추출 (괄호/파이프/대시/장조)
  ↓ 키 추출 실패한 라인은 스킵 (보수적)
곡 매칭 (find_matching_song)
  ├─ 매칭 성공 → song.keys[] 누적 (default_key 보존)
  └─ 매칭 실패 → 새 Song 자동 등록 (source=CRAWLED, default_key=key)
타임스탬프 레퍼런스 생성
  ↓ youtube_video_id = "{video_id}@{ts_seconds}" (UNIQUE 회피용 합성 키)
  ↓ youtube_url     = "...&t={ts_seconds}s"
  ↓ 중복 가드 후 SongReference INSERT
```
세트리스트 모드는 검증 큐를 거치지 않고 자동 등록한다 (description이 곡 목록 자체이므로).

### 필터링 규칙
- **시간**: 60초 이하(Shorts) 무시, 10분(600초) 초과 무시
- **키워드 제외**: inst, instrumental, 연주, MR, 반주, AR, 드럼캠, 기타캠, 베이스캠, making, shorts, teaser, interview, 예배실황, 주일예배, 설교
- **합쳐진 곡**: +, &, medley, 메들리, 모음, 연속 듣기, playlist, worship set
- **DB 추가 키워드**: 관리자가 `/api/admin/filter-keywords`로 동적 추가 가능

### 제목 파싱 예시
```
"거룩 영원히 (Holy Forever) - 마커스워십 𝑳𝒊𝒗𝒆 𝑪𝒍𝒊𝒑"
  → "거룩 영원히"
"이 세상에 근심된 일이 많고 - 소진영 인도 | 마커스워십 | The haven rest"
  → "이 세상에 근심된 일이 많고"
"마커스워십 - 이와 같은 때엔 (소진영 인도) In moments like these"
  → "이와 같은 때엔"
"구원의 반석 (심종호 인도) Blessed be the rock"
  → "구원의 반석"
"Holy Forever"  → "Holy Forever"  (한글 없으면 영문 보존)
```

처리 단계: STRIP_PATTERNS → 팀 이름 제거 → 인도자 메타 제거 →
끝 대시 정리 → (한글 있을 때) 영문 부제 제거 → 따옴표/공백 정리.

제거 대상 팀 이름: 마커스워십, 어노인팅, 아이자야씩스티원, 위러브, 잔치공동체, 피아워십, 기프티드, 사운드오브워십, 예람워십, CIY, CGN

### Description 보강 파서
- `parse_setlist_description` — 타임스탬프 라인을 [{title, key, ts_seconds}]로 반환
- `parse_lyrics_from_description` — '가사:' 마커 또는 휴리스틱(한글 비율/줄 수/평균 길이)으로 가사 블록 추출
- `parse_sheet_urls` — 도메인/경로/같은 줄 키워드 기반 악보 링크 추출 (drive.google, dropbox, mssaint, .pdf 등)
- `_augment_song_keys` — 중복 없이 keys[]에 누적, default_key가 비어있을 때만 set

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
