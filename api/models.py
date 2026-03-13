# api/models.py
from api.db import Base
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
import uuid

def _uuid():
    return str(uuid.uuid4())

DEFAULT_PARTS = ["보컬", "피아노", "신디", "기타", "베이스", "드럼", "리더", "설교자", "음향", "영상"]

class Team(Base):
    __tablename__ = "teams"
    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Invite(Base):
    __tablename__ = "invites"
    code = Column(String, primary_key=True)
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
    status = Column(String, nullable=False, default="ACTIVE")
    # ✅ Step3: 세션별 파트 목록 커스터마이징
    parts = Column(JSON, nullable=False, default=lambda: DEFAULT_PARTS.copy())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SessionParticipant(Base):
    __tablename__ = "session_participants"
    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), index=True, nullable=False)
    user_name = Column(String, nullable=False)
    part = Column(String, nullable=True)
    role = Column(String, nullable=False, default="MEMBER")  # LEADER|MEMBER
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

class Grant(Base):
    __tablename__ = "grants"
    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), index=True, nullable=False)
    # participant_id 저장 (컬럼명 유지)
    user_name = Column(String, nullable=False, index=True)
    can_broadcast = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BroadcastPreset(Base):
    __tablename__ = "broadcast_presets"
    id = Column(String, primary_key=True, default=_uuid)
    team_id = Column(String, ForeignKey("teams.id"), index=True, nullable=False)
    # ✅ Step3: title(버튼명)
    title = Column(String, nullable=False)
    # ✅ Step3: payload.text(전송 내용). 비어있으면 title을 전송
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Broadcast(Base):
    __tablename__ = "broadcasts"
    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("sessions.id"), index=True, nullable=False)
    sender_id = Column(String, nullable=False)  # participant_id
    target = Column(JSON, nullable=False, default=dict)
    type = Column(String, nullable=False, default="TEXT")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())