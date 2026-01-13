# api/models.py
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def _uuid():
    return str(uuid.uuid4())


class Team(Base):
    __tablename__ = "teams"
    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Invite(Base):
    __tablename__ = "invites"
    code = Column(String, primary_key=True)  # short code
    team_id = Column(String, ForeignKey("teams.id"), index=True, nullable=False)
    remain = Column(Integer, nullable=False, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(String, primary_key=True, default=_uuid)
    team_id = Column(String, ForeignKey("teams.id"), index=True, nullable=False)
    name = Column(String, nullable=False)
    part = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=_uuid)
    team_id = Column(String, ForeignKey("teams.id"), index=True, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE / CLOSED
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SessionParticipant(Base):
    __tablename__ = "session_participants"
    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), index=True, nullable=False)
    user_name = Column(String, nullable=False)
    part = Column(String, nullable=True)

    # Step2: 첫 참가자 LEADER
    role = Column(String, nullable=False, default="MEMBER")  # LEADER | MEMBER

    joined_at = Column(DateTime(timezone=True), server_default=func.now())


class Grant(Base):
    __tablename__ = "grants"
    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), index=True, nullable=False)

    # MVP 유지: 컬럼 이름은 user_name 이지만, Step2부터 participant_id 를 저장합니다.
    user_name = Column(String, nullable=False, index=True)  # participant_id

    can_broadcast = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BroadcastPreset(Base):
    __tablename__ = "broadcast_presets"
    id = Column(String, primary_key=True, default=_uuid)
    team_id = Column(String, ForeignKey("teams.id"), index=True, nullable=False)
    label = Column(String, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Broadcast(Base):
    __tablename__ = "broadcasts"
    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), index=True, nullable=False)

    # Step2: sender_id 기반
    sender_id = Column(String, nullable=False)  # participant_id

    target = Column(JSON, nullable=False, default=dict)  # {"all":true} or {"parts":[...]}
    type = Column(String, nullable=False, default="TEXT")  # TEXT/PRESET/...
    payload = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())