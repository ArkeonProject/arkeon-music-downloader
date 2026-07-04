"""One-shot source synchronization with playlist delta tracking."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from .db.database import SessionLocal
from .db.models import Source, SourceItem, Track
from .discovery import INITIAL_IMPORT, PLAYLIST_DELTA
from .playlist_monitor import PlaylistMonitor
from .watcher import YouTubeWatcher

logger = logging.getLogger(__name__)


def _cookies_path() -> str | None:
    configured = os.getenv("COOKIES_PATH") or os.getenv("COOKIES_FILE")
    if configured and os.path.exists(configured):
        return configured
    for candidate in ("/data/cookies.txt",):
        if os.path.exists(candidate):
            return candidate
    return None


def normalize_video_entry(video_data: dict[str, Any]) -> tuple[str | None, str, bool]:
    """Return `(youtube_id, title, invalid)` for a yt-dlp playlist entry."""
    youtube_id = video_data.get("id")
    raw_title = video_data.get("title")
    title = str(raw_title) if raw_title is not None else ""
    invalid = (
        not youtube_id
        or not title.strip()
        or "[Deleted" in title
        or "[Private" in title
    )
    return youtube_id, title, invalid


def _get_watcher(watcher: YouTubeWatcher | None = None) -> YouTubeWatcher:
    if watcher is not None:
        return watcher
    download_path = os.getenv("DOWNLOAD_PATH", "./downloads")
    interval_ms = int(os.getenv("OBSERVER_INTERVAL_MS", "60000"))
    return YouTubeWatcher(
        download_path=download_path,
        interval_ms=interval_ms,
        cookies_path=_cookies_path(),
        enable_sync_deletions=str(os.getenv("ENABLE_SYNC_DELETIONS", "true")).lower() == "true",
        use_trash_folder=str(os.getenv("USE_TRASH_FOLDER", "true")).lower() == "true",
        trash_retention_days=int(os.getenv("TRASH_RETENTION_DAYS", "7")),
    )


def sync_source_once(source_id: int, *, watcher: YouTubeWatcher | None = None) -> dict[str, Any]:
    """Sync one source once, processing only true playlist deltas as latest-eligible."""
    now = datetime.utcnow()
    with SessionLocal() as db:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return {"status": "not_found", "source_id": source_id}
        if source.status != "active":
            return {"status": "skipped", "reason": "source_not_active", "source_id": source_id}
        if source.type not in ("playlist", "artist", "channel"):
            return {"status": "skipped", "reason": "unsupported_source_type", "source_id": source_id}

        monitor = PlaylistMonitor(source.url, cookies_path=_cookies_path())
        videos = monitor.get_playlist_videos()
        if not videos:
            return {"status": "ok", "source_id": source_id, "seen": 0, "new_items": 0, "queued_downloads": 0, "skipped_existing": 0, "removed": 0}

        existing_items = {
            item.youtube_id: item
            for item in db.query(SourceItem).filter(SourceItem.source_id == source_id).all()
        }
        is_initial_import = len(existing_items) == 0
        seen_ids: set[str] = set()
        videos_to_process: list[tuple[dict[str, Any], str]] = []
        new_items = 0
        skipped_existing = 0

        for position, video_data in enumerate(videos):
            youtube_id, title, invalid = normalize_video_entry(video_data)
            if invalid or not youtube_id:
                continue
            seen_ids.add(youtube_id)
            item = existing_items.get(youtube_id)
            if item is None:
                reason = INITIAL_IMPORT if is_initial_import else PLAYLIST_DELTA
                track = db.query(Track).filter(Track.youtube_id == youtube_id).first()
                item = SourceItem(
                    source_id=source_id,
                    youtube_id=youtube_id,
                    track_id=track.id if track else None,
                    title=title,
                    position=position,
                    status="present",
                    discovery_reason=reason,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                db.add(item)
                new_items += 1
                if reason in (INITIAL_IMPORT, PLAYLIST_DELTA):
                    videos_to_process.append((video_data, reason))
            else:
                item.title = title
                item.position = position
                item.status = "present"
                item.last_seen_at = now
                skipped_existing += 1

        removed = 0
        for youtube_id, item in existing_items.items():
            if youtube_id not in seen_ids and item.status != "removed":
                item.status = "removed"
                item.last_seen_at = now
                removed += 1

        db.commit()

    active_watcher = _get_watcher(watcher)
    downloaded = 0
    failed = 0
    for video_data, reason in videos_to_process:
        try:
            with SessionLocal() as bg_db:
                active_watcher._process_video(
                    video_data,
                    source_id=source_id,
                    db=bg_db,
                    discovery_reason=reason,
                )
            downloaded += 1
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error processing playlist delta for source %s: %s", source_id, exc)
            failed += 1

    return {
        "status": "ok",
        "source_id": source_id,
        "initial_import": is_initial_import,
        "seen": len(seen_ids),
        "new_items": new_items,
        "queued_downloads": len(videos_to_process),
        "downloaded": downloaded,
        "failed": failed,
        "skipped_existing": skipped_existing,
        "removed": removed,
    }


def sync_all_sources(*, watcher: YouTubeWatcher | None = None) -> dict[str, Any]:
    """Sync all active playlist-like sources once."""
    with SessionLocal() as db:
        source_ids = [
            source.id
            for source in db.query(Source).filter(
                Source.status == "active",
                Source.type.in_(["playlist", "artist", "channel"]),
            ).all()
        ]

    results = [sync_source_once(source_id, watcher=watcher) for source_id in source_ids]
    return {
        "status": "ok",
        "sources": len(source_ids),
        "results": results,
        "new_items": sum(r.get("new_items", 0) for r in results),
        "queued_downloads": sum(r.get("queued_downloads", 0) for r in results),
        "downloaded": sum(r.get("downloaded", 0) for r in results),
        "failed": sum(r.get("failed", 0) for r in results),
    }
