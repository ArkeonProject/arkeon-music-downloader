"""
YouTube Playlist Watcher - Clase principal para monitoreo continuo
"""

import logging
import time
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from .downloader import YouTubeDownloader
from .playlist_monitor import PlaylistMonitor

logger = logging.getLogger(__name__)


class YouTubeWatcher:
    """
    Watcher principal que monitorea una playlist de YouTube y descarga
    automáticamente nuevas canciones.
    """

    def __init__(
        self,
        playlist_url: str,
        download_path: str,
        interval_ms: int = 60000,
        *,
        cookies_path: str | None = None,
        enable_sync_deletions: bool = False,
        use_trash_folder: bool = True,
        trash_retention_days: int = 7,
    ):
        """
        Inicializar el watcher.

        Args:
            playlist_url: URL de la playlist de YouTube
            download_path: Directorio donde guardar archivos FLAC
            interval_ms: Intervalo de verificación en milisegundos
            cookies_path: Ruta al archivo de cookies
            enable_sync_deletions: Habilitar sincronización bidireccional
            use_trash_folder: Usar carpeta .trash en lugar de eliminar
            trash_retention_days: Días de retención en .trash (0=nunca)
        """
        self.playlist_url = playlist_url
        self.download_path = Path(download_path)
        self._download_path_raw = download_path
        self.interval_ms = interval_ms
        self.enable_sync_deletions = enable_sync_deletions
        self.use_trash_folder = use_trash_folder
        self.trash_retention_days = trash_retention_days
        self.downloaded_videos = set()
        self.downloads = {}  # video_id -> {filename, downloaded_at, title, artist}
        self.failed_downloads = (
            {}
        )  # video_id -> {reason, failed_at, title, retry_count}
        self._failed_retry_hours = (
            24  # Reintentar descargas fallidas después de X horas
        )
        self._state_file = self.download_path / ".downloaded.json"
        self._trash_folder = self.download_path / ".trash"

        # Crear directorio de descargas si no existe
        self.download_path.mkdir(parents=True, exist_ok=True)

        # Inicializar componentes
        self.monitor = PlaylistMonitor(playlist_url, cookies_path=cookies_path)
        self.downloader = YouTubeDownloader(download_path, cookies_path=cookies_path)

        # Cargar estado previo de descargas
        self._load_state()

        logger.info(f"Watcher iniciado para playlist: {playlist_url}")
        logger.info(f"Directorio de descargas: {self.download_path}")
        logger.info(f"Intervalo de observación: {interval_ms}ms")
        if self.enable_sync_deletions:
            logger.info(
                f"Sincronización bidireccional habilitada "
                f"(trash={self.use_trash_folder}, retention={self.trash_retention_days}d)"
            )

    def start(self):
        """Iniciar el watcher en bucle continuo"""
        logger.info("Iniciando monitoreo de playlist...")

        errors = 0
        base_sleep = max(1.0, self.interval_ms / 1000.0)
        max_backoff = 300.0  # 5 minutos

        try:
            while True:
                try:
                    self._check_playlist()
                    errors = 0
                    time.sleep(base_sleep)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    errors += 1
                    backoff = min(max_backoff, base_sleep * (2 ** min(errors, 8)))
                    logger.error(
                        f"Error en el watcher: {e}. Reintentando en {backoff:.1f}s"
                    )
                    time.sleep(backoff)
        except KeyboardInterrupt:
            logger.info("Watcher detenido por el usuario")

    def _check_playlist(self):
        """Verificar playlist para nuevas canciones"""
        try:
            logger.info("Verificando playlist para nuevas canciones...")

            # Obtener videos de la playlist
            videos = self.monitor.get_playlist_videos()

            # Procesar nuevas descargas
            for video_data in videos:
                self._process_video(video_data)

            # Sincronización bidireccional: detectar eliminaciones
            if self.enable_sync_deletions:
                self._detect_and_remove_deleted_videos(videos)

            # Auto-limpieza de carpeta .trash
            if self.use_trash_folder and self.trash_retention_days > 0:
                self._cleanup_trash_folder()

        except Exception as e:
            logger.error(f"Error verificando playlist: {e}")

    def _normalize_video_entry(self, video_data: Dict):
        """
        Normalizar título/ID y determinar si la entrada es válida.
        """
        raw_title = video_data.get("title")
        title = str(raw_title) if raw_title is not None else ""
        video_id = video_data.get("id")
        is_invalid = not video_id or not title.strip() or "[Deleted" in title
        return video_id, raw_title, title, is_invalid

    def _process_video(self, video_data: Dict):
        """Procesar un video individual"""
        video_id, raw_title, title, is_invalid = self._normalize_video_entry(video_data)

        if is_invalid:
            logger.warning(
                f"Saltando entrada inválida: title={raw_title}, video_id={video_id}"
            )
            return

        display_title = title or "Unknown Title"

        # Verificar si ya se descargó
        if video_id in self.downloaded_videos:
            return

        # Verificar si ya falló recientemente (no reintentar hasta pasadas X horas)
        if video_id in self.failed_downloads:
            failed_info = self.failed_downloads[video_id]
            failed_at_str = failed_info.get("failed_at", "")
            try:
                failed_at = datetime.fromisoformat(failed_at_str)
                hours_since_fail = (datetime.now() - failed_at).total_seconds() / 3600
                if hours_since_fail < self._failed_retry_hours:
                    # Silenciosamente omitir, ya intentamos recientemente
                    return
                else:
                    # Ha pasado suficiente tiempo, reintentar
                    logger.info(
                        f"🔄 Reintentando descarga fallida: {display_title} "
                        f"(último intento hace {hours_since_fail:.1f}h)"
                    )
            except (ValueError, TypeError):
                pass  # Si no podemos parsear la fecha, reintentar

        logger.info(f"Nueva canción detectada: {display_title}")

        try:
            result = self.downloader.download_and_convert(video_data)
            if result and result.get("success"):
                # Guardar información de descarga
                self.downloaded_videos.add(video_id)
                self.downloads[video_id] = {
                    "filename": result.get("filename", ""),
                    "downloaded_at": datetime.now().isoformat(),
                    "title": result.get("title", display_title),
                    "artist": result.get("artist", "Unknown Artist"),
                }
                # Limpiar de fallidos si estaba ahí
                self.failed_downloads.pop(video_id, None)
                self._save_state()
                logger.info(f"✅ Descarga completada: {display_title}")
            else:
                # Registrar como descarga fallida
                retry_count = (
                    self.failed_downloads.get(video_id, {}).get("retry_count", 0) + 1
                )
                self.failed_downloads[video_id] = {
                    "title": display_title,
                    "reason": "download_failed",
                    "failed_at": datetime.now().isoformat(),
                    "retry_count": retry_count,
                }
                self._save_state()
                logger.warning(
                    f"⚠️ Descarga fallida: {display_title} "
                    f"(intento #{retry_count}, próximo reintento en {self._failed_retry_hours}h)"
                )
        except Exception as e:
            # Registrar como descarga fallida por excepción
            retry_count = (
                self.failed_downloads.get(video_id, {}).get("retry_count", 0) + 1
            )
            self.failed_downloads[video_id] = {
                "title": display_title,
                "reason": str(e),
                "failed_at": datetime.now().isoformat(),
                "retry_count": retry_count,
            }
            self._save_state()
            logger.error(
                f"❌ Error descargando {display_title}: {e} "
                f"(intento #{retry_count}, próximo reintento en {self._failed_retry_hours}h)"
            )

    def _detect_and_remove_deleted_videos(self, current_videos: list) -> None:
        """
        Detectar videos eliminados de la playlist y remover archivos.

        Args:
            current_videos: Lista actual de videos en la playlist
        """
        try:
            # Obtener IDs válidos de videos actuales en la playlist
            current_video_ids = set()
            for video_data in current_videos:
                video_id, raw_title, title, is_invalid = self._normalize_video_entry(
                    video_data
                )
                if is_invalid:
                    # Si la entrada es inválida la tratamos como ausente para sync
                    logger.debug(
                        f"Ignorando entrada inválida en sync: "
                        f"title={raw_title}, video_id={video_id}"
                    )
                    continue
                current_video_ids.add(video_id)

            # === SAFETY CHECK: Protección contra respuestas incompletas ===
            # Si YouTube devuelve muy pocos videos, probablemente es un error
            total_downloaded = len(self.downloaded_videos)
            total_current = len(current_video_ids)

            # Si la playlist actual tiene menos del 80% de los videos descargados,
            # probablemente YouTube devolvió una respuesta incompleta
            if total_downloaded > 0 and total_current < total_downloaded * 0.8:
                logger.warning(
                    f"⚠️ Sync ignorado: YouTube devolvió {total_current} videos "
                    f"pero tenemos {total_downloaded} descargados. "
                    f"Posible respuesta incompleta de YouTube."
                )
                return

            # Encontrar videos que fueron descargados pero ya no están en la playlist
            deleted_video_ids = self.downloaded_videos - current_video_ids

            if not deleted_video_ids:
                return

            # === SAFETY CHECK: No eliminar más del 10% de videos de golpe ===
            deletion_threshold = max(5, int(total_downloaded * 0.1))
            if len(deleted_video_ids) > deletion_threshold:
                logger.warning(
                    f"⚠️ Sync ignorado: {len(deleted_video_ids)} videos marcados "
                    f"como eliminados (umbral: {deletion_threshold}). "
                    f"Esto parece un error de YouTube, no una eliminación real."
                )
                return

            logger.info(
                f"🗑️ Detectadas {len(deleted_video_ids)} canciones "
                f"eliminadas de la playlist"
            )

            # Remover archivos de videos eliminados
            for video_id in deleted_video_ids:
                download_info = self.downloads.get(video_id)
                if download_info:
                    filename = download_info.get("filename")
                    title = download_info.get("title", "Unknown")
                    if filename:
                        self._remove_file(filename, title)

                # Actualizar estado
                self.downloaded_videos.discard(video_id)
                self.downloads.pop(video_id, None)

            # Guardar estado actualizado
            self._save_state()

        except Exception as e:
            logger.error(f"Error detectando videos eliminados: {e}")

    def _remove_file(self, filename: str, title: str) -> None:
        """
        Remover archivo FLAC (mover a .trash o eliminar permanentemente).

        Args:
            filename: Nombre del archivo a remover
            title: Título de la canción (para logs)
        """
        try:
            file_path = self.download_path / filename

            if not file_path.exists():
                logger.warning(f"Archivo no encontrado para eliminar: {filename}")
                return

            if self.use_trash_folder:
                # Crear carpeta .trash si no existe
                self._trash_folder.mkdir(parents=True, exist_ok=True)

                # Generar nombre con timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                name_parts = filename.rsplit(".", 1)
                if len(name_parts) == 2:
                    trash_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    trash_filename = f"{filename}_{timestamp}"

                trash_path = self._trash_folder / trash_filename

                # Mover a .trash
                shutil.move(str(file_path), str(trash_path))
                logger.info(f"🗑️ Movido a .trash: {title} -> {trash_filename}")
            else:
                # Eliminar permanentemente
                file_path.unlink()
                logger.info(f"❌ Eliminado permanentemente: {title}")

        except Exception as e:
            logger.error(f"Error eliminando archivo {filename}: {e}")

    def _cleanup_trash_folder(self) -> None:
        """
        Limpiar archivos antiguos de la carpeta .trash según retención.
        """
        try:
            if not self._trash_folder.exists():
                return

            now = datetime.now()
            retention_delta = timedelta(days=self.trash_retention_days)
            deleted_count = 0
            total_files = 0

            # Iterar sobre archivos en .trash
            for file_path in self._trash_folder.glob("*.flac"):
                total_files += 1
                try:
                    file_date = None

                    # Intentar extraer timestamp del nombre
                    # Formato: Artist - Title_YYYY-MM-DD_HH-MM-SS.flac
                    filename = file_path.stem
                    parts = filename.rsplit("_", 2)

                    if len(parts) >= 3:
                        # Intentar parsear fecha y hora
                        date_str = parts[-2]
                        time_str = parts[-1]
                        timestamp_str = f"{date_str} {time_str.replace('-', ':')}"

                        try:
                            file_date = datetime.strptime(
                                timestamp_str, "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            logger.debug(
                                f"No se pudo parsear timestamp de {file_path.name}, "
                                f"usando mtime como fallback"
                            )

                    # Fallback: usar fecha de modificación del archivo
                    if file_date is None:
                        file_date = datetime.fromtimestamp(file_path.stat().st_mtime)

                    file_age_days = (now - file_date).days

                    # Verificar si excede retención
                    if now - file_date > retention_delta:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(
                            f"🗑️ Auto-limpieza: eliminado {file_path.name} "
                            f"(edad: {file_age_days} días)"
                        )
                    else:
                        logger.debug(
                            f"Manteniendo {file_path.name} "
                            f"(edad: {file_age_days} días, retención: {self.trash_retention_days} días)"
                        )

                except Exception as e:
                    logger.warning(f"Error procesando archivo {file_path.name}: {e}")

            if deleted_count > 0:
                logger.info(
                    f"🗑️ Auto-limpieza: eliminados {deleted_count} archivos "
                    f"de .trash/ (>{self.trash_retention_days} días)"
                )

        except Exception as e:
            logger.error(f"Error en auto-limpieza de .trash: {e}")

    def download_latest_song(self):
        """Descargar únicamente la última canción de la playlist"""
        try:
            logger.info("Obteniendo la última canción de la playlist...")

            # Obtener videos de la playlist
            videos = self.monitor.get_playlist_videos()

            if not videos:
                logger.warning("No se encontraron canciones en la playlist")
                return None

            # Seleccionar la última por fecha si está disponible;
            # si no, usar la primera posición
            latest_video = videos[0]
            try:
                candidates = [
                    v for v in videos if isinstance(v, dict) and v.get("upload_date")
                ]
                if candidates:
                    latest_video = max(
                        candidates, key=lambda v: str(v.get("upload_date"))
                    )
            except Exception:
                pass
            video_id, raw_title, title, is_invalid = self._normalize_video_entry(
                latest_video
            )

            if is_invalid:
                logger.warning(
                    f"Saltando entrada inválida en última canción: "
                    f"title={raw_title}, video_id={video_id}"
                )
                return None

            display_title = title or "Unknown Title"

            if not video_id:
                logger.warning(f"No se encontró ID para: {display_title}")
                return None

            logger.info(f"Descargando última canción: {display_title}")

            try:
                result = self.downloader.download_and_convert(latest_video)
                if result and result.get("success"):
                    if video_id:
                        self.downloaded_videos.add(video_id)
                        self.downloads[video_id] = {
                            "filename": result.get("filename", ""),
                            "downloaded_at": datetime.now().isoformat(),
                            "title": result.get("title", display_title),
                            "artist": result.get("artist", "Unknown Artist"),
                        }
                        self._save_state()
                    logger.info(f"✅ Descarga completada: {display_title}")
                    return latest_video
                else:
                    logger.warning(f"Descarga fallida/omitida: {display_title}")
                    return None
            except Exception as e:
                logger.error(f"Error descargando {display_title}: {e}")
                return None

        except Exception as e:
            logger.error(f"Error obteniendo la última canción: {e}")
            return None

    def get_stats(self) -> Dict:
        """Obtener estadísticas del watcher"""
        return {
            "playlist_url": self.playlist_url,
            "download_path": self._download_path_raw,
            "interval_ms": self.interval_ms,
            "downloaded_count": len(self.downloaded_videos),
            "downloaded_videos": list(self.downloaded_videos),
        }

    # Estado persistente de descargas
    def _load_state(self) -> None:
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    # Cargar video_ids (backward compatibility)
                    if isinstance(data.get("video_ids"), list):
                        self.downloaded_videos = set(str(v) for v in data["video_ids"])
                    # Cargar downloads dict (nueva estructura)
                    if isinstance(data.get("downloads"), dict):
                        self.downloads = data["downloads"]
                        # Garantizar que downloaded_videos incluya claves de downloads
                        self.downloaded_videos.update(self.downloads.keys())
                    # Cargar failed_downloads dict
                    if isinstance(data.get("failed_downloads"), dict):
                        self.failed_downloads = data["failed_downloads"]
                        logger.info(
                            f"📋 Cargados {len(self.failed_downloads)} videos con descargas fallidas previas"
                        )
        except Exception as e:
            logger.warning(f"No se pudo cargar estado previo: {e}")

    def _save_state(self) -> None:
        try:
            payload = {
                "video_ids": sorted(self.downloaded_videos),
                "downloads": self.downloads,
                "failed_downloads": self.failed_downloads,
            }
            self._state_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"No se pudo guardar estado: {e}")
