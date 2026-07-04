from pathlib import Path
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from youtube_watcher.db.models import Base, Source, SourceItem
from youtube_watcher.discovery import INITIAL_IMPORT, PLAYLIST_DELTA
from youtube_watcher.sync_service import sync_source_once


def make_session_factory(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sync.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def add_source(SessionLocal, source_id=1):
    with SessionLocal() as db:
        db.add(Source(id=source_id, url="https://youtube.test/playlist", name="YT", type="playlist", status="active"))
        db.commit()


def source_items(SessionLocal):
    with SessionLocal() as db:
        return {item.youtube_id: item.discovery_reason for item in db.query(SourceItem).all()}


def test_first_sync_snapshots_playlist_and_processes_as_initial_import(tmp_path):
    SessionLocal = make_session_factory(tmp_path)
    add_source(SessionLocal)
    watcher = Mock()

    with patch("youtube_watcher.sync_service.SessionLocal", SessionLocal), \
         patch("youtube_watcher.sync_service.PlaylistMonitor") as monitor_cls:
        monitor_cls.return_value.get_playlist_videos.return_value = [
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B"},
        ]

        result = sync_source_once(1, watcher=watcher)

    assert result["initial_import"] is True
    assert result["new_items"] == 2
    assert result["queued_downloads"] == 2
    assert watcher._process_video.call_count == 2
    for call in watcher._process_video.call_args_list:
        assert call.kwargs["discovery_reason"] == INITIAL_IMPORT
    assert source_items(SessionLocal) == {"a": INITIAL_IMPORT, "b": INITIAL_IMPORT}


def test_second_sync_processes_only_new_playlist_delta(tmp_path):
    SessionLocal = make_session_factory(tmp_path)
    add_source(SessionLocal)

    with patch("youtube_watcher.sync_service.SessionLocal", SessionLocal), \
         patch("youtube_watcher.sync_service.PlaylistMonitor") as monitor_cls:
        monitor_cls.return_value.get_playlist_videos.return_value = [
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B"},
        ]
        sync_source_once(1, watcher=Mock())

    watcher = Mock()
    with patch("youtube_watcher.sync_service.SessionLocal", SessionLocal), \
         patch("youtube_watcher.sync_service.PlaylistMonitor") as monitor_cls:
        monitor_cls.return_value.get_playlist_videos.return_value = [
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B"},
            {"id": "c", "title": "C"},
        ]
        result = sync_source_once(1, watcher=watcher)

    assert result["initial_import"] is False
    assert result["new_items"] == 1
    assert result["queued_downloads"] == 1
    assert source_items(SessionLocal)["c"] == PLAYLIST_DELTA
    watcher._process_video.assert_called_once()
    _, kwargs = watcher._process_video.call_args
    assert kwargs["discovery_reason"] == PLAYLIST_DELTA
