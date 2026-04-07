from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db import get_db
from models import CrawlChannel, CrawlLog, ReviewQueue, Song, SongReference, SongSheet, ContiItem, User, CrawlFilterKeyword
from auth import require_admin

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
    song_id: str | None = None      # 기존 곡에 매칭, None이면 새 곡 생성
    song_title: str | None = None   # 새 곡 생성 시 제목
    keys: list[str] | None = None   # 새 곡 생성 시 키 목록
    tempo: str | None = None        # 새 곡 생성 시 빠르기 (FAST/SLOW)


# ── Channels ───────────────────────────────────────────

@router.get("/channels")
def list_channels(_: User = Depends(require_admin), db: Session = Depends(get_db)):
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
def resolve_channel_id(youtube_channel_id: str = Query(...), _: User = Depends(require_admin)):
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
def create_channel(body: ChannelCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    existing = db.query(CrawlChannel).filter(CrawlChannel.youtube_channel_id == body.youtube_channel_id).first()
    if existing:
        raise HTTPException(409, "Channel already exists")
    ch = CrawlChannel(**body.model_dump())
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return {"id": ch.id, "name": ch.name}


@router.put("/channels/{channel_id}")
def update_channel(channel_id: str, body: ChannelUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    ch = db.query(CrawlChannel).filter(CrawlChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(404, "Channel not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ch, field, value)
    db.commit()
    return {"ok": True}


@router.delete("/channels/{channel_id}")
def delete_channel(channel_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
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

@router.post("/crawl/all")
def crawl_all(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """활성화된 모든 채널 크롤링."""
    channels = db.query(CrawlChannel).filter(CrawlChannel.is_active == True).all()
    results = []
    from crawler import crawl_channel as do_crawl
    for ch in channels:
        try:
            result = do_crawl(ch, db)
        except Exception as e:
            db.rollback()
            result = {"channel_id": ch.id, "channel_name": ch.name, "status": "FAILED", "error": str(e), "videos_found": 0, "refs_added": 0}
        results.append(result)
    return {"channels_crawled": len(results), "results": results}


@router.post("/crawl/{channel_id}")
def crawl_channel(channel_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
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


# ── Setlist crawl (예배 실황 description 파싱) ──────────

@router.post("/crawl-setlists/all")
def crawl_setlists_all(
    max_videos: int = 10,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """활성 채널의 예배 실황 영상에서 세트리스트를 추출해 곡/키/레퍼런스 보강."""
    channels = db.query(CrawlChannel).filter(CrawlChannel.is_active == True).all()
    from crawler import crawl_setlists as do_setlists
    results = []
    for ch in channels:
        try:
            results.append(do_setlists(ch, db, max_videos=max_videos))
        except Exception as e:
            db.rollback()
            results.append({
                "channel_id": ch.id,
                "channel_name": ch.name,
                "status": "FAILED",
                "error": str(e),
            })
    return {"channels_crawled": len(results), "results": results}


@router.post("/crawl-setlists/{channel_id}")
def crawl_setlists_one(
    channel_id: str,
    max_videos: int = 10,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """특정 채널의 예배 실황 세트리스트만 크롤."""
    ch = db.query(CrawlChannel).filter(CrawlChannel.id == channel_id).first()
    if not ch:
        raise HTTPException(404, "Channel not found")
    try:
        from crawler import crawl_setlists as do_setlists
        return do_setlists(ch, db, max_videos=max_videos)
    except Exception as e:
        db.rollback()
        return {
            "channel_id": ch.id,
            "channel_name": ch.name,
            "status": "FAILED",
            "error": str(e),
        }


# ── Crawl logs ─────────────────────────────────────────

@router.get("/crawl/logs")
def list_crawl_logs(
    limit: int = Query(default=50, le=200),
    _: User = Depends(require_admin),
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
    limit: int = Query(default=10, le=100),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(ReviewQueue).filter(ReviewQueue.status == status)
    total = q.count()
    items = q.order_by(ReviewQueue.created_at.asc()).offset(offset).limit(limit).all()

    result = []
    for rq in items:
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
    return {"total": total, "items": result}


@router.get("/review-queue/export")
def export_review_queue(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """검증 큐를 Claude Code에 붙여넣기 가능한 텍스트로 내보내기."""
    items = (
        db.query(ReviewQueue)
        .filter(ReviewQueue.status == "PENDING")
        .order_by(ReviewQueue.created_at.desc())
        .all()
    )
    if not items:
        return {"text": "== 검증 큐 비어있음 ==", "count": 0}

    lines = [f"== 검증 큐 ({len(items)}개) =="]
    lines.append("아래 내용을 Claude Code에 붙여넣으면 곡 매칭/등록을 처리합니다.")
    lines.append("각 항목에 대해: 승인(기존곡 매칭 or 새곡) / 거부 를 판단해주세요.")
    lines.append("")

    for i, rq in enumerate(items, 1):
        # 유사곡 검색
        candidates_str = "없음"
        if rq.parsed_song_title:
            like = f"%{rq.parsed_song_title}%"
            matched = db.query(Song).filter(Song.title.ilike(like)).limit(3).all()
            if matched:
                candidates_str = ", ".join(f"{s.title}(id:{s.id})" for s in matched)

        lines.append(
            f"{i}. [review_id:{rq.id}] \"{rq.video_title}\" "
            f"→ 파싱: \"{rq.parsed_song_title or '(없음)'}\" "
            f"| 유사곡: {candidates_str} "
            f"| URL: {rq.youtube_url}"
        )

    lines.append("")
    lines.append("---")
    lines.append("처리 형식: 각 번호에 대해")
    lines.append("- 기존곡 매칭: POST /api/admin/review/{review_id}/approve {\"song_id\": \"곡ID\"}")
    lines.append("- 새곡 등록: POST /api/admin/review/{review_id}/approve {\"song_title\": \"곡제목\"}")
    lines.append("- 거부: POST /api/admin/review/{review_id}/reject")

    return {"text": "\n".join(lines), "count": len(items)}


# 자동승인 시 "곡이 아닌" 영상을 걸러내는 블랙리스트.
# video_title / parsed_song_title 둘 다에 대해 부분 일치 검사 (lowercase).
NON_SONG_KEYWORDS = [
    # 설교/말씀/기도
    "설교", "sermon", "말씀묵상", "묵상", "큐티", "qt",
    "기도회", "새벽기도", "중보기도", "통성기도",
    # 축도/임직/권면
    "축도", "축복기도", "임직", "임직식", "권면", "권사", "장로",
    # 간증/나눔/인터뷰
    "간증", "나눔", "소감", "인터뷰", "interview", "토크", "talk show",
    # 강의/세미나/교육
    "강의", "세미나", "특강", "교육", "컨퍼런스", "conference", "수련회",
    # 공지/광고/이벤트
    "공지", "광고", "홍보", "안내", "이벤트", "event", "모집",
    # 예배순서/봉독/봉헌
    "봉독", "봉헌", "성찬", "세례", "입교", "예배순서",
    # 오프닝/클로징/사회
    "오프닝", "클로징", "멘트", "사회",
    # 일상/브이로그
    "vlog", "브이로그", "일상", "데일리", "daily",
    # 리뷰/챌린지
    "챌린지", "challenge", "리뷰", "review",
    # 트레일러/티저 (크롤러에서도 거르지만 이중 방어)
    "trailer", "teaser", "예고",
]

# 서술/보고체 종결 — 곡 제목에는 거의 안 쓰이는 종결어만 (보수적)
# "찬양합니다"(합니다 ≠ 습니다), "사랑해요" 같은 일반 곡 제목은 안 걸림.
REPORT_ENDINGS = (
    "습니다",       # "왔습니다", "받았습니다", "오셨습니다" 등 과거형 서술
    "입니다",       # "오늘은 주일입니다"
    "드립니다",     # "감사드립니다"
)


def _is_non_song_content(video_title: str, parsed_title: str) -> bool:
    """블랙리스트 + 서술형 휴리스틱. True면 곡 아님 → PENDING 유지."""
    import re as _re

    vt = (video_title or "").lower()
    pt_raw = parsed_title or ""

    # 1) 블랙리스트 — 원본 제목 또는 파싱 제목에 포함되면 곡 아님
    pt_lower = pt_raw.lower()
    for kw in NON_SONG_KEYWORDS:
        if kw in vt or kw in pt_lower:
            return True

    # 2) 서술/보고체 종결 — parsed_title 기준
    stripped = pt_raw.rstrip(" .~。")
    for ending in REPORT_ENDINGS:
        if stripped.endswith(ending):
            return True

    # 3) 일상 설명형 접두 — "오늘의 말씀", "이번주 나눔" 등
    if _re.match(r"^(오늘의|금주|이번주|이번\s)", pt_raw):
        return True

    return False


@router.post("/review/auto-approve")
def auto_approve_review_queue(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """검증 큐 자동 승인: 깔끔한 것은 자동 등록, 애매한 것만 남김.

    필터 순서:
      1) 길이/공백/숫자 기본 이상 감지
      2) 곡이 아닌 영상 판정(블랙리스트 + 문장형 휴리스틱)
      3) 위 둘 다 통과한 항목만 APPROVED 처리
    """
    import re

    items = db.query(ReviewQueue).filter(ReviewQueue.status == "PENDING").all()

    auto_approved = 0
    auto_rejected = 0
    skipped = 0  # 애매해서 남긴 것

    for rq in items:
        title = rq.parsed_song_title or ""

        # 애매한 것 판단 — PENDING으로 남김
        is_ambiguous = False

        # 1) 파싱된 제목이 없거나 너무 짧음
        if len(title.strip()) < 2:
            is_ambiguous = True
        # 2) 제목이 너무 김 (보통 곡 제목은 30자 이내)
        elif len(title) > 40:
            is_ambiguous = True
        # 3) 영어+한글 섞인 긴 설명형 제목
        elif title.count(" ") > 6:
            is_ambiguous = True
        # 4) 숫자만 있거나 의미 없는 제목
        elif re.match(r'^[\d\s\-\.]+$', title):
            is_ambiguous = True
        # 5) 곡이 아닌 콘텐츠 (설교/축도/나눔 등)
        elif _is_non_song_content(rq.video_title or "", title):
            is_ambiguous = True

        if is_ambiguous:
            skipped += 1
            continue

        # DB에 같은 곡 있는지 확인
        existing = db.query(Song).filter(Song.title == title).first()

        if existing:
            # 같은 곡 있으면 레퍼런스만 추가
            # 이미 같은 video_id 레퍼런스 있으면 스킵
            existing_ref = db.query(SongReference).filter(
                SongReference.youtube_video_id == rq.youtube_video_id
            ).first()
            if not existing_ref:
                ref = SongReference(
                    song_id=existing.id,
                    youtube_url=rq.youtube_url,
                    youtube_video_id=rq.youtube_video_id,
                    title=rq.video_title,
                    channel_id=rq.channel_id,
                    trust_level="HIGH",
                    source="CRAWL",
                )
                db.add(ref)
        else:
            # 새 곡 등록
            song = Song(title=title, source="CRAWLED")
            db.add(song)
            db.flush()

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
        auto_approved += 1

    db.commit()

    return {
        "total": len(items),
        "auto_approved": auto_approved,
        "skipped_ambiguous": skipped,
    }


@router.post("/review/batch")
def batch_review(body: dict, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    """검증 큐 일괄 처리. body: {"actions": [{"review_id": "...", "action": "approve|reject", "song_id": "...", "song_title": "..."}]}"""
    actions = body.get("actions", [])
    results = []
    for action in actions:
        review_id = action.get("review_id")
        act = action.get("action")
        rq = db.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()
        if not rq:
            results.append({"review_id": review_id, "status": "NOT_FOUND"})
            continue

        if act == "reject":
            rq.status = "REJECTED"
            rq.reviewed_at = datetime.utcnow()
            results.append({"review_id": review_id, "status": "REJECTED"})
        elif act == "approve":
            song_id = action.get("song_id")
            song_title = action.get("song_title")

            if song_id:
                song = db.query(Song).filter(Song.id == song_id).first()
                if not song:
                    results.append({"review_id": review_id, "status": "SONG_NOT_FOUND"})
                    continue
            else:
                title = song_title or rq.parsed_song_title or rq.video_title
                song = Song(title=title)
                db.add(song)
                db.flush()

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
            results.append({"review_id": review_id, "status": "APPROVED", "song_id": song.id})

    db.commit()
    return {"processed": len(results), "results": results}


@router.post("/review/{review_id}/approve")
def approve_review(review_id: str, body: ReviewApprove, _: User = Depends(require_admin), db: Session = Depends(get_db)):
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
        song = Song(
            title=title,
            keys=body.keys or None,
            tempo=body.tempo or None,
        )
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
def reject_review(review_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    rq = db.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()
    if not rq:
        raise HTTPException(404, "Review item not found")
    rq.status = "REJECTED"
    rq.reviewed_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


# ── User Songs Review ─────────────────────────────────

class SongSourceUpdate(BaseModel):
    source: str  # MANUAL / CRAWLED / USER


@router.delete("/crawl/reset")
def reset_crawl_data(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """크롤링 + 곡 데이터 전체 삭제 (TRUNCATE)."""
    from models import ContiItem, SongSheet

    # 순서 중요 (FK 의존성)
    db.query(ContiItem).delete()
    db.query(SongSheet).delete()
    ref_count = db.query(SongReference).delete()
    rq_count = db.query(ReviewQueue).delete()
    log_count = db.query(CrawlLog).delete()
    song_count = db.query(Song).delete()
    # 채널의 last_crawled_at 초기화
    db.query(CrawlChannel).update({"last_crawled_at": None}, synchronize_session="fetch")

    db.commit()
    return {
        "ok": True,
        "deleted": {
            "songs": song_count,
            "references": ref_count,
            "review_queue": rq_count,
            "crawl_logs": log_count,
        },
    }


@router.put("/songs/{song_id}/source")
def update_song_source(song_id: str, body: SongSourceUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(404, "Song not found")
    song.source = body.source
    if body.source in ("MANUAL", "CRAWLED"):
        song.user_id = None  # 정식 곡으로 전환 → 소유자 제거
    db.commit()
    return {"ok": True, "source": song.source}


# ── 곡 병합 (admin) ─────────────────────────────────────

class MergeBody(BaseModel):
    source_ids: list[str]  # 삭제될 곡들
    target_id: str         # 남길 곡


@router.post("/songs/merge")
def admin_merge_songs(body: MergeBody, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    """여러 source 곡의 레퍼런스/악보/콘티아이템을 target으로 이전하고 source 삭제."""
    source_ids = [sid for sid in body.source_ids if sid != body.target_id]
    if not source_ids:
        raise HTTPException(400, "source 곡이 없습니다")
    target = db.query(Song).filter(Song.id == body.target_id).first()
    if not target:
        raise HTTPException(404, "target 곡을 찾을 수 없습니다")

    for source_id in source_ids:
        source = db.query(Song).filter(Song.id == source_id).first()
        if not source:
            continue
        db.query(SongReference).filter(SongReference.song_id == source_id).update({"song_id": body.target_id})
        db.query(SongSheet).filter(SongSheet.song_id == source_id).update({"song_id": body.target_id})
        db.query(ContiItem).filter(ContiItem.song_id == source_id).update({"song_id": body.target_id})
        db.delete(source)

    db.commit()
    return {"ok": True, "merged_into": body.target_id, "merged_count": len(source_ids)}


class BulkUpdateBody(BaseModel):
    song_ids: list[str]
    add_keys: list[str] | None = None   # 기존 keys에 추가
    set_tempo: str | None = None        # FAST / SLOW / "" (빈 문자열이면 초기화)


@router.post("/songs/bulk-update")
def bulk_update_songs(body: BulkUpdateBody, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    """여러 곡에 키 추가 또는 빠르기 일괄 설정."""
    updated = 0
    for song_id in body.song_ids:
        song = db.query(Song).filter(Song.id == song_id).first()
        if not song:
            continue
        if body.add_keys:
            existing = list(song.keys or [])
            for k in body.add_keys:
                if k not in existing:
                    existing.append(k)
            song.keys = existing
        if body.set_tempo is not None:
            song.tempo = body.set_tempo if body.set_tempo else None
        updated += 1
    db.commit()
    return {"ok": True, "updated": updated}


# ── 필터 키워드 관리 ────────────────────────────────────

@router.get("/filter-keywords")
def list_filter_keywords(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    items = db.query(CrawlFilterKeyword).order_by(CrawlFilterKeyword.created_at.asc()).all()
    return [{"id": kw.id, "keyword": kw.keyword, "created_at": kw.created_at.isoformat()} for kw in items]


class FilterKeywordCreate(BaseModel):
    keyword: str


@router.post("/filter-keywords")
def add_filter_keyword(body: FilterKeywordCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    kw = body.keyword.strip().lower()
    if not kw:
        raise HTTPException(400, "키워드를 입력해주세요")
    exists = db.query(CrawlFilterKeyword).filter(CrawlFilterKeyword.keyword == kw).first()
    if exists:
        raise HTTPException(409, "이미 등록된 키워드입니다")
    item = CrawlFilterKeyword(keyword=kw)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "keyword": item.keyword, "created_at": item.created_at.isoformat()}


@router.delete("/filter-keywords/{keyword_id}")
def delete_filter_keyword(keyword_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(CrawlFilterKeyword).filter(CrawlFilterKeyword.id == keyword_id).first()
    if not item:
        raise HTTPException(404, "키워드를 찾을 수 없습니다")
    db.delete(item)
    db.commit()
    return {"ok": True}
