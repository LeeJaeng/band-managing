from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from pydantic import BaseModel

from db import get_db
from models import Song, SongReference, SongSheet

router = APIRouter(prefix="/api/songs", tags=["songs"])


# ── Schemas ────────────────────────────────────────────

class SongCreate(BaseModel):
    title: str
    artist: str | None = None
    default_key: str | None = None
    lyrics: str | None = None


class SongUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
    default_key: str | None = None
    lyrics: str | None = None


class ReferenceCreate(BaseModel):
    youtube_url: str
    youtube_video_id: str
    title: str
    thumbnail_url: str | None = None
    key: str | None = None
    channel_id: str | None = None
    trust_level: str = "MEDIUM"
    source: str = "MANUAL"


class ReferenceUpdate(BaseModel):
    title: str | None = None
    key: str | None = None
    trust_level: str | None = None


class SheetCreate(BaseModel):
    file_url: str
    file_type: str  # PDF / IMAGE
    reference_id: str | None = None
    uploaded_by: str | None = None


# ── Song CRUD ──────────────────────────────────────────

@router.get("")
def list_songs(
    q: str = Query(default="", description="검색어 (제목/가사)"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Song)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Song.title.ilike(like), Song.lyrics.ilike(like)))
    total = query.count()
    songs = (
        query.options(joinedload(Song.references))
        .order_by(Song.title).offset(offset).limit(limit).all()
    )
    return {
        "total": total,
        "items": [
            {
                "id": s.id,
                "title": s.title,
                "artist": s.artist,
                "default_key": s.default_key,
                "ref_count": len(s.references),
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in songs
        ],
    }


@router.get("/{song_id}")
def get_song(song_id: str, db: Session = Depends(get_db)):
    song = (
        db.query(Song)
        .options(joinedload(Song.references), joinedload(Song.sheets))
        .filter(Song.id == song_id)
        .first()
    )
    if not song:
        raise HTTPException(404, "Song not found")
    return {
        "id": song.id,
        "title": song.title,
        "artist": song.artist,
        "default_key": song.default_key,
        "lyrics": song.lyrics,
        "created_at": song.created_at.isoformat() if song.created_at else None,
        "updated_at": song.updated_at.isoformat() if song.updated_at else None,
        "references": [
            {
                "id": r.id,
                "youtube_url": r.youtube_url,
                "youtube_video_id": r.youtube_video_id,
                "title": r.title,
                "thumbnail_url": r.thumbnail_url,
                "key": r.key,
                "trust_level": r.trust_level,
                "source": r.source,
                "channel_id": r.channel_id,
            }
            for r in song.references
        ],
        "sheets": [
            {
                "id": sh.id,
                "file_url": sh.file_url,
                "file_type": sh.file_type,
                "reference_id": sh.reference_id,
                "uploaded_by": sh.uploaded_by,
            }
            for sh in song.sheets
        ],
    }


@router.post("", status_code=201)
def create_song(body: SongCreate, db: Session = Depends(get_db)):
    song = Song(title=body.title, artist=body.artist, default_key=body.default_key, lyrics=body.lyrics)
    db.add(song)
    db.commit()
    db.refresh(song)
    return {"id": song.id, "title": song.title}


@router.put("/{song_id}")
def update_song(song_id: str, body: SongUpdate, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(404, "Song not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(song, field, value)
    db.commit()
    db.refresh(song)
    return {"id": song.id, "title": song.title}


@router.delete("/{song_id}")
def delete_song(song_id: str, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(404, "Song not found")
    # conti_items에서 참조 제거
    from models import ContiItem, ReviewQueue
    db.query(ContiItem).filter(ContiItem.song_id == song_id).delete()
    # review_queue에서 참조 제거
    db.query(ReviewQueue).filter(ReviewQueue.suggested_song_id == song_id).update(
        {"suggested_song_id": None}, synchronize_session="fetch"
    )
    db.delete(song)
    db.commit()
    return {"ok": True}


@router.post("/merge")
def merge_songs(source_id: str, target_id: str, db: Session = Depends(get_db)):
    """source 곡의 레퍼런스/악보를 target으로 옮기고 source 삭제."""
    source = db.query(Song).filter(Song.id == source_id).first()
    target = db.query(Song).filter(Song.id == target_id).first()
    if not source or not target:
        raise HTTPException(404, "Song not found")
    # relationship cascade를 우회하여 직접 SQL로 이동
    from models import SongReference, SongSheet
    db.query(SongReference).filter(SongReference.song_id == source.id).update(
        {"song_id": target.id}, synchronize_session="fetch"
    )
    db.query(SongSheet).filter(SongSheet.song_id == source.id).update(
        {"song_id": target.id}, synchronize_session="fetch"
    )
    db.flush()
    # source를 expunge하여 cascade 삭제 방지 후 직접 삭제
    db.query(Song).filter(Song.id == source.id).delete(synchronize_session="fetch")
    db.commit()
    return {"ok": True, "target_id": target.id}


# ── References ─────────────────────────────────────────

@router.get("/{song_id}/references")
def list_references(song_id: str, db: Session = Depends(get_db)):
    refs = db.query(SongReference).filter(SongReference.song_id == song_id).all()
    return [
        {
            "id": r.id,
            "youtube_url": r.youtube_url,
            "youtube_video_id": r.youtube_video_id,
            "title": r.title,
            "thumbnail_url": r.thumbnail_url,
            "key": r.key,
            "trust_level": r.trust_level,
            "source": r.source,
            "channel_id": r.channel_id,
        }
        for r in refs
    ]


@router.post("/{song_id}/references", status_code=201)
def add_reference(song_id: str, body: ReferenceCreate, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(404, "Song not found")
    ref = SongReference(song_id=song_id, **body.model_dump())
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return {"id": ref.id}


@router.put("/references/{ref_id}")
def update_reference(ref_id: str, body: ReferenceUpdate, db: Session = Depends(get_db)):
    ref = db.query(SongReference).filter(SongReference.id == ref_id).first()
    if not ref:
        raise HTTPException(404, "Reference not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ref, field, value)
    db.commit()
    return {"ok": True}


@router.delete("/references/{ref_id}")
def delete_reference(ref_id: str, db: Session = Depends(get_db)):
    ref = db.query(SongReference).filter(SongReference.id == ref_id).first()
    if not ref:
        raise HTTPException(404, "Reference not found")
    db.delete(ref)
    db.commit()
    return {"ok": True}


# ── Sheets ─────────────────────────────────────────────

@router.get("/{song_id}/sheets")
def list_sheets(song_id: str, db: Session = Depends(get_db)):
    sheets = db.query(SongSheet).filter(SongSheet.song_id == song_id).all()
    return [
        {
            "id": sh.id,
            "file_url": sh.file_url,
            "file_type": sh.file_type,
            "reference_id": sh.reference_id,
            "uploaded_by": sh.uploaded_by,
        }
        for sh in sheets
    ]


@router.post("/{song_id}/sheets", status_code=201)
def upload_sheet(song_id: str, body: SheetCreate, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(404, "Song not found")
    sheet = SongSheet(song_id=song_id, **body.model_dump())
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    return {"id": sheet.id}


@router.delete("/sheets/{sheet_id}")
def delete_sheet(sheet_id: str, db: Session = Depends(get_db)):
    sheet = db.query(SongSheet).filter(SongSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(404, "Sheet not found")
    db.delete(sheet)
    db.commit()
    return {"ok": True}
