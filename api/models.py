import uuid
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.db import Base

def gen_id() -> str:
    return str(uuid.uuid4())

class Team(Base):
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    name: Mapped[str] = mapped_column(String, nullable=False)

class Invite(Base):
    __tablename__ = "invites"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("teams.id"), nullable=False)
    remain: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

class TeamMember(Base):
    __tablename__ = "team_members"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("teams.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    part: Mapped[str] = mapped_column(String, nullable=True)

from sqlalchemy import DateTime, Boolean, JSON
from sqlalchemy.sql import func

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("teams.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")  # ACTIVE/CLOSED
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Grant(Base):
    __tablename__ = "grants"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False)
    user_name: Mapped[str] = mapped_column(String, nullable=False)   # MVP: user_id 대신 name
    can_broadcast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class BroadcastPreset(Base):
    __tablename__ = "broadcast_presets"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("teams.id"), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)  # {type:"TEXT", text:"엔딩 컷"} 등
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Broadcast(Base):
    __tablename__ = "broadcasts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id"), nullable=False)
    sender_name: Mapped[str] = mapped_column(String, nullable=False)
    target: Mapped[dict] = mapped_column(JSON, nullable=False)   # {"all":true} or {"parts":["VOCAL","DRUM"]}
    type: Mapped[str] = mapped_column(String, nullable=False)    # TEXT / PRESET
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())