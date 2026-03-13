# api/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import uuid
import json

from sqlalchemy import select
from api.db import SessionLocal, engine, Base
from api.ws_hub import Hub

from api.models import (
    Team, Invite, TeamMember,
    Session as DbSession,
    SessionParticipant,
    Grant as DbGrant,
    Broadcast as DbBroadcast,
    BroadcastPreset as DbPreset,
)

Base.metadata.create_all(bind=engine)

app = FastAPI()
hub = Hub()

@app.get("/health")
def health():
    return {"ok": True, "service": "band-managing-api"}

# ---------- Team ----------
class TeamCreate(BaseModel):
    name: str

@app.post("/teams")
def create_team(body: TeamCreate):
    with SessionLocal() as db:
        team = Team(name=body.name)
        db.add(team)
        db.commit()
        db.refresh(team)
        return {"id": team.id, "name": team.name}

# ---------- WS ----------
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
                user = msg.get("user")

                await hub.join(joined_session_id, ws)
                await ws.send_text(json.dumps({"type": "JOINED"}))

                if user:
                    await hub.broadcast(joined_session_id, {"type": "USER_JOINED", "data": user})

            else:
                await ws.send_text(json.dumps({"type": "ERROR", "message": "unknown type"}))
    except WebSocketDisconnect:
        if joined_session_id:
            await hub.leave(joined_session_id, ws)

# ---------- Session ----------
class SessionCreate(BaseModel):
    team_id: str
    title: str
    parts: list[str] | None = None  # ✅ Step3

@app.post("/sessions")
def create_session(body: SessionCreate):
    with SessionLocal() as db:
        team = db.get(Team, body.team_id)
        if not team:
            raise HTTPException(404, "team not found")

        parts = body.parts if body.parts and len(body.parts) > 0 else None
        s = DbSession(team_id=body.team_id, title=body.title, status="ACTIVE")
        if parts is not None:
            s.parts = parts

        db.add(s)
        db.commit()
        db.refresh(s)
        return {"id": s.id, "team_id": s.team_id, "title": s.title, "status": s.status, "parts": s.parts}

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    with SessionLocal() as db:
        s = db.get(DbSession, session_id)
        if not s:
            raise HTTPException(404, "session not found")
        return {"id": s.id, "team_id": s.team_id, "title": s.title, "status": s.status, "parts": s.parts}

# join
class JoinSessionBody(BaseModel):
    user_name: str
    part: str | None = None

@app.post("/sessions/{session_id}/join")
def join_session(session_id: str, body: JoinSessionBody):
    with SessionLocal() as db:
        s = db.get(DbSession, session_id)
        if not s:
            raise HTTPException(404, "session not found")

        first = (
            db.execute(select(SessionParticipant).where(SessionParticipant.session_id == session_id))
            .scalars()
            .first()
        )
        is_first = first is None

        p = SessionParticipant(
            session_id=session_id,
            user_name=body.user_name.strip(),
            part=body.part,
            role="LEADER" if is_first else "MEMBER",
        )
        db.add(p)
        db.commit()
        db.refresh(p)

        # leader default grant
        if p.role == "LEADER":
            existing = (
                db.execute(select(DbGrant).where(DbGrant.session_id == session_id, DbGrant.user_name == p.id))
                .scalar_one_or_none()
            )
            if not existing:
                db.add(DbGrant(session_id=session_id, user_name=p.id, can_broadcast=True))
                db.commit()

        return {"participant": {"id": p.id, "user_name": p.user_name, "part": p.part, "role": p.role}}

@app.get("/sessions/{session_id}/participants")
def list_participants(session_id: str):
    with SessionLocal() as db:
        rows = (
            db.execute(
                select(SessionParticipant)
                .where(SessionParticipant.session_id == session_id)
                .order_by(SessionParticipant.joined_at.asc())
            )
            .scalars()
            .all()
        )
        return [{"id": r.id, "user_name": r.user_name, "part": r.part, "role": r.role} for r in rows]

# ---------- Permissions ----------
class BroadcastPermissionBody(BaseModel):
    participant_id: str
    can_broadcast: bool = True

@app.post("/sessions/{session_id}/broadcast-permissions")
async def set_broadcast_permission(session_id: str, body: BroadcastPermissionBody):
    with SessionLocal() as db:
        p = db.get(SessionParticipant, body.participant_id)
        if not p or p.session_id != session_id:
            raise HTTPException(404, "participant not found")

        if p.role == "LEADER":
            body.can_broadcast = True

        existing = (
            db.execute(select(DbGrant).where(DbGrant.session_id == session_id, DbGrant.user_name == body.participant_id))
            .scalar_one_or_none()
        )
        if existing:
            existing.can_broadcast = body.can_broadcast
            db.commit()
        else:
            db.add(DbGrant(session_id=session_id, user_name=body.participant_id, can_broadcast=body.can_broadcast))
            db.commit()

    await hub.broadcast(session_id, {
        "type": "PERMISSION_UPDATED",
        "data": {"participant_id": body.participant_id, "can_broadcast": body.can_broadcast}
    })
    return {"ok": True}

@app.get("/sessions/{session_id}/broadcast-permissions")
def list_broadcast_permissions(session_id: str):
    with SessionLocal() as db:
        rows = db.execute(select(DbGrant).where(DbGrant.session_id == session_id)).scalars().all()
        return [{"participant_id": r.user_name, "can_broadcast": r.can_broadcast} for r in rows]

# ---------- Presets (Step3) ----------
class PresetCreate(BaseModel):
    team_id: str
    title: str
    text: str | None = None

class PresetUpdate(BaseModel):
    title: str | None = None
    text: str | None = None

@app.get("/teams/{team_id}/presets")
def list_presets(team_id: str):
    with SessionLocal() as db:
        rows = (
            db.execute(select(DbPreset).where(DbPreset.team_id == team_id).order_by(DbPreset.created_at.desc()))
            .scalars()
            .all()
        )
        return [{"id": r.id, "title": r.title, "payload": r.payload} for r in rows]

async def _broadcast_presets_updated(team_id: str):
    with SessionLocal() as db:
        session_ids = (
            db.execute(select(DbSession.id).where(DbSession.team_id == team_id, DbSession.status == "ACTIVE"))
            .scalars()
            .all()
        )

    payload = {"type": "PRESETS_UPDATED", "data": {"team_id": team_id}}
    for session_id in session_ids:
        await hub.broadcast(session_id, payload)

@app.post("/teams/{team_id}/presets")
async def create_preset(team_id: str, body: PresetCreate):
    with SessionLocal() as db:
        team = db.get(Team, team_id)
        if not team:
            raise HTTPException(404, "team not found")

        payload = {}
        if body.text is not None:
            payload["text"] = body.text

        p = DbPreset(team_id=team_id, title=body.title.strip(), payload=payload)
        db.add(p)
        db.commit()
        db.refresh(p)
        result = {"id": p.id, "title": p.title, "payload": p.payload}

    await _broadcast_presets_updated(team_id)
    return result

@app.put("/presets/{preset_id}")
async def update_preset(preset_id: str, body: PresetUpdate):
    with SessionLocal() as db:
        p = db.get(DbPreset, preset_id)
        if not p:
            raise HTTPException(404, "preset not found")
        team_id = p.team_id

        if body.title is not None:
            p.title = body.title.strip()

        # text가 ""(빈 문자열)로 들어오면 payload에서 제거해서 "title 전송" 규칙을 만들 수 있음
        if body.text is None:
            pass
        else:
            if body.text.strip() == "":
                # payload text 제거
                newp = dict(p.payload or {})
                newp.pop("text", None)
                p.payload = newp
            else:
                newp = dict(p.payload or {})
                newp["text"] = body.text
                p.payload = newp

        db.commit()
        db.refresh(p)
        result = {"id": p.id, "title": p.title, "payload": p.payload}

    await _broadcast_presets_updated(team_id)
    return result

@app.delete("/presets/{preset_id}")
async def delete_preset(preset_id: str):
    with SessionLocal() as db:
        p = db.get(DbPreset, preset_id)
        if not p:
            raise HTTPException(404, "preset not found")
        team_id = p.team_id
        db.delete(p)
        db.commit()

    await _broadcast_presets_updated(team_id)
    return {"ok": True}

# ---------- Broadcast ----------
class BroadcastCreate(BaseModel):
    session_id: str
    sender_id: str
    target: dict
    type: str
    payload: dict

def _is_leader(db, sender_id: str) -> bool:
    p = db.get(SessionParticipant, sender_id)
    return bool(p and p.role == "LEADER")

def _can_user_broadcast(db, session_id: str, sender_id: str) -> bool:
    if _is_leader(db, sender_id):
        return True
    g = db.execute(select(DbGrant).where(DbGrant.session_id == session_id, DbGrant.user_name == sender_id)).scalar_one_or_none()
    return bool(g and g.can_broadcast)

@app.post("/broadcasts")
async def create_broadcast(body: BroadcastCreate):
    with SessionLocal() as db:
        s = db.get(DbSession, body.session_id)
        if not s:
            raise HTTPException(404, "session not found")

        if not _can_user_broadcast(db, body.session_id, body.sender_id):
            raise HTTPException(403, "no permission to broadcast")

        b = DbBroadcast(
            session_id=body.session_id,
            sender_id=body.sender_id,
            target=body.target,
            type=body.type,
            payload=body.payload,
        )
        db.add(b)
        db.commit()
        db.refresh(b)

        sp = db.get(SessionParticipant, body.sender_id)
        sender = None
        if sp:
            sender = {"id": sp.id, "name": sp.user_name, "part": sp.part, "role": sp.role}

        event = {
            "type": "BROADCAST",
            "data": {
                "id": b.id,
                "session_id": b.session_id,
                "sender": sender,
                "target": b.target,
                "type": b.type,
                "payload": b.payload,
                "created_at": str(b.created_at),
            },
        }
        await hub.broadcast(b.session_id, event)
        return {"id": b.id, "created_at": str(b.created_at)}