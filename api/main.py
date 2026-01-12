from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import uuid

from sqlalchemy import select
from api.db import SessionLocal, engine, Base
from api.models import Team, Invite, TeamMember

# create tables (MVP)
Base.metadata.create_all(bind=engine)

app = FastAPI()

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

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            await ws.send_text(f"echo: {msg}")
    except WebSocketDisconnect:
        pass
