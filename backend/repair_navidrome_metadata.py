#!/usr/bin/env python3
"""Repair FLAC YouTube metadata and Navidrome sync state for existing tracks.

This is intentionally a one-shot operator script, not part of the watcher loop.
It can:
  1. Add `comment=youtube_id=<id>` metadata to existing FLAC files.
  2. Ask Navidrome for matching songs and persist `navidrome_song_id`.
  3. Optionally add resolved songs to the global and source playlists in batches.

Usage examples:
  python backend/repair_navidrome_metadata.py --dry-run
  python backend/repair_navidrome_metadata.py --write-tags --sync-navidrome
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from mutagen.flac import FLAC

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from youtube_watcher.db.database import (
    SessionLocal,
    ensure_database_schema,
)  # noqa: E402
from youtube_watcher.db.models import Source, Track  # noqa: E402
from youtube_watcher.navidrome_client import NavidromeClient  # noqa: E402
from youtube_watcher.watcher import YouTubeWatcher  # noqa: E402


def _write_youtube_comment(track: Track, dry_run: bool) -> bool:
    if not track.file_path:
        return False
    path = Path(track.file_path)
    if not path.exists() or path.suffix.lower() != ".flac":
        return False

    audio = FLAC(path)
    expected = f"youtube_id={track.youtube_id}"
    comments = [str(v) for v in audio.get("comment", [])]
    if expected in comments:
        return False

    if dry_run:
        print(f"DRY-RUN tag {path}: add comment={expected}")
        return True

    audio["comment"] = expected
    if track.title:
        audio["title"] = track.title
    if track.artist:
        audio["artist"] = track.artist
    if track.published_at:
        audio["date"] = track.published_at
        audio["originalyear"] = track.published_at
    audio.save()
    print(f"Tagged {path}: {expected}")
    return True


def _client_from_env() -> NavidromeClient | None:
    url = os.getenv("NAVIDROME_URL")
    user = os.getenv("NAVIDROME_USER")
    password = os.getenv("NAVIDROME_PASSWORD")
    if not all([url, user, password]):
        return None
    return NavidromeClient(url, user, password)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview work without writing files or DB changes",
    )
    parser.add_argument(
        "--write-tags",
        action="store_true",
        help="Write youtube_id comments into existing FLAC files",
    )
    parser.add_argument(
        "--sync-navidrome",
        action="store_true",
        help="Resolve Navidrome song IDs and update playlists",
    )
    args = parser.parse_args()

    ensure_database_schema()
    client = _client_from_env() if args.sync_navidrome else None
    watcher = (
        YouTubeWatcher(os.getenv("DOWNLOAD_PATH", str(ROOT / "downloads")))
        if client
        else None
    )

    tagged = resolved = failed = 0
    with SessionLocal() as db:
        tracks = db.query(Track).filter(Track.download_status == "completed").all()
        sources = {s.id: s for s in db.query(Source).all()}
        playlist_cache: dict[str, set[str]] = {}

        for track in tracks:
            if args.write_tags and _write_youtube_comment(track, args.dry_run):
                tagged += 1

            if not client or not watcher:
                continue

            song_id = track.navidrome_song_id or watcher._find_navidrome_song_id(
                client, track.youtube_id, track.title
            )
            track.navidrome_sync_attempted_at = datetime.utcnow()
            if not song_id:
                track.navidrome_sync_status = "failed"
                track.navidrome_sync_error = "song_not_found_in_navidrome"
                failed += 1
                continue

            track.navidrome_song_id = song_id
            track.navidrome_sync_status = "synced"
            track.navidrome_sync_error = None
            track.navidrome_synced_at = datetime.utcnow()
            resolved += 1

            source = sources.get(track.source_id)
            playlist_ids: dict[str, str] = {}
            global_name = os.getenv("NAVIDROME_GLOBAL_PLAYLIST_NAME")
            if global_name:
                pid = client.ensure_playlist(global_name)
                if pid:
                    playlist_ids[global_name] = pid
            if source and source.type in ("playlist", "artist"):
                pid = source.navidrome_playlist_id or client.ensure_playlist(
                    source.name
                )
                if pid:
                    source.navidrome_playlist_id = pid
                    playlist_ids[source.name] = pid

            for label, pid in playlist_ids.items():
                if pid not in playlist_cache:
                    songs = client.get_playlist_songs(pid)
                    if songs is None:
                        continue
                    playlist_cache[pid] = {s.get("id") for s in songs}
                if song_id not in playlist_cache[pid]:
                    if args.dry_run:
                        print(f"DRY-RUN add {track.title!r} to {label}")
                    elif client.update_playlist(pid, song_ids_to_add=[song_id]):
                        playlist_cache[pid].add(song_id)

        if args.dry_run:
            db.rollback()
        else:
            db.commit()

    print(
        {
            "tracks": len(tracks),
            "tagged": tagged,
            "resolved": resolved,
            "failed": failed,
            "dry_run": args.dry_run,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
