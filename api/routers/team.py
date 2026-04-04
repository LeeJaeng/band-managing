from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db import get_db
from models import TeamMember, User
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/team", tags=["team"])


# ── Schemas ────────────────────────────────────────────

class MemberCreate(BaseModel):
    name: str
    position: str


class MemberUpdate(BaseModel):
    name: str | None = None
    position: str | None = None
    is_active: bool | None = None


# ── CRUD ───────────────────────────────────────────────

@router.get("/members")
def list_members(
    active_only: bool = Query(default=False),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(TeamMember)
    if active_only:
        q = q.filter(TeamMember.is_active == True)
    members = q.order_by(TeamMember.position, TeamMember.name).all()
    return {
        "total": len(members),
        "items": [
            {
                "id": m.id,
                "name": m.name,
                "position": m.position,
                "is_active": m.is_active,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in members
        ],
    }


@router.get("/members/{member_id}")
def get_member(member_id: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(404, "Member not found")
    return {
        "id": member.id,
        "name": member.name,
        "position": member.position,
        "is_active": member.is_active,
    }


@router.post("/members", status_code=201)
def create_member(body: MemberCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    member = TeamMember(name=body.name, position=body.position)
    db.add(member)
    db.commit()
    db.refresh(member)
    return {"id": member.id, "name": member.name, "position": member.position}


@router.put("/members/{member_id}")
def update_member(member_id: str, body: MemberUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(404, "Member not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return {"id": member.id, "name": member.name, "position": member.position, "is_active": member.is_active}


@router.delete("/members/{member_id}")
def delete_member(member_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    member = db.query(TeamMember).filter(TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(404, "Member not found")
    db.delete(member)
    db.commit()
    return {"ok": True}
