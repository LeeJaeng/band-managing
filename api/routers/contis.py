from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from db import get_db
from models import Conti, ContiItem, Song, SongReference

router = APIRouter(prefix="/api/contis", tags=["contis"])


# ── Schemas ────────────────────────────────────────────

class ContiCreate(BaseModel):
    date: date_type
    service_name: str
    author: str


class ContiUpdate(BaseModel):
    date: date_type | None = None
    service_name: str | None = None
    author: str | None = None


class ItemCreate(BaseModel):
    song_id: str
    order_num: int
    slot_label: str = ""
    use_key: str | None = None
    reference_id: str | None = None
    memo: str | None = None


class ItemUpdate(BaseModel):
    song_id: str | None = None
    order_num: int | None = None
    slot_label: str | None = None
    use_key: str | None = None
    reference_id: str | None = None
    memo: str | None = None


class ReorderItem(BaseModel):
    id: str
    order_num: int


class ReorderBody(BaseModel):
    items: list[ReorderItem]


# ── helpers ────────────────────────────────────────────

def _serialize_item(item: ContiItem) -> dict:
    song = item.song
    ref = item.reference
    return {
        "id": item.id,
        "order_num": item.order_num,
        "slot_label": item.slot_label,
        "use_key": item.use_key,
        "memo": item.memo,
        "song": {
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "default_key": song.default_key,
        } if song else None,
        "reference": {
            "id": ref.id,
            "youtube_url": ref.youtube_url,
            "title": ref.title,
            "key": ref.key,
        } if ref else None,
    }


# ── Conti CRUD ─────────────────────────────────────────

@router.get("")
def list_contis(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    total = db.query(Conti).count()
    contis = db.query(Conti).order_by(Conti.date.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": c.id,
                "date": c.date.isoformat(),
                "service_name": c.service_name,
                "author": c.author,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in contis
        ],
    }


@router.get("/{conti_id}")
def get_conti(conti_id: str, db: Session = Depends(get_db)):
    conti = (
        db.query(Conti)
        .options(
            joinedload(Conti.items).joinedload(ContiItem.song),
            joinedload(Conti.items).joinedload(ContiItem.reference),
        )
        .filter(Conti.id == conti_id)
        .first()
    )
    if not conti:
        raise HTTPException(404, "Conti not found")
    return {
        "id": conti.id,
        "date": conti.date.isoformat(),
        "service_name": conti.service_name,
        "author": conti.author,
        "status": conti.status,
        "created_at": conti.created_at.isoformat() if conti.created_at else None,
        "items": [_serialize_item(item) for item in conti.items],
    }


@router.post("", status_code=201)
def create_conti(body: ContiCreate, db: Session = Depends(get_db)):
    conti = Conti(date=body.date, service_name=body.service_name, author=body.author)
    db.add(conti)
    db.commit()
    db.refresh(conti)
    return {"id": conti.id, "date": conti.date.isoformat(), "service_name": conti.service_name}


@router.put("/{conti_id}")
def update_conti(conti_id: str, body: ContiUpdate, db: Session = Depends(get_db)):
    conti = db.query(Conti).filter(Conti.id == conti_id).first()
    if not conti:
        raise HTTPException(404, "Conti not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(conti, field, value)
    db.commit()
    db.refresh(conti)
    return {"id": conti.id, "date": conti.date.isoformat(), "service_name": conti.service_name}


@router.delete("/{conti_id}")
def delete_conti(conti_id: str, db: Session = Depends(get_db)):
    conti = db.query(Conti).filter(Conti.id == conti_id).first()
    if not conti:
        raise HTTPException(404, "Conti not found")
    db.delete(conti)
    db.commit()
    return {"ok": True}


@router.put("/{conti_id}/confirm")
def confirm_conti(conti_id: str, db: Session = Depends(get_db)):
    conti = db.query(Conti).filter(Conti.id == conti_id).first()
    if not conti:
        raise HTTPException(404, "Conti not found")
    conti.status = "CONFIRMED"
    db.commit()
    return {"ok": True, "status": "CONFIRMED"}


# ── Conti Items ────────────────────────────────────────

@router.post("/{conti_id}/items", status_code=201)
def add_item(conti_id: str, body: ItemCreate, db: Session = Depends(get_db)):
    conti = db.query(Conti).filter(Conti.id == conti_id).first()
    if not conti:
        raise HTTPException(404, "Conti not found")
    song = db.query(Song).filter(Song.id == body.song_id).first()
    if not song:
        raise HTTPException(404, "Song not found")
    item = ContiItem(conti_id=conti_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id}


@router.put("/items/{item_id}")
def update_item(item_id: str, body: ItemUpdate, db: Session = Depends(get_db)):
    item = db.query(ContiItem).filter(ContiItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.commit()
    return {"ok": True}


@router.delete("/items/{item_id}")
def delete_item(item_id: str, db: Session = Depends(get_db)):
    item = db.query(ContiItem).filter(ContiItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.put("/{conti_id}/reorder")
def reorder_items(conti_id: str, body: ReorderBody, db: Session = Depends(get_db)):
    conti = db.query(Conti).filter(Conti.id == conti_id).first()
    if not conti:
        raise HTTPException(404, "Conti not found")
    for entry in body.items:
        item = db.query(ContiItem).filter(ContiItem.id == entry.id, ContiItem.conti_id == conti_id).first()
        if item:
            item.order_num = entry.order_num
    db.commit()
    return {"ok": True}
