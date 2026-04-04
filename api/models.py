import uuid
from datetime import datetime, date

from sqlalchemy import String, Text, Integer, Boolean, Date, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ── Songs ──────────────────────────────────────────────

class Song(Base):
    __tablename__ = "songs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    artist: Mapped[str | None] = mapped_column(String(200), nullable=True)
    default_key: Mapped[str | None] = mapped_column(String(10), nullable=True)
    keys: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["A", "Bb", "G"]
    lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    references: Mapped[list["SongReference"]] = relationship(back_populates="song", cascade="all, delete-orphan")
    sheets: Mapped[list["SongSheet"]] = relationship(back_populates="song", cascade="all, delete-orphan")


class SongReference(Base):
    __tablename__ = "song_references"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    song_id: Mapped[str] = mapped_column(String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    channel_id: Mapped[str | None] = mapped_column(String, ForeignKey("crawl_channels.id"), nullable=True)
    youtube_url: Mapped[str] = mapped_column(String(500), nullable=False)
    youtube_video_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    key: Mapped[str | None] = mapped_column(String(10), nullable=True)
    trust_level: Mapped[str] = mapped_column(String(10), default="MEDIUM")
    source: Mapped[str] = mapped_column(String(10), default="MANUAL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    song: Mapped["Song"] = relationship(back_populates="references")
    channel: Mapped["CrawlChannel | None"] = relationship(back_populates="references")


class SongSheet(Base):
    __tablename__ = "song_sheets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    song_id: Mapped[str] = mapped_column(String, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String, ForeignKey("song_references.id"), nullable=True)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # PDF / IMAGE
    uploaded_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    song: Mapped["Song"] = relationship(back_populates="sheets")


# ── Contis ─────────────────────────────────────────────

class Conti(Base):
    __tablename__ = "contis"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    items: Mapped[list["ContiItem"]] = relationship(
        back_populates="conti", cascade="all, delete-orphan", order_by="ContiItem.order_num"
    )


class ContiItem(Base):
    __tablename__ = "conti_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    conti_id: Mapped[str] = mapped_column(String, ForeignKey("contis.id", ondelete="CASCADE"), nullable=False)
    song_id: Mapped[str] = mapped_column(String, ForeignKey("songs.id"), nullable=False)
    order_num: Mapped[int] = mapped_column(Integer, nullable=False)
    slot_label: Mapped[str] = mapped_column(String(50), default="")
    use_key: Mapped[str | None] = mapped_column(String(10), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String, ForeignKey("song_references.id"), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conti: Mapped["Conti"] = relationship(back_populates="items")
    song: Mapped["Song"] = relationship()
    reference: Mapped["SongReference | None"] = relationship()


# ── Crawl ──────────────────────────────────────────────

class CrawlChannel(Base):
    __tablename__ = "crawl_channels"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    youtube_channel_url: Mapped[str] = mapped_column(String(500), nullable=False)
    youtube_channel_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    trust_level: Mapped[str] = mapped_column(String(10), default="HIGH")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    references: Mapped[list["SongReference"]] = relationship(back_populates="channel")


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    channel_id: Mapped[str] = mapped_column(String, ForeignKey("crawl_channels.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    videos_found: Mapped[int] = mapped_column(Integer, default=0)
    songs_added: Mapped[int] = mapped_column(Integer, default=0)
    refs_added: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    channel: Mapped["CrawlChannel"] = relationship()


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    youtube_video_id: Mapped[str] = mapped_column(String(20), nullable=False)
    youtube_url: Mapped[str] = mapped_column(String(500), nullable=False)
    video_title: Mapped[str] = mapped_column(String(500), nullable=False)
    channel_id: Mapped[str] = mapped_column(String, ForeignKey("crawl_channels.id"), nullable=False)
    parsed_song_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    suggested_song_id: Mapped[str | None] = mapped_column(String, ForeignKey("songs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    channel: Mapped["CrawlChannel"] = relationship()
    suggested_song: Mapped["Song | None"] = relationship()

    __table_args__ = (
        Index("ix_review_queue_status", "status"),
    )
