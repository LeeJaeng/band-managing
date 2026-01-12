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
