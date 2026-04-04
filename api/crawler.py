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
]

# 키 감지 패턴
KEY_PATTERN = re.compile(r"keys?\s*[:\-]?\s*([A-G][#b]?m?)", re.IGNORECASE)


def parse_song_title(video_title: str) -> str:
    """영상 제목에서 곡 제목을 추출."""
    title = video_title.strip()
    for pattern in STRIP_PATTERNS:
        title = re.sub(pattern, "", title, flags=re.IGNORECASE)
    title = title.strip(" -–—·|")
    return title if title else video_title.strip()


def detect_key(text: str) -> str | None:
    """텍스트에서 키 정보를 추출."""
    match = KEY_PATTERN.search(text)
    return match.group(1) if match else None


def find_matching_song(parsed_title: str, db: Session) -> Song | None:
    """DB에서 제목이 유사한 곡을 찾기 (정확 매칭 우선)."""
    exact = db.query(Song).filter(Song.title == parsed_title).first()
    if exact:
        return exact
    like = db.query(Song).filter(Song.title.ilike(f"%{parsed_title}%")).first()
    return like


def _fetch_channel_videos(channel_id: str) -> list[dict]:
    """YouTube Data API로 채널의 영상 목록을 가져온다."""
    if not YOUTUBE_API_KEY:
        return []

    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    videos = []
    next_page = None

    for _ in range(5):  # 최대 5페이지 (250개)
        req = youtube.search().list(
            channelId=channel_id,
            part="snippet",
            type="video",
            order="date",
            maxResults=50,
            pageToken=next_page,
        )
        resp = req.execute()

        for item in resp.get("items", []):
            snippet = item["snippet"]
            videos.append({
                "video_id": item["id"]["videoId"],
                "title": snippet["title"],
                "description": snippet.get("description", ""),
                "thumbnail": snippet["thumbnails"].get("high", {}).get("url", ""),
                "published_at": snippet["publishedAt"],
            })

        next_page = resp.get("nextPageToken")
        if not next_page:
            break

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
                # 확실한 매칭 → 레퍼런스 추가
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
                # 불확실 → 검증 큐
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
            "refs_added": refs_added,
        }

    except Exception as e:
        log.status = "FAILED"
        log.error_message = str(e)
        log.finished_at = datetime.utcnow()
        db.commit()
        return {
            "channel_id": channel.id,
            "channel_name": channel.name,
            "status": "FAILED",
            "error": str(e),
        }
