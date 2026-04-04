from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db import get_db
from models import CrawlChannel, CrawlLog, ReviewQueue, Song, SongReference

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Schemas ────────────────────────────────────────────

class ChannelCreate(BaseModel):
    name: str
    youtube_channel_url: str
    youtube_channel_id: str
    trust_level: str = "HIGH"


class ChannelUpdate(BaseModel):
    name: str | None = None
    youtube_channel_url: str | None = None
    youtube_channel_id: str | None = None
    trust_level: str | None = None
    is_active: bool | None = None


class ReviewApprove(BaseModel):
    song_id: str | None = None  # 기존 곡에 매칭, None이면 새 곡 생성
    song_title: str | None = None  # 새 곡 생성 시 제목


# ── Channels ───────────────────────────────────────────

@router.get("/channels")
def list_channels(db: Session = Depends(get_db)):
    channels = db.query(CrawlChannel).order_by(CrawlChannel.name).all()
    return [
        {
            "id": ch.id,
            "name": ch.name,
            "youtube_channel_url": ch.youtube_channel_url,
            "youtube_channel_id": ch.youtube_channel_id,
            "trust_level": ch.trust_level,
            "is_active": ch.is_active,
            "last_crawled_at": ch.last_crawled_at.isoformat() if ch.last_crawled_at else None,
        }
        for ch in channels
    ]


@router.get("/channels/resolve-id")
def resolve_channel_id(youtube_channel_id: str = Query(...)):
    """@handle이나 UC...를 실제 채널 ID로 변환."""
    import os
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "YouTube API 키가 설정되지 않았습니다")

    from googleapiclient.discovery import build
    youtube = build("youtube", "v3", developerKey=api_key)

    channel_id = youtube_channel_id.strip().lstrip("@")

    if channel_id.startswith("UC"):
        return {"channel_id": channel_id}

    # forHandle로 시도
    resp = youtube.channels().list(part="id,snippet", forHandle=channel_id).execute()
    items = resp.get("items", [])
    if items:
        return {"channel_id": items[0]["id"], "name": items[0]["snippet"]["title"]}

    # forUsername으로 시도
    resp = youtube.channels().list(part="id,snippet", forUsername=channel_id).execute()
    items = resp.get("items", [])
    if items:
        return {"channel_id": items[0]["id"], "name": items[0]["snippet"]["title"]}

    raise HTTPException(404, f"채널을 찾을 수 없습니다: {youtube_channel_id}")


@router.post("/channels", status_code=201)
def create_channel(body: ChannelCreate, db: Session = Depends(get_db)):
    existing = db.query(CrawlChannel).filter(CrawlChannel.youtube_channel_id == body.youtube_channel_id).first()
    if existing:
        raise HTTPException(409, "Channel already exists")
    ch = CrawlChannel(**body.model_dump())
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return {"id": ch.id, "name": ch.name}


@router.put("/channels/{channel_id}")
def update_channel(channel_id: str, body: ChannelUpdate, db: Session = Depends(get_db)):
    ch = db.query(CrawlChannel).filter(CrawlChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(404, "Channel not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ch, field, value)
    db.commit()
    return {"ok": True}


@router.delete("/channels/{channel_id}")
def delete_channel(channel_id: str, db: Session = Depends(get_db)):
    ch = db.query(CrawlChannel).filter(CrawlChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(404, "Channel not found")
    # 관련 로그/검증큐 삭제
    db.query(CrawlLog).filter(CrawlLog.channel_id == channel_id).delete()
    db.query(ReviewQueue).filter(ReviewQueue.channel_id == channel_id).delete()
    # 레퍼런스의 channel_id를 null로 변경 (곡 데이터는 유지)
    from models import SongReference
    db.query(SongReference).filter(SongReference.channel_id == channel_id).update(
        {"channel_id": None}, synchronize_session="fetch"
    )
    db.delete(ch)
    db.commit()
    return {"ok": True}


# ── Crawl trigger ──────────────────────────────────────

@router.post("/crawl/{channel_id}")
def crawl_channel(channel_id: str, db: Session = Depends(get_db)):
    """특정 채널 크롤링 실행 (동기식 — MVP)."""
    ch = db.query(CrawlChannel).filter(CrawlChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(404, "Channel not found")

    try:
        from crawler import crawl_channel as do_crawl
        result = do_crawl(ch, db)
        return result
    except Exception as e:
        db.rollback()
        return {
            "channel_id": ch.id,
            "channel_name": ch.name,
            "status": "FAILED",
            "error": str(e),
            "videos_found": 0,
            "refs_added": 0,
        }


@router.post("/crawl/all")
def crawl_all(db: Session = Depends(get_db)):
    """활성화된 모든 채널 크롤링."""
    channels = db.query(CrawlChannel).filter(CrawlChannel.is_active == True).all()
    results = []
    from crawler import crawl_channel as do_crawl
    for ch in channels:
        result = do_crawl(ch, db)
        results.append(result)
    return {"channels_crawled": len(results), "results": results}


# ── Crawl logs ─────────────────────────────────────────

@router.get("/crawl/logs")
def list_crawl_logs(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    logs = db.query(CrawlLog).order_by(CrawlLog.started_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "channel_id": log.channel_id,
            "status": log.status,
            "videos_found": log.videos_found,
            "songs_added": log.songs_added,
            "refs_added": log.refs_added,
            "error_message": log.error_message,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "finished_at": log.finished_at.isoformat() if log.finished_at else None,
        }
        for log in logs
    ]


# ── Review queue ───────────────────────────────────────

@router.get("/review-queue")
def list_review_queue(
    status: str = Query(default="PENDING"),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    items = (
        db.query(ReviewQueue)
        .filter(ReviewQueue.status == status)
        .order_by(ReviewQueue.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for rq in items:
        # 파싱된 제목으로 유사곡 검색
        candidates = []
        if rq.parsed_song_title:
            like = f"%{rq.parsed_song_title}%"
            matched = db.query(Song).filter(Song.title.ilike(like)).limit(5).all()
            candidates = [{"id": s.id, "title": s.title} for s in matched]

        result.append({
            "id": rq.id,
            "youtube_video_id": rq.youtube_video_id,
            "youtube_url": rq.youtube_url,
            "video_title": rq.video_title,
            "channel_id": rq.channel_id,
            "parsed_song_title": rq.parsed_song_title,
            "suggested_song_id": rq.suggested_song_id,
            "status": rq.status,
            "created_at": rq.created_at.isoformat() if rq.created_at else None,
            "candidates": candidates,
        })
    return result


@router.post("/review/{review_id}/approve")
def approve_review(review_id: str, body: ReviewApprove, db: Session = Depends(get_db)):
    rq = db.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()
    if not rq:
        raise HTTPException(404, "Review item not found")

    # 곡 결정
    if body.song_id:
        song = db.query(Song).filter(Song.id == body.song_id).first()
        if not song:
            raise HTTPException(404, "Song not found")
    else:
        title = body.song_title or rq.parsed_song_title or rq.video_title
        song = Song(title=title)
        db.add(song)
        db.flush()

    # 레퍼런스 추가
    ref = SongReference(
        song_id=song.id,
        youtube_url=rq.youtube_url,
        youtube_video_id=rq.youtube_video_id,
        title=rq.video_title,
        channel_id=rq.channel_id,
        trust_level="HIGH",
        source="CRAWL",
    )
    db.add(ref)

    rq.status = "APPROVED"
    rq.reviewed_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "song_id": song.id}


@router.post("/review/{review_id}/reject")
def reject_review(review_id: str, db: Session = Depends(get_db)):
    rq = db.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()
    if not rq:
        raise HTTPException(404, "Review item not found")
    rq.status = "REJECTED"
    rq.reviewed_at = datetime.utcnow()
    db.commit()
    return {"ok": True}
