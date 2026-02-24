"""
YouTube Playlist Watcher - Clase principal para monitoreo continuo usando SQLite
"""

import logging
import time
import shutil
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
        enable_sync_deletions: bool = False,
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
        self.failed_downloads = {}  # In-memory tracking to prevent spam on failures
        self._trash_folder = self.download_path / ".trash"

        self.download_path.mkdir(parents=True, exist_ok=True)

        self.downloader = YouTubeDownloader(download_path, cookies_path=cookies_path)

        logger.info(f"Watcher inicializado. Directorio de descargas: {self.download_path}")
        logger.info(f"Intervalo de observación: {interval_ms}ms")

    def update_cookies(self, cookies_path: str | None):
        """Actualizar el archivo de cookies y reiniciar el downloader local"""
        self.cookies_path = cookies_path
        self.downloader = YouTubeDownloader(str(self.download_path), cookies_path=self.cookies_path)
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
                    logger.error(f"Error en el watcher loop: {e}. Reintentando en {backoff:.1f}s")
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
                    monitor = PlaylistMonitor(source.url, cookies_path=self.cookies_path)
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
        is_invalid = not video_id or not title.strip() or "[Deleted" in title
        return video_id, raw_title, title, is_invalid

    def _process_video(self, video_data: Dict, source_id: int, db):
        video_id, raw_title, title, is_invalid = self._normalize_video_entry(video_data)

        if is_invalid:
            return

        display_title = title or "Unknown Title"

        # Check DB
        existing_track = db.query(Track).filter(Track.youtube_id == video_id).first()
        
        if existing_track:
            if existing_track.download_status == "completed":
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
                    hours_since_fail = (datetime.now() - failed_at).total_seconds() / 3600
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
                source_id=source_id,
                download_status="pending"
            )
            db.add(existing_track)
            db.commit()
            db.refresh(existing_track)

        try:
            result = self.downloader.download_and_convert(video_data)
            if result and result.get("success"):
                filename = result.get("filename", "")
                existing_track.file_path = str(self.download_path / filename)
                existing_track.download_status = "completed"
                existing_track.downloaded_at = datetime.utcnow()
                existing_track.title = result.get("title", display_title)
                
                self.failed_downloads.pop(video_id, None)
                db.commit()
                logger.info(f"✅ Descarga completada: {existing_track.title}")
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
            "retry_count": retry_count
        }
        logger.warning(f"⚠️ Descarga fallida: {track_record.title} (intento #{retry_count}) - {reason}")

    def _detect_and_remove_deleted_videos(self, current_videos: list, source_id: int, db):
        try:
            current_video_ids = set()
            for video_data in current_videos:
                video_id, _, _, is_invalid = self._normalize_video_entry(video_data)
                if not is_invalid:
                    current_video_ids.add(video_id)

            downloaded_tracks = db.query(Track).filter(Track.source_id == source_id, Track.download_status == "completed").all()
            downloaded_video_ids = {t.youtube_id for t in downloaded_tracks}

            total_downloaded = len(downloaded_video_ids)
            total_current = len(current_video_ids)

            if total_downloaded > 0 and total_current < total_downloaded * 0.8:
                return

            deleted_video_ids = downloaded_video_ids - current_video_ids

            if not deleted_video_ids:
                return

            deletion_threshold = max(5, int(total_downloaded * 0.1))
            if len(deleted_video_ids) > deletion_threshold:
                return

            logger.info(f"🗑️ Detectadas {len(deleted_video_ids)} canciones eliminadas de la playlist")

            for video_id in deleted_video_ids:
                track = db.query(Track).filter(Track.youtube_id == video_id).first()
                if track and track.file_path:
                    self._remove_file(track.file_path, track.title)
                    db.delete(track)
            
            db.commit()

        except Exception as e:
            logger.error(f"Error detectando videos eliminados: {e}")

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
                trash_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}" if len(name_parts) == 2 else f"{filename}_{timestamp}"
                
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
                        logger.info(f"🗑️ Auto-limpieza de .trash: eliminado {file_path.name}")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error en auto-limpieza de .trash: {e}")
