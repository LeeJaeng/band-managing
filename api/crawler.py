"""유튜브 채널 크롤링 모듈.

MVP에서는 YouTube Data API v3를 사용.
API 키가 없으면 mock/스킵 처리.
"""

import os
import re
from datetime import datetime

from sqlalchemy.orm import Session

from models import CrawlChannel, CrawlLog, Song, SongReference, ReviewQueue

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

# 키 감지 패턴
KEY_PATTERN = re.compile(r"keys?\s*[:\-]?\s*([A-G][#b]?m?)", re.IGNORECASE)

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

# 최대 영상 길이 (초) — 10분 초과 영상 무시
MAX_DURATION_SECONDS = 600

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
    for pattern in STRIP_PATTERNS:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)
    # 사역팀 이름 제거
    for team in TEAM_NAMES:
        title = re.sub(re.escape(team), "", title, flags=re.IGNORECASE)
    # " - " 뒤에 남은 텍스트 제거 (보통 팀 이름이 뒤에 붙음)
    title = re.sub(r"\s*-\s*$", "", title)
    title = title.strip(" -–—·|,")
    return title if title else video_title.strip()


def detect_key(text: str) -> str | None:
    """텍스트에서 키 정보를 추출."""
    match = KEY_PATTERN.search(text)
    return match.group(1) if match else None


def should_skip_video(title: str) -> bool:
    """예배 실황, 연주, inst, 합쳐진 곡 등 스킵해야 할 영상인지 확인."""
    lower = title.lower()
    for kw in SKIP_KEYWORDS:
        if kw.lower() in lower:
            return True
    for kw in SKIP_TYPE_KEYWORDS:
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


def _fetch_channel_videos(channel_id_or_handle: str) -> list[dict]:
    """YouTube Data API로 채널의 영상 목록을 가져온다."""
    if not YOUTUBE_API_KEY:
        return []

    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # @handle → UC... 변환
    resolved_id = _resolve_channel_id(youtube, channel_id_or_handle)

    # 업로드 재생목록 ID: UC... → UU...
    uploads_playlist_id = "UU" + resolved_id[2:]

    # 1단계: playlistItems로 영상 ID 목록 수집
    video_ids = []
    next_page = None

    for _ in range(5):  # 최대 5페이지 (250개)
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

            # 15분 초과 영상 무시
            if duration > MAX_DURATION_SECONDS:
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
        videos = _fetch_channel_videos(channel.youtube_channel_id)
        log.videos_found = len(videos)

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
                refs_added += 1
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
