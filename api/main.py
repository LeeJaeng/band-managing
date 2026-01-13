# api/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import uuid
import json

from sqlalchemy import select
from api.db import SessionLocal, engine, Base

from api.models import (
    Team,
    Invite,
    TeamMember,
    Session as DbSession,
    SessionParticipant,
    Grant as DbGrant,
    Broadcast as DbBroadcast,
    BroadcastPreset as DbPreset,
)

from api.ws_hub import Hub

# create tables (MVP)
Base.metadata.create_all(bind=engine)

app = FastAPI()
hub = Hub()


@app.get("/health")
def health():
    return {"ok": True, "service": "band-managing-api"}


# ---------- Team / Invite ----------
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

                # announce join to room
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


class JoinSessionBody(BaseModel):
    user_name: str
    part: str | None = None


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
        rows = (
            db.execute(
                select(DbSession)
                .where(DbSession.team_id == team_id)
                .order_by(DbSession.created_at.desc())
            )
            .scalars()
            .all()
        )
        return [{"id": r.id, "title": r.title, "status": r.status, "created_at": str(r.created_at)} for r in rows]


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    with SessionLocal() as db:
        s = db.get(DbSession, session_id)
        if not s:
            raise HTTPException(404, "session not found")
        return {"id": s.id, "team_id": s.team_id, "title": s.title, "status": s.status}


# Step2: join participant (first join => LEADER)
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

        # LEADER는 기본 broadcast 허용
        if p.role == "LEADER":
            g = DbGrant(session_id=session_id, user_name=p.id, can_broadcast=True)
            db.add(g)
            db.commit()

        return {
            "participant": {
                "id": p.id,
                "user_name": p.user_name,
                "part": p.part,
                "role": p.role,
            }
        }


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
        return [
            {"id": r.id, "user_name": r.user_name, "part": r.part, "role": r.role}
            for r in rows
        ]


# ---------- Permissions (Step2) ----------
class BroadcastPermissionBody(BaseModel):
    participant_id: str
    can_broadcast: bool = True


@app.post("/sessions/{session_id}/broadcast-permissions")
def set_broadcast_permission(session_id: str, body: BroadcastPermissionBody):
    with SessionLocal() as db:
        p = db.get(SessionParticipant, body.participant_id)
        if not p or p.session_id != session_id:
            raise HTTPException(404, "participant not found")

        existing = (
            db.execute(
                select(DbGrant).where(
                    DbGrant.session_id == session_id,
                    DbGrant.user_name == body.participant_id,  # participant_id stored here
                )
            )
            .scalar_one_or_none()
        )

        if existing:
            existing.can_broadcast = body.can_broadcast
            db.commit()
        else:
            g = DbGrant(session_id=session_id, user_name=body.participant_id, can_broadcast=body.can_broadcast)
            db.add(g)
            db.commit()

        return {"ok": True}


@app.get("/sessions/{session_id}/broadcast-permissions")
def list_broadcast_permissions(session_id: str):
    with SessionLocal() as db:
        rows = db.execute(select(DbGrant).where(DbGrant.session_id == session_id)).scalars().all()
        return [{"participant_id": r.user_name, "can_broadcast": r.can_broadcast} for r in rows]


# ---------- Presets ----------
class PresetCreate(BaseModel):
    team_id: str
    label: str
    payload: dict


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
        rows = (
            db.execute(select(DbPreset).where(DbPreset.team_id == team_id).order_by(DbPreset.created_at.desc()))
            .scalars()
            .all()
        )
        return [{"id": r.id, "label": r.label, "payload": r.payload} for r in rows]


# ---------- Broadcast (Step2 sender_id) ----------
class BroadcastCreate(BaseModel):
    session_id: str
    sender_id: str          # participant_id
    target: dict            # {"all":true} or {"parts":[...]}
    type: str               # TEXT/PRESET/...
    payload: dict


def _is_leader(db, sender_id: str) -> bool:
    p = db.get(SessionParticipant, sender_id)
    return bool(p and p.role == "LEADER")


def _can_user_broadcast(db, session_id: str, sender_id: str) -> bool:
    if _is_leader(db, sender_id):
        return True
    g = (
        db.execute(
            select(DbGrant).where(
                DbGrant.session_id == session_id,
                DbGrant.user_name == sender_id,  # participant_id stored here
            )
        )
        .scalar_one_or_none()
    )
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

        # sender info (for UI)
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


@app.get("/sessions/{session_id}/broadcasts")
def list_broadcasts(session_id: str, limit: int = 50):
    with SessionLocal() as db:
        rows = (
            db.execute(
                select(DbBroadcast)
                .where(DbBroadcast.session_id == session_id)
                .order_by(DbBroadcast.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": r.id,
                "sender_id": r.sender_id,
                "target": r.target,
                "type": r.type,
                "payload": r.payload,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]