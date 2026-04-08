"""유튜브 채널 크롤링 모듈.

MVP에서는 YouTube Data API v3를 사용.
API 키가 없으면 mock/스킵 처리.
"""

import os
import re
from datetime import datetime

from sqlalchemy.orm import Session

from models import (
    CrawlChannel,
    CrawlLog,
    CrawlFilterKeyword,
    ReviewQueue,
    Song,
    SongReference,
    SongSheet,
)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# 영상 제목에서 제거할 패턴들
STRIP_PATTERNS = [
    r"\[.*?\]",           # [마커스 4집]
    r"\(Official.*?\)",   # (Official Video)
    r"\(Live.*?\)",       # (Live)
    r"\(MV\)",
    r"\(lyrics?\)",
    r"official\s*(m/?v|video|audio)",
    r"live\s*worship",
    r"lyrics?\s*video",
    r"\|.*$",             # | 뒤의 모든 텍스트
    r"-\s*\d{4}.*$",      # - 2024 라이브
    r"𝑳𝒊𝒗𝒆\s*𝑪𝒍𝒊𝒑",    # Live Clip (스타일 폰트)
    r"live\s*clip",
]

# 제목에서 제거할 사역팀 이름들
TEAM_NAMES = [
    "마커스워십", "마커스 워십", "markers worship", "markersworship",
    "어노인팅", "anointing",
    "아이자야씩스티원", "isaiah 61", "isaiah61",
    "위러브", "welove", "we love",
    "잔치공동체", "잔치 공동체",
    "피아워십", "pia worship", "piaworship",
    "기프티드", "gifted",
    "사운드오브워십", "sound of worship",
    "예람워십", "yeram worship",
    "ciy", "cgn",
]

# 키 감지 패턴 — 영어/한국어 키워드 + 장조/단조
KEY_PATTERN = re.compile(
    r"(?:keys?|키|코드)\s*[:\-]?\s*([A-G][#b\u266d\u266f]?m?)(?![a-zA-Z])"
    r"|\b([A-G][#b]?)\s*(?:장조|단조)",
    re.IGNORECASE,
)

# 세트리스트(예배 실황) 감지 — 긴 영상 중 어떤 것에서 description 파싱할지 판단
WORSHIP_VIDEO_KEYWORDS = [
    "예배", "worship", "목요", "주일", "thursday", "sunday",
    "라이브", "live", "집회", "service", "찬양집회",
]

# "00:00 곡명" / "1:23:45 곡명" — 줄 시작 타임스탬프
SETLIST_TIMESTAMP = re.compile(r"^\s*[\[\(]?(\d{1,2}:\d{2}(?::\d{2})?)[\]\)]?\s+(.+?)\s*$")

# 라인 안 어디에서나 키 추출 — (Key: G) / | key Am / (G) / G장조 / "곡 - Am"
SETLIST_KEY = re.compile(
    r"(?:\bkeys?|키|코드)\s*[:\-]?\s*([A-G][#b\u266d\u266f]?m?)(?![a-zA-Z])"
    r"|[\(\[]\s*([A-G][#b\u266d\u266f]?m?)\s*[\)\]]"
    r"|\b([A-G][#b]?)\s*(?:장조|단조)"
    r"|[\|\-–—]\s*([A-G][#b\u266d\u266f]?m?)\s*$",
    re.IGNORECASE,
)

# URL 추출
URL_PATTERN = re.compile(r"https?://[^\s\)\]\>\"']+", re.IGNORECASE)

# 악보 링크 휴리스틱: 도메인/경로/파일명에 이런 토큰이 있으면 악보 후보
SHEET_URL_HINTS = [
    "sheet", "sheetmusic", "악보", "praise", "chord", "score",
    "mssaint", "mss", "musicgroups", "praisecho",
]
SHEET_DRIVE_HOSTS = [
    "drive.google.com/file", "drive.google.com/open",
    "dropbox.com/s", "1drv.ms",
]
# 악보 링크와 같은 줄에 있어야 추가 인정되는 키워드
SHEET_LINE_KEYWORDS = ["악보", "sheet", "chord chart", "코드", "score", "lead sheet"]

# 가사 마커 — 이 라인 이후를 가사 블록으로 인식
LYRICS_MARKERS = re.compile(
    r"^\s*(?:\[?\s*(?:가사|lyrics?)\s*\]?\s*[:\-]?\s*)$",
    re.IGNORECASE,
)

# 긴 영상 제외 키워드 (예배 실황 등)
SKIP_KEYWORDS = [
    "예배 실황", "예배실황", "full worship", "전체 예배",
    "sunday service", "주일예배", "주일 예배",
    "예배 영상", "worship service",
    "설교", "sermon", "말씀",
]

# 제외할 영상 키워드 (연주/인스트/MR 등)
SKIP_TYPE_KEYWORDS = [
    "inst", "instrumental", "연주", "mr", "반주",
    "ar", "accompaniment", "karaoke", "노래방",
    "drum cam", "드럼캠", "bass cam", "베이스캠",
    "guitar cam", "기타캠",
    "making", "메이킹", "behind", "비하인드",
    "interview", "인터뷰",
    "teaser", "trailer", "예고",
    "shorts",
]

# 영상 길이 제한 (초)
MAX_DURATION_SECONDS = 600   # 10분 초과 무시
MIN_DURATION_SECONDS = 61    # 60초 이하는 Shorts로 간주하고 무시

# 곡 두 개 이상 합쳐진 영상 감지 패턴
MULTI_SONG_PATTERNS = [
    r"\+",                # A곡 + B곡
    r"\&",                # A곡 & B곡
    r"medley",            # 메들리
    r"메들리",
    r"모음",              # 찬양 모음
    r"연속\s*듣기",
    r"playlist",
    r"worship\s*set",
]


def parse_song_title(video_title: str) -> str:
    """영상 제목에서 곡 제목을 추출."""
    title = video_title.strip()
    # 선두 번호 매기기 제거: "1.", "10.", "1)", "1.RE_" — 셋다 점/괄호가 있어야 안전
    title = re.sub(r"^\s*\d{1,2}\s*[.)]\s*(?:[A-Z]+_)?\s*", "", title)
    for pattern in STRIP_PATTERNS:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)
    # 사역팀 이름 제거
    for team in TEAM_NAMES:
        title = re.sub(re.escape(team), "", title, flags=re.IGNORECASE)
    # 인도자 표기 제거: (소진영 인도) / (심종호 인도) / [김선락 인도] 등
    title = re.sub(r"\s*[\(\[（][^)\]）]*인도[^)\]）]*[\)\]）]\s*", " ", title)
    # 대시로 이어진 인도자 표기 제거: " - 소진영 인도" / "- 인도: 김선락"
    title = re.sub(r"\s*[-–—]\s*[^-–—|()\[\]]*?인도\b[^-–—|()\[\]]*", " ", title)
    # 끝에 매달린 대시/구분자 정리 (다음 단계의 영어 부제 제거가 잘 동작하도록)
    title = re.sub(r"\s*[-–—|·]+\s*$", "", title)
    # 언더스코어를 공백으로 정규화 (한글_영문 같은 패턴이 부제 분리 패턴을 회피하는 문제 방지)
    title = title.replace("_", " ")
    # 한글 제목 + 영어 부제 → 한글만 유지
    # 예: "구원의 반석 Blessed be the rock" → "구원의 반석"
    #     "거룩 영원히 (Holy Forever)"     → "거룩 영원히"
    #     "우물가의 여인처럼 (Fill my cup, Lord)" → "우물가의 여인처럼"
    if re.search(r"[가-힣]", title):
        # 1) 끝의 영어를 포함한 괄호 부제 (콤마/구두점 가능): "(Fill my cup, Lord)"
        title = re.sub(r"\s*\([^)]*[A-Za-z][^)]*\)\s*$", "", title)
        # 2) 끝의 단순 영어 부제: "Holy Forever" / "Psalm 139" / "Where Jesus is, 'tis heaven"
        # 첫 단어는 최소 2글자 이상이어야 함 (단일 문자 "A"가 잘못 떼이는 것 방지)
        title = re.sub(
            r"\s*\(?\s*[A-Za-z]{2,}[A-Za-z\d\s'’&,.]*\)?\s*$",
            "",
            title,
        ).strip()
    # " - " 뒤에 남은 텍스트 제거 (보통 팀 이름이 뒤에 붙음)
    title = re.sub(r"\s*-\s*$", "", title)
    # 따옴표, 특수 유니코드 문자 제거
    title = re.sub(r'["\u201c\u201d\u2018\u2019\u300c\u300d\u300e\u300f\uff02]', '', title)
    # 다중 공백 정리
    title = re.sub(r"\s+", " ", title)
    # 앞뒤 공백/특수문자 정리
    title = title.strip(" -–—·|,.'\"")
    return title if title else video_title.strip()


def _normalize_key(raw: str) -> str:
    """유니코드 ♭/♯을 b/#으로 정규화."""
    return raw.replace("\u266d", "b").replace("\u266f", "#").strip()


def detect_key(text: str) -> str | None:
    """텍스트에서 키 정보를 추출."""
    match = KEY_PATTERN.search(text)
    if not match:
        return None
    for grp in match.groups():
        if grp:
            return _normalize_key(grp)
    return None


def should_skip_video(title: str, extra_keywords: list[str] | None = None) -> bool:
    """예배 실황, 연주, inst, 합쳐진 곡 등 스킵해야 할 영상인지 확인."""
    lower = title.lower()
    for kw in SKIP_KEYWORDS:
        if kw.lower() in lower:
            return True
    for kw in SKIP_TYPE_KEYWORDS:
        if kw.lower() in lower:
            return True
    for kw in (extra_keywords or []):
        if kw.lower() in lower:
            return True
    # 곡 두 개 이상 합쳐진 영상
    for pattern in MULTI_SONG_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return True
    return False


def _parse_duration(duration_str: str) -> int:
    """ISO 8601 duration (PT1H2M3S) → 초 변환."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def find_matching_song(parsed_title: str, db: Session) -> Song | None:
    """DB에서 제목이 유사한 곡을 찾기 (정확 매칭 우선)."""
    exact = db.query(Song).filter(Song.title == parsed_title).first()
    if exact:
        return exact
    like = db.query(Song).filter(Song.title.ilike(f"%{parsed_title}%")).first()
    return like


# ── 세트리스트 / description 보강 파서 ──────────────────────

def _ts_to_seconds(ts: str) -> int:
    """'1:23:45' / '05:30' → 초."""
    parts = [int(p) for p in ts.split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return 0


def _strip_setlist_title(raw: str, key_match: re.Match | None) -> str:
    """세트리스트 라인에서 키 표기를 제거하고 곡명만 남긴다."""
    title = raw
    if key_match:
        title = title.replace(key_match.group(0), "")
    # 키 제거 후 남은 빈 괄호 정리: "주님 찾아오셨네 ()" → "주님 찾아오셨네"
    title = re.sub(r"[\(\[]\s*[\)\]]", "", title)
    # 끝부분 구분자 정리
    title = re.sub(r"\s*[\|\-–—:·,/]\s*$", "", title)
    # 일반 곡 제목 정리(번호/팀명/인도자/영문부제) 재사용 — 언더스코어 정규화는 parse_song_title 내부에서 처리
    title = parse_song_title(title)
    return title


def parse_setlist_description(description: str) -> list[dict]:
    """description에서 [{title, key, ts_seconds}] 추출. 키가 없는 라인은 제외."""
    if not description:
        return []
    results: list[dict] = []
    seen_titles: set[str] = set()
    for line in description.splitlines():
        m = SETLIST_TIMESTAMP.match(line)
        if not m:
            continue
        ts, rest = m.group(1), m.group(2)
        key_match = SETLIST_KEY.search(rest)
        if not key_match:
            continue
        key = None
        for grp in key_match.groups():
            if grp:
                key = _normalize_key(grp)
                break
        if not key:
            continue
        title = _strip_setlist_title(rest, key_match)
        if not title or len(title) < 2:
            continue
        # 중복 제거
        dedup_key = title.lower()
        if dedup_key in seen_titles:
            continue
        seen_titles.add(dedup_key)
        results.append({
            "title": title,
            "key": key,
            "ts_seconds": _ts_to_seconds(ts),
        })
    return results


def _augment_song_keys(song: Song, key: str) -> bool:
    """song.keys 리스트에 key를 중복 없이 추가. default_key가 null이면 같이 set.

    반환: 변경 발생 여부.
    """
    if not key:
        return False
    changed = False
    existing = list(song.keys or [])
    if key not in existing:
        existing.append(key)
        song.keys = existing
        changed = True
    if not song.default_key:
        song.default_key = key
        changed = True
    return changed


def parse_lyrics_from_description(desc: str) -> str | None:
    """description에서 가사 블록을 추출.

    1) 명시 마커('가사', 'Lyrics') 라인 이후 → 빈 줄 2개 또는 URL 만나기 전까지
    2) 마커 없으면 fallback: 한글 비율 ≥ 0.5, 줄 수 ≥ 6, 평균 줄 길이 ≤ 40 인 블록
    3) 길이 40자 미만이면 None
    """
    if not desc:
        return None

    lines = desc.splitlines()

    def _collect_block(start: int) -> str:
        block: list[str] = []
        blank_streak = 0
        for line in lines[start:]:
            if URL_PATTERN.search(line):
                break
            if not line.strip():
                blank_streak += 1
                if blank_streak >= 2:
                    break
                if block:
                    block.append("")
                continue
            blank_streak = 0
            block.append(line.rstrip())
        return "\n".join(block).strip()

    # 1) 명시 마커
    for i, line in enumerate(lines):
        if LYRICS_MARKERS.match(line):
            text = _collect_block(i + 1)
            if len(text) >= 40:
                return text

    # 2) 휴리스틱: 가장 큰 한글 블록을 추정
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if not line.strip() or URL_PATTERN.search(line) or SETLIST_TIMESTAMP.match(line):
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line.rstrip())
    if current:
        blocks.append(current)

    best: tuple[int, str] | None = None
    for block in blocks:
        if len(block) < 6:
            continue
        text = "\n".join(block)
        korean = sum(1 for ch in text if "\uac00" <= ch <= "\ud7a3")
        non_space = sum(1 for ch in text if not ch.isspace())
        if non_space == 0 or korean / non_space < 0.5:
            continue
        avg_len = sum(len(line) for line in block) / len(block)
        if avg_len > 40:
            continue
        if len(text) < 40:
            continue
        if best is None or len(text) > best[0]:
            best = (len(text), text)

    return best[1] if best else None


def parse_sheet_urls(desc: str) -> list[str]:
    """description에서 악보 링크 후보 URL을 추출 (휴리스틱)."""
    if not desc:
        return []
    found: list[str] = []
    for line in desc.splitlines():
        line_lower = line.lower()
        line_has_keyword = any(kw in line_lower for kw in SHEET_LINE_KEYWORDS)
        for url in URL_PATTERN.findall(line):
            url_clean = url.rstrip(".,;)]")
            url_lower = url_clean.lower()
            looks_like_sheet = (
                url_lower.endswith(".pdf")
                or any(h in url_lower for h in SHEET_URL_HINTS)
            )
            looks_like_drive = any(h in url_lower for h in SHEET_DRIVE_HOSTS)
            if looks_like_sheet or (looks_like_drive and line_has_keyword) or (line_has_keyword and url_lower.startswith("http")):
                if url_clean not in found:
                    found.append(url_clean)
                if len(found) >= 5:
                    return found
    return found


def _sheet_file_type(url: str) -> str:
    lower = url.lower()
    if lower.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
        return "IMAGE"
    return "PDF"


def _add_sheet(db: Session, song: Song, reference: SongReference | None, file_url: str) -> bool:
    """SongSheet 생성. 동일 (song_id, file_url) 존재하면 skip."""
    exists = db.query(SongSheet).filter(
        SongSheet.song_id == song.id,
        SongSheet.file_url == file_url,
    ).first()
    if exists:
        return False
    sheet = SongSheet(
        song_id=song.id,
        reference_id=reference.id if reference else None,
        file_url=file_url,
        file_type=_sheet_file_type(file_url),
        uploaded_by="crawler",
    )
    db.add(sheet)
    return True


def _resolve_channel_id(youtube, channel_id_or_handle: str) -> str:
    """@handle이나 커스텀 URL을 실제 채널 ID (UC...)로 변환."""
    if channel_id_or_handle.startswith("UC"):
        return channel_id_or_handle

    # @handle인 경우
    handle = channel_id_or_handle.lstrip("@")
    resp = youtube.channels().list(
        part="id",
        forHandle=handle,
    ).execute()

    items = resp.get("items", [])
    if items:
        return items[0]["id"]

    # forUsername으로도 시도
    resp = youtube.channels().list(
        part="id",
        forUsername=handle,
    ).execute()
    items = resp.get("items", [])
    if items:
        return items[0]["id"]

    raise ValueError(f"채널을 찾을 수 없습니다: {channel_id_or_handle}")


def _fetch_channel_videos(channel_id_or_handle: str, known_video_ids: set[str] | None = None) -> list[dict]:
    """YouTube Data API로 채널의 영상 목록을 가져온다.
    known_video_ids가 주어지면, 이미 수집된 영상을 만나면 조기 종료."""
    if not YOUTUBE_API_KEY:
        return []

    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # @handle → UC... 변환
    resolved_id = _resolve_channel_id(youtube, channel_id_or_handle)

    # 업로드 재생목록 ID: UC... → UU...
    uploads_playlist_id = "UU" + resolved_id[2:]

    # 1단계: playlistItems로 영상 ID 목록 수집 (최신순)
    video_ids = []
    next_page = None
    stop_early = False

    while True:  # 페이지 제한 없이 전체 수집
        req = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="contentDetails",
            maxResults=50,
            pageToken=next_page,
        )
        resp = req.execute()

        for item in resp.get("items", []):
            vid = item["contentDetails"]["videoId"]
            # 이미 수집된 영상이면 여기서 멈춤 (최신순이니까 이후는 다 수집됨)
            if known_video_ids and vid in known_video_ids:
                stop_early = True
                break
            video_ids.append(vid)

        if stop_early:
            break

        next_page = resp.get("nextPageToken")
        if not next_page:
            break

    if not video_ids:
        return []

    # 2단계: videos로 duration 정보 가져오기 (50개씩 배치)
    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        detail_resp = youtube.videos().list(
            part="snippet,contentDetails",
            id=",".join(batch),
        ).execute()

        for item in detail_resp.get("items", []):
            duration = _parse_duration(item["contentDetails"]["duration"])

            # 10분 초과 영상 무시
            if duration > MAX_DURATION_SECONDS:
                continue
            # Shorts (60초 이하) 무시
            if duration < MIN_DURATION_SECONDS:
                continue

            snippet = item["snippet"]
            title = snippet["title"]

            # 예배 실황 키워드 무시
            if should_skip_video(title):
                continue

            videos.append({
                "video_id": item["id"],
                "title": title,
                "description": snippet.get("description", ""),
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url", ""),
                "published_at": snippet["publishedAt"],
                "duration": duration,
            })

    return videos


def _fetch_worship_videos(channel_id_or_handle: str, max_results: int = 10) -> list[dict]:
    """예배 실황 영상(긴 영상 + 예배 키워드)만 수집해 description 포함 반환."""
    if not YOUTUBE_API_KEY:
        return []

    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    resolved_id = _resolve_channel_id(youtube, channel_id_or_handle)
    uploads_playlist_id = "UU" + resolved_id[2:]

    # 1단계: 영상 ID 후보 수집 (최신순) — quota 절약 위해 일정 개수 모이면 중단
    video_ids: list[str] = []
    next_page = None
    while len(video_ids) < max_results * 5:  # 후보를 넉넉히
        req = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="contentDetails",
            maxResults=50,
            pageToken=next_page,
        )
        resp = req.execute()
        for item in resp.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
        next_page = resp.get("nextPageToken")
        if not next_page:
            break

    if not video_ids:
        return []

    videos: list[dict] = []
    for i in range(0, len(video_ids), 50):
        if len(videos) >= max_results:
            break
        batch = video_ids[i:i+50]
        detail_resp = youtube.videos().list(
            part="snippet,contentDetails",
            id=",".join(batch),
        ).execute()
        for item in detail_resp.get("items", []):
            duration = _parse_duration(item["contentDetails"]["duration"])
            # 예배 실황은 보통 30분 이상이지만 보수적으로 MAX_DURATION 초과만 받음
            if duration <= MAX_DURATION_SECONDS:
                continue
            snippet = item["snippet"]
            title = snippet["title"]
            lower = title.lower()
            if not any(kw.lower() in lower for kw in WORSHIP_VIDEO_KEYWORDS):
                continue
            videos.append({
                "video_id": item["id"],
                "title": title,
                "description": snippet.get("description", ""),
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url", ""),
                "published_at": snippet["publishedAt"],
                "duration": duration,
            })
            if len(videos) >= max_results:
                break

    return videos


def crawl_setlists(channel: CrawlChannel, db: Session, max_videos: int = 10) -> dict:
    """예배 실황 영상의 description에서 세트리스트를 추출해 곡 DB / 레퍼런스 보강."""
    log = CrawlLog(
        channel_id=channel.id,
        status="RUNNING",
        started_at=datetime.utcnow(),
    )
    db.add(log)
    db.flush()

    try:
        videos = _fetch_worship_videos(channel.youtube_channel_id, max_results=max_videos)
        log.videos_found = len(videos)

        songs_created = 0
        keys_added = 0

        for video in videos:
            entries = parse_setlist_description(video["description"])
            if not entries:
                continue

            for entry in entries:
                title = entry["title"]
                key = entry["key"]

                song = find_matching_song(title, db)
                if song is None:
                    song = Song(
                        title=title,
                        source="CRAWLED",
                        default_key=key,
                        keys=[key],
                    )
                    db.add(song)
                    db.flush()
                    songs_created += 1
                else:
                    if _augment_song_keys(song, key):
                        keys_added += 1

        log.songs_added = songs_created
        log.refs_added = 0
        log.status = "SUCCESS"
        log.finished_at = datetime.utcnow()
        channel.last_crawled_at = datetime.utcnow()
        db.commit()

        return {
            "channel_id": channel.id,
            "channel_name": channel.name,
            "status": "SUCCESS",
            "videos_scanned": log.videos_found,
            "songs_created": songs_created,
            "keys_added": keys_added,
        }
    except Exception as e:
        try:
            db.rollback()
            fail_log = CrawlLog(
                channel_id=channel.id,
                status="FAILED",
                error_message=str(e),
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
            )
            db.add(fail_log)
            db.commit()
        except Exception:
            db.rollback()
        return {
            "channel_id": channel.id,
            "channel_name": channel.name,
            "status": "FAILED",
            "error": str(e),
        }


def crawl_channel(channel: CrawlChannel, db: Session) -> dict:
    """단일 채널 크롤링 실행."""
    log = CrawlLog(
        channel_id=channel.id,
        status="RUNNING",
        started_at=datetime.utcnow(),
    )
    db.add(log)
    db.flush()

    try:
        # 이미 수집된 영상 ID 목록 (레퍼런스 + 검증 큐)
        existing_refs = {r.youtube_video_id for r in
            db.query(SongReference.youtube_video_id).filter(SongReference.channel_id == channel.id).all()}
        existing_reviews = {r.youtube_video_id for r in
            db.query(ReviewQueue.youtube_video_id).filter(ReviewQueue.channel_id == channel.id).all()}
        known_ids = existing_refs | existing_reviews

        videos = _fetch_channel_videos(channel.youtube_channel_id, known_video_ids=known_ids)
        log.videos_found = len(videos)

        # DB에 등록된 추가 필터 키워드 로드
        extra_keywords = [r.keyword for r in db.query(CrawlFilterKeyword).all()]

        songs_added = 0
        refs_added = 0

        for video in videos:
            # 이미 수집된 영상인지 확인
            existing_ref = db.query(SongReference).filter(
                SongReference.youtube_video_id == video["video_id"]
            ).first()
            if existing_ref:
                continue

            existing_review = db.query(ReviewQueue).filter(
                ReviewQueue.youtube_video_id == video["video_id"]
            ).first()
            if existing_review:
                continue

            # DB 추가 필터 키워드 체크
            if extra_keywords and should_skip_video(video["title"], extra_keywords):
                continue

            parsed_title = parse_song_title(video["title"])
            detected_key = detect_key(video["title"] + " " + video["description"])
            matching_song = find_matching_song(parsed_title, db)

            if matching_song:
                ref = SongReference(
                    song_id=matching_song.id,
                    channel_id=channel.id,
                    youtube_url=f"https://www.youtube.com/watch?v={video['video_id']}",
                    youtube_video_id=video["video_id"],
                    title=video["title"],
                    thumbnail_url=video["thumbnail"],
                    key=detected_key,
                    trust_level=channel.trust_level,
                    source="CRAWL",
                )
                db.add(ref)
                db.flush()  # ref.id 확보 (SongSheet 연결용)
                refs_added += 1

                # ── description 보강: 키 / 가사 / 악보 ──
                if detected_key:
                    _augment_song_keys(matching_song, detected_key)

                lyrics = parse_lyrics_from_description(video["description"])
                if lyrics and not matching_song.lyrics:
                    matching_song.lyrics = lyrics

                for sheet_url in parse_sheet_urls(video["description"]):
                    _add_sheet(db, matching_song, ref, sheet_url)
            else:
                rq = ReviewQueue(
                    youtube_video_id=video["video_id"],
                    youtube_url=f"https://www.youtube.com/watch?v={video['video_id']}",
                    video_title=video["title"],
                    channel_id=channel.id,
                    parsed_song_title=parsed_title,
                )
                db.add(rq)

        log.songs_added = songs_added
        log.refs_added = refs_added
        log.status = "SUCCESS"
        log.finished_at = datetime.utcnow()

        channel.last_crawled_at = datetime.utcnow()
        db.commit()

        return {
            "channel_id": channel.id,
            "channel_name": channel.name,
            "status": "SUCCESS",
            "videos_found": log.videos_found,
            "songs_added": songs_added,
            "refs_added": refs_added,
            "review_queue_added": log.videos_found - refs_added - songs_added,
        }

    except Exception as e:
        try:
            db.rollback()
            fail_log = CrawlLog(
                channel_id=channel.id,
                status="FAILED",
                error_message=str(e),
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
            )
            db.add(fail_log)
            db.commit()
        except Exception:
            db.rollback()
        return {
            "channel_id": channel.id,
            "channel_name": channel.name,
            "status": "FAILED",
            "error": str(e),
        }
