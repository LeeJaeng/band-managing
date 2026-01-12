from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import uuid

from sqlalchemy import select
from api.db import SessionLocal, engine, Base
from api.models import Team, Invite, TeamMember

from typing import Optional
from sqlalchemy import delete
from api.models import Session as DbSession, Grant as DbGrant, Broadcast as DbBroadcast, BroadcastPreset as DbPreset

from api.ws_hub import Hub

# create tables (MVP)
Base.metadata.create_all(bind=engine)

app = FastAPI()

hub = Hub()

@app.get("/health")
def health():
    return {"ok": True, "service": "band-managing-api"}

class TeamCreate(BaseModel):
    name: str

class InviteCreate(BaseModel):
    max_use: int = 10

class JoinRequest(BaseModel):
    user_name: str
    part: str | None = None

@app.post("/teams")
def create_team(body: TeamCreate):
    with SessionLocal() as db:
        team = Team(name=body.name)
        db.add(team)
        db.commit()
        db.refresh(team)
        return {"id": team.id, "name": team.name}

@app.post("/teams/{team_id}/invites")
def create_invite(team_id: str, body: InviteCreate):
    with SessionLocal() as db:
        team = db.get(Team, team_id)
        if not team:
            raise HTTPException(404, "team not found")
        code = uuid.uuid4().hex[:6]
        inv = Invite(code=code, team_id=team_id, remain=body.max_use)
        db.add(inv)
        db.commit()
        return {"code": code}

@app.post("/invites/{code}/join")
def join_team(code: str, body: JoinRequest):
    with SessionLocal() as db:
        inv = db.get(Invite, code)
        if not inv or inv.remain <= 0:
            raise HTTPException(400, "invalid invite")
        inv.remain -= 1
        member = TeamMember(team_id=inv.team_id, name=body.user_name, part=body.part)
        db.add(member)
        db.commit()
        return {"team_id": inv.team_id, "member": {"name": member.name, "part": member.part}}

import json

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    joined_session_id = None
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            t = msg.get("type")

            if t == "JOIN_SESSION":
                joined_session_id = msg["session_id"]
                await hub.join(joined_session_id, ws)
                await ws.send_text(json.dumps({"type": "JOINED"}))

            else:
                await ws.send_text(json.dumps({"type": "ERROR", "message": "unknown type"}))
    except WebSocketDisconnect:
        if joined_session_id:
            await hub.leave(joined_session_id, ws)

class SessionCreate(BaseModel):
    team_id: str
    title: str

class GrantUpsert(BaseModel):
    session_id: str
    user_name: str
    can_broadcast: bool = True

class PresetCreate(BaseModel):
    team_id: str
    label: str
    payload: dict

class BroadcastCreate(BaseModel):
    session_id: str
    sender_name: str
    target: dict   # {"all":true} or {"parts":[...]}
    type: str      # TEXT/PRESET
    payload: dict


@app.post("/sessions")
def create_session(body: SessionCreate):
    with SessionLocal() as db:
        team = db.get(Team, body.team_id)
        if not team:
            raise HTTPException(404, "team not found")
        s = DbSession(team_id=body.team_id, title=body.title, status="ACTIVE")
        db.add(s)
        db.commit()
        db.refresh(s)
        return {"id": s.id, "team_id": s.team_id, "title": s.title, "status": s.status}

@app.get("/teams/{team_id}/sessions")
def list_sessions(team_id: str):
    with SessionLocal() as db:
        rows = db.execute(select(DbSession).where(DbSession.team_id == team_id).order_by(DbSession.created_at.desc())).scalars().all()
        return [{"id": r.id, "title": r.title, "status": r.status, "created_at": str(r.created_at)} for r in rows]


@app.post("/grants")
def upsert_grant(body: GrantUpsert):
    with SessionLocal() as db:
        s = db.get(DbSession, body.session_id)
        if not s:
            raise HTTPException(404, "session not found")

        # 같은 session + user_name 있으면 업데이트, 없으면 생성
        existing = db.execute(
            select(DbGrant).where(DbGrant.session_id == body.session_id, DbGrant.user_name == body.user_name)
        ).scalar_one_or_none()

        if existing:
            existing.can_broadcast = body.can_broadcast
            db.commit()
            return {"id": existing.id, "session_id": existing.session_id, "user_name": existing.user_name, "can_broadcast": existing.can_broadcast}

        g = DbGrant(session_id=body.session_id, user_name=body.user_name, can_broadcast=body.can_broadcast)
        db.add(g)
        db.commit()
        db.refresh(g)
        return {"id": g.id, "session_id": g.session_id, "user_name": g.user_name, "can_broadcast": g.can_broadcast}

@app.get("/sessions/{session_id}/grants")
def list_grants(session_id: str):
    with SessionLocal() as db:
        rows = db.execute(select(DbGrant).where(DbGrant.session_id == session_id)).scalars().all()
        return [{"user_name": r.user_name, "can_broadcast": r.can_broadcast} for r in rows]


@app.post("/presets")
def create_preset(body: PresetCreate):
    with SessionLocal() as db:
        team = db.get(Team, body.team_id)
        if not team:
            raise HTTPException(404, "team not found")
        p = DbPreset(team_id=body.team_id, label=body.label, payload=body.payload)
        db.add(p)
        db.commit()
        db.refresh(p)
        return {"id": p.id, "team_id": p.team_id, "label": p.label, "payload": p.payload}

@app.get("/teams/{team_id}/presets")
def list_presets(team_id: str):
    with SessionLocal() as db:
        rows = db.execute(select(DbPreset).where(DbPreset.team_id == team_id).order_by(DbPreset.created_at.desc())).scalars().all()
        return [{"id": r.id, "label": r.label, "payload": r.payload} for r in rows]


def _can_user_broadcast(db, session_id: str, sender_name: str) -> bool:
    # MVP: grant가 있으면 허용 (리더 개념은 다음 단계에서 role로 강화)
    g = db.execute(select(DbGrant).where(DbGrant.session_id == session_id, DbGrant.user_name == sender_name)).scalar_one_or_none()
    return bool(g and g.can_broadcast)

@app.post("/broadcasts")
async def create_broadcast(body: BroadcastCreate):
    with SessionLocal() as db:
        s = db.get(DbSession, body.session_id)
        if not s:
            raise HTTPException(404, "session not found")

        if not _can_user_broadcast(db, body.session_id, body.sender_name):
            raise HTTPException(403, "no permission to broadcast")

        b = DbBroadcast(
            session_id=body.session_id,
            sender_name=body.sender_name,
            target=body.target,
            type=body.type,
            payload=body.payload,
        )
        db.add(b)
        db.commit()
        db.refresh(b)

        event = {
            "type": "BROADCAST",
            "data": {
                "id": b.id,
                "session_id": b.session_id,
                "sender_name": b.sender_name,
                "target": b.target,
                "type": b.type,
                "payload": b.payload,
                "created_at": str(b.created_at),
            },
        }

        # ✅ 여기서 그냥 await로 전파 (MVP에 충분히 빠름)
        await hub.broadcast(b.session_id, event)

        return {"id": b.id, "created_at": str(b.created_at)}

@app.get("/sessions/{session_id}/broadcasts")
def list_broadcasts(session_id: str, limit: int = 50):
    with SessionLocal() as db:
        rows = db.execute(
            select(DbBroadcast).where(DbBroadcast.session_id == session_id)
            .order_by(DbBroadcast.created_at.desc())
            .limit(limit)
        ).scalars().all()
        return [{
            "id": r.id,
            "sender_name": r.sender_name,
            "target": r.target,
            "type": r.type,
            "payload": r.payload,
            "created_at": str(r.created_at),
        } for r in rows]