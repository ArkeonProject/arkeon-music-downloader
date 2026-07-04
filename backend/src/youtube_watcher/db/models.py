from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, default="playlist") # playlist, artist, channel, track
    status = Column(String, default="active") # active, paused
    navidrome_playlist_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tracks = relationship("Track", back_populates="source", cascade="all, delete")

class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    youtube_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    file_path = Column(String, nullable=True)
    download_status = Column(String, default="pending") # pending, completed, failed
    downloaded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(String, nullable=True) # YouTube publication date/year
    artist = Column(String, nullable=True) # YouTube channel/uploader
    discovery_reason = Column(String, nullable=True)

    source = relationship("Source", back_populates="tracks")


class SourceItem(Base):
    __tablename__ = "source_items"
    __table_args__ = (
        UniqueConstraint("source_id", "youtube_id", name="uq_source_item_source_youtube"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    youtube_id = Column(String, nullable=False, index=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=True)
    title = Column(String, nullable=True)
    position = Column(Integer, nullable=True)
    status = Column(String, default="present") # present, removed
    discovery_reason = Column(String, nullable=False, default="initial_import")
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
