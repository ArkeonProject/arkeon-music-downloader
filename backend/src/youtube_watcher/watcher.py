"""
YouTube Playlist Watcher - Clase principal para monitoreo continuo usando SQLite
"""

import logging
import os
import time
import shutil
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from .downloader import YouTubeDownloader
from .playlist_monitor import PlaylistMonitor
from .db.database import SessionLocal
from .db.models import Source, Track

logger = logging.getLogger(__name__)


class YouTubeWatcher:
    """
    Watcher principal que monitorea múltiples fuentes de YouTube y descarga
    automáticamente nuevas canciones.
    """

    def __init__(
        self,
        download_path: str,
        interval_ms: int = 60000,
        *,
        cookies_path: str | None = None,
        enable_sync_deletions: bool = True,  # Changed to True
        use_trash_folder: bool = True,
        trash_retention_days: int = 7,
    ):
        self.download_path = Path(download_path)
        self._download_path_raw = download_path
        self.interval_ms = interval_ms
        self.cookies_path = cookies_path
        self.enable_sync_deletions = enable_sync_deletions
        self.use_trash_folder = use_trash_folder
        self.trash_retention_days = trash_retention_days

        self._failed_retry_hours = 24
        self._navidrome_failed_retry_hours = int(
            os.getenv("NAVIDROME_SYNC_FAILED_RETRY_HOURS", "6")
        )
        self._navidrome_scan_cooldown_seconds = int(
            os.getenv("NAVIDROME_SCAN_COOLDOWN_SECONDS", "600")
        )
        self._last_navidrome_scan_at: datetime | None = None
        self.failed_downloads = {}  # In-memory tracking to prevent spam on failures
        self._trash_folder = self.download_path / ".trash"

        self.download_path.mkdir(parents=True, exist_ok=True)

        self.downloader = YouTubeDownloader(download_path, cookies_path=cookies_path)

        logger.info(
            f"Watcher inicializado. Directorio de descargas: {self.download_path}"
        )
        logger.info(f"Intervalo de observación: {interval_ms}ms")

    def update_cookies(self, cookies_path: str | None):
        """Actualizar el archivo de cookies y reiniciar el downloader local"""
        self.cookies_path = cookies_path
        self.downloader = YouTubeDownloader(
            str(self.download_path), cookies_path=self.cookies_path
        )
        if cookies_path:
            logger.info("🍪 Cookies establecidas localmente en el Watcher")
        else:
            logger.info("🍪 Cookies removidas del Watcher")

    def start(self):
        """Iniciar el watcher en bucle continuo"""
        logger.info("Iniciando monitor de fuentes en segundo plano...")

        errors = 0
        base_sleep = max(1.0, self.interval_ms / 1000.0)
        max_backoff = 300.0

        try:
            while True:
                try:
                    self._check_all_sources()
                    errors = 0
                    time.sleep(base_sleep)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    errors += 1
                    backoff = min(max_backoff, base_sleep * (2 ** min(errors, 8)))
                    logger.error(
                        f"Error en el watcher loop: {e}. Reintentando en {backoff:.1f}s"
                    )
                    time.sleep(backoff)
        except KeyboardInterrupt:
            logger.info("Watcher detenido")

    def _check_all_sources(self):
        with SessionLocal() as db:
            sources = db.query(Source).filter(Source.status == "active").all()

            if not sources:
                logger.debug("No hay fuentes activas para monitorizar.")
                return

            for source in sources:
                try:
                    logger.info(f"Verificando fuente: {source.name} ({source.url})")
                    monitor = PlaylistMonitor(
                        source.url, cookies_path=self.cookies_path
                    )
                    videos = monitor.get_playlist_videos()

                    for video_data in videos:
                        self._process_video(video_data, source.id, db)

                    if self.enable_sync_deletions and source.type == "playlist":
                        self._detect_and_remove_deleted_videos(videos, source.id, db)

                except Exception as e:
                    logger.error(f"Error procesando fuente {source.name}: {e}")

            if self.use_trash_folder and self.trash_retention_days > 0:
                self._cleanup_trash_folder()

    def _normalize_video_entry(self, video_data: Dict):
        raw_title = video_data.get("title")
        title = str(raw_title) if raw_title is not None else ""
        video_id = video_data.get("id")
        is_invalid = (
            not video_id
            or not title.strip()
            or "[Deleted" in title
            or "[Private" in title
        )

        artist = (
            video_data.get("artist")
            or video_data.get("channel")
            or video_data.get("uploader", "Unknown Artist")
        )
        upload_date = video_data.get("upload_date")
        formatted_date = None
        if upload_date and len(upload_date) == 8:
            formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        elif upload_date:
            formatted_date = upload_date

        return video_id, raw_title, title, artist, formatted_date, is_invalid

    def _process_video(self, video_data: Dict, source_id: int, db):
        video_id, raw_title, title, artist, published_at, is_invalid = (
            self._normalize_video_entry(video_data)
        )

        if is_invalid:
            return

        display_title = title or "Unknown Title"

        # Check DB
        existing_track = db.query(Track).filter(Track.youtube_id == video_id).first()

        if existing_track:
            if existing_track.download_status == "completed":
                self._sync_track_to_navidrome(
                    db,
                    existing_track,
                    source_id,
                    is_new_download=False,
                )
                return
            if existing_track.download_status == "ignored":
                return
            if existing_track.download_status == "pending":
                # It's pending, let's process it
                pass
            if existing_track.download_status == "failed":
                # Check retry rules
                if video_id in self.failed_downloads:
                    failed_at = self.failed_downloads[video_id]["failed_at"]
                    hours_since_fail = (
                        datetime.now() - failed_at
                    ).total_seconds() / 3600
                    if hours_since_fail < self._failed_retry_hours:
                        return
                    else:
                        logger.info(f"🔄 Reintentando descarga: {display_title}")

        # Try to download
        logger.info(f"Nueva canción detectada: {display_title}")

        # Ensure tracking DB record exists before parsing
        if not existing_track:
            existing_track = Track(
                youtube_id=video_id,
                title=display_title,
                artist=artist,
                published_at=published_at,
                source_id=source_id,
                download_status="pending",
            )
            db.add(existing_track)
            db.commit()
            db.refresh(existing_track)
        else:
            # Update missing fields if needed
            changed = False
            if not existing_track.artist and artist != "Unknown Artist":
                existing_track.artist = artist
                changed = True
            if not existing_track.published_at and published_at:
                existing_track.published_at = published_at
                changed = True
            if changed:
                db.commit()

        try:
            result = self.downloader.download_and_convert(video_data)
            if result and result.get("success"):
                filename = result.get("filename", "")
                existing_track.file_path = str(self.download_path / filename)
                existing_track.download_status = "completed"
                existing_track.downloaded_at = datetime.utcnow()
                existing_track.title = result.get("title", display_title)

                # Update published_at and artist if acquired during full download
                if result.get("published_at"):
                    existing_track.published_at = result.get("published_at")
                if result.get("artist"):
                    existing_track.artist = result.get("artist")

                self.failed_downloads.pop(video_id, None)
                db.commit()
                logger.info(f"✅ Descarga completada: {existing_track.title}")

                # Add to Navidrome playlists if configured.
                self._sync_track_to_navidrome(
                    db,
                    existing_track,
                    source_id,
                    is_new_download=True,
                )
            else:
                self._mark_failed(existing_track, video_id, "download_failed", db)
        except Exception as e:
            self._mark_failed(existing_track, video_id, str(e), db)

    def _mark_failed(self, track_record, video_id: str, reason: str, db):
        track_record.download_status = "failed"
        db.commit()
        retry_count = self.failed_downloads.get(video_id, {}).get("retry_count", 0) + 1
        self.failed_downloads[video_id] = {
            "failed_at": datetime.now(),
            "retry_count": retry_count,
        }
        logger.warning(
            f"⚠️ Descarga fallida: {track_record.title} (intento #{retry_count}) - {reason}"
        )

    def _detect_and_remove_deleted_videos(
        self, current_videos: list, source_id: int, db
    ):
        try:
            current_video_ids = set()
            for video_data in current_videos:
                video_id, _, _, _, _, is_invalid = self._normalize_video_entry(
                    video_data
                )
                # YouTube sometimes returns raw IDs with missing titles for deleted items
                # We specifically want to parse valid playlist members
                if video_id and not is_invalid:
                    current_video_ids.add(video_id)

            if not current_video_ids:
                return  # Playlist might be private or unreachable, do not mass-delete

            downloaded_tracks = (
                db.query(Track)
                .filter(
                    Track.source_id == source_id, Track.download_status == "completed"
                )
                .all()
            )

            downloaded_video_ids = {t.youtube_id for t in downloaded_tracks}

            # Find items in DB that are NO LONGER in the YouTube playlist
            deleted_video_ids = downloaded_video_ids - current_video_ids

            if not deleted_video_ids:
                return

            # Safety check: if the difference is > 30% of the library, something went wrong with the fetch
            # Do not mass purge to prevent catastrophic data loss on API errors
            total_downloaded = len(downloaded_video_ids)
            if len(deleted_video_ids) > (total_downloaded * 0.3):
                logger.warning(
                    f"⚠️ Alerta anti-purgado: Detectadas {len(deleted_video_ids)} canciones como borradas, lo cual supera el umbral de seguridad. Ignorando sincronización estricta por seguridad."
                )
                return

            logger.info(
                f"🗑️ Detectadas {len(deleted_video_ids)} canciones eliminadas de la playlist de YouTube. Sincronizando..."
            )

            for video_id in deleted_video_ids:
                track = db.query(Track).filter(Track.youtube_id == video_id).first()
                if track:
                    logger.info(f"Retirando canción huérfana: {track.title}")
                    if track.file_path:
                        self._remove_file(track.file_path, track.title)
                    db.delete(track)

            db.commit()

        except Exception as e:
            logger.error(f"Error procesando sincronización de eliminaciones: {e}")

    def _remove_file(self, file_path_str: str, title: str):
        try:
            file_path = Path(file_path_str)

            if not file_path.exists():
                logger.warning(f"Archivo no encontrado para eliminar: {file_path_str}")
                return

            if self.use_trash_folder:
                self._trash_folder.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = file_path.name
                name_parts = filename.rsplit(".", 1)
                trash_filename = (
                    f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                    if len(name_parts) == 2
                    else f"{filename}_{timestamp}"
                )

                trash_path = self._trash_folder / trash_filename
                shutil.move(str(file_path), str(trash_path))
                logger.info(f"🗑️ Movido a .trash: {title} -> {trash_filename}")
            else:
                file_path.unlink()
                logger.info(f"❌ Eliminado permanentemente: {title}")

        except Exception as e:
            logger.error(f"Error eliminando archivo {file_path_str}: {e}")

    def _cleanup_trash_folder(self):
        try:
            if not self._trash_folder.exists():
                return

            now = datetime.now()
            retention_delta = timedelta(days=self.trash_retention_days)

            for file_path in self._trash_folder.glob("*.flac"):
                try:
                    file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if now - file_date > retention_delta:
                        file_path.unlink()
                        logger.info(
                            f"🗑️ Auto-limpieza de .trash: eliminado {file_path.name}"
                        )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error en auto-limpieza de .trash: {e}")

    def _sync_track_to_navidrome(
        self, db, track: Track, source_id: int | None, *, is_new_download: bool
    ) -> None:
        """Synchronize one completed track to Navidrome once, with failure backoff.

        The old implementation retried every completed track on every polling
        cycle. Persisted sync state makes the watcher idempotent and prevents
        expensive playlist/search/scan traffic from repeating every minute.
        """
        if not self._navidrome_is_configured():
            return

        if track.navidrome_sync_status == "synced" and track.navidrome_song_id:
            return

        if (
            track.navidrome_sync_status == "failed"
            and track.navidrome_sync_attempted_at
        ):
            retry_at = track.navidrome_sync_attempted_at + timedelta(
                hours=self._navidrome_failed_retry_hours
            )
            if datetime.utcnow() < retry_at:
                logger.debug(
                    "Skipping Navidrome sync for '%s' until %s after previous failure",
                    track.title,
                    retry_at.isoformat(),
                )
                return

        try:
            from .navidrome_client import NavidromeClient

            client = NavidromeClient(
                os.environ["NAVIDROME_URL"],
                os.environ["NAVIDROME_USER"],
                os.environ["NAVIDROME_PASSWORD"],
            )
            navidrome_song_id = track.navidrome_song_id or self._find_navidrome_song_id(
                client, track.youtube_id, track.title
            )

            if (
                not navidrome_song_id
                and is_new_download
                and self._maybe_start_navidrome_scan(client)
            ):
                for _ in range(5):
                    time.sleep(3)
                    navidrome_song_id = self._find_navidrome_song_id(
                        client, track.youtube_id, track.title
                    )
                    if navidrome_song_id:
                        break

            track.navidrome_sync_attempted_at = datetime.utcnow()

            if not navidrome_song_id:
                self._mark_navidrome_sync_failed(
                    db,
                    track,
                    "song_not_found_in_navidrome",
                )
                logger.warning(
                    "Could not find '%s' (youtube_id=%s) in Navidrome; applying %sh backoff",
                    track.title,
                    track.youtube_id,
                    self._navidrome_failed_retry_hours,
                )
                return

            playlist_ids = self._resolve_target_playlists(
                db, client, source_id, is_new_download
            )
            if not self._add_song_to_playlists(
                client, playlist_ids, navidrome_song_id, track.title
            ):
                self._mark_navidrome_sync_failed(db, track, "playlist_update_failed")
                return

            track.navidrome_song_id = navidrome_song_id
            track.navidrome_sync_status = "synced"
            track.navidrome_sync_error = None
            track.navidrome_synced_at = datetime.utcnow()
            db.commit()
            logger.info("✅ Navidrome sync completed for '%s'", track.title)
        except Exception as e:
            self._mark_navidrome_sync_failed(db, track, str(e))
            logger.error(
                "Error syncing '%s' to Navidrome playlists: %s", track.title, e
            )

    def _navidrome_is_configured(self) -> bool:
        return all(
            os.getenv(key)
            for key in ("NAVIDROME_URL", "NAVIDROME_USER", "NAVIDROME_PASSWORD")
        )

    def _maybe_start_navidrome_scan(self, client) -> bool:
        now = datetime.utcnow()
        if self._last_navidrome_scan_at:
            elapsed = (now - self._last_navidrome_scan_at).total_seconds()
            if elapsed < self._navidrome_scan_cooldown_seconds:
                logger.debug(
                    "Skipping Navidrome scan; cooldown has %.1fs remaining",
                    self._navidrome_scan_cooldown_seconds - elapsed,
                )
                return False
        if client.start_scan():
            self._last_navidrome_scan_at = now
            return True
        return False

    def _mark_navidrome_sync_failed(self, db, track: Track, reason: str) -> None:
        track.navidrome_sync_status = "failed"
        track.navidrome_sync_error = reason[:500]
        track.navidrome_sync_attempted_at = datetime.utcnow()
        db.commit()

    def _resolve_target_playlists(
        self, db, client, source_id: int | None, is_new_download: bool
    ) -> dict[str, str]:
        playlists: dict[str, str] = {}
        global_playlist_name = os.getenv("NAVIDROME_GLOBAL_PLAYLIST_NAME")
        new_playlist_name = os.getenv("NAVIDROME_NEW_PLAYLIST_NAME", "Lo más nuevo")

        if global_playlist_name:
            playlist_id = client.ensure_playlist(global_playlist_name)
            if playlist_id:
                playlists[global_playlist_name] = playlist_id

        if source_id:
            source = db.query(Source).filter(Source.id == source_id).first()
            if source and source.type in ("playlist", "artist"):
                playlist_id = source.navidrome_playlist_id
                if playlist_id and not client.playlist_exists(playlist_id):
                    logger.warning(
                        "Stored Navidrome playlist ID '%s' for source '%s' is stale. Re-linking by name.",
                        playlist_id,
                        source.name,
                    )
                    source.navidrome_playlist_id = None
                    db.commit()
                    playlist_id = None

                if not playlist_id:
                    playlist_id = client.ensure_playlist(source.name)
                    if playlist_id:
                        source.navidrome_playlist_id = playlist_id
                        db.commit()

                if playlist_id:
                    playlists[source.name] = playlist_id

        if is_new_download and new_playlist_name:
            playlist_id = client.ensure_playlist(new_playlist_name)
            if playlist_id:
                playlists[new_playlist_name] = playlist_id

        return playlists

    def _add_song_to_playlists(
        self, client, playlists: dict[str, str], song_id: str, title: str
    ) -> bool:
        """Batch playlist membership checks and add a song only where missing."""
        for playlist_label, playlist_id in playlists.items():
            current_songs = client.get_playlist_songs(playlist_id)
            if current_songs is None:
                logger.warning(
                    "Could not fetch songs for Navidrome playlist '%s' (%s); skipping sync for '%s'",
                    playlist_label,
                    playlist_id,
                    title,
                )
                return False

            current_song_ids = {s.get("id") for s in current_songs}
            if song_id in current_song_ids:
                continue

            if client.update_playlist(playlist_id, song_ids_to_add=[song_id]):
                logger.info(
                    "✅ Added '%s' to Navidrome playlist '%s'", title, playlist_label
                )
            else:
                logger.warning(
                    "Failed to add '%s' to Navidrome playlist '%s'",
                    title,
                    playlist_label,
                )
                return False

        return True

    @staticmethod
    def _normalize_string(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "")
        return (
            "".join(ch for ch in normalized if not unicodedata.combining(ch))
            .strip()
            .casefold()
        )

    def _find_navidrome_song_id(
        self, client, youtube_id: str, title: str
    ) -> str | None:
        songs = client.search_songs(youtube_id)
        if not songs:
            songs = client.search_songs(title)

        normalized_title = self._normalize_string(title)
        for song in songs:
            comment = str(song.get("comment", ""))
            song_title = str(song.get("title", ""))
            if youtube_id and youtube_id in comment:
                return song.get("id")
            if self._normalize_string(song_title) == normalized_title:
                return song.get("id")

        return None
