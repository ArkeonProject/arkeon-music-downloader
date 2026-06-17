from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (Index("ix_sources_status", "status"),)

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, default="playlist")  # playlist, artist, channel, track
    status = Column(String, default="active")  # active, paused
    navidrome_playlist_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tracks = relationship("Track", back_populates="source", cascade="all, delete")


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        Index("ix_tracks_source_status", "source_id", "download_status"),
        Index("ix_tracks_navidrome_sync_status", "navidrome_sync_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    youtube_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    file_path = Column(String, nullable=True)
    download_status = Column(
        String, default="pending"
    )  # pending, completed, failed, ignored
    downloaded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(String, nullable=True)  # YouTube publication date/year
    artist = Column(String, nullable=True)  # YouTube channel/uploader

    # Navidrome synchronization state. This prevents re-processing every
    # completed track on every watcher poll and allows long backoff for tracks
    # Navidrome cannot resolve yet.
    navidrome_song_id = Column(String, nullable=True)
    navidrome_synced_at = Column(DateTime, nullable=True)
    navidrome_sync_status = Column(
        String, nullable=True
    )  # pending, synced, failed, skipped
    navidrome_sync_error = Column(String, nullable=True)
    navidrome_sync_attempted_at = Column(DateTime, nullable=True)

    source = relationship("Source", back_populates="tracks")
