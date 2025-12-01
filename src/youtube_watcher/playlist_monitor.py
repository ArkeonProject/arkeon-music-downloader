"""
Monitor de playlist de YouTube - Obtiene información de videos
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, List

import yt_dlp

logger = logging.getLogger(__name__)


class PlaylistMonitor:
    """
    Clase para monitorear y obtener información de playlists de YouTube
    """

    def __init__(self, playlist_url: str, cookies_path: str | None = None):
        """
        Inicializar monitor de playlist.

        Args:
            playlist_url: URL de la playlist de YouTube
        """
        self.playlist_url = playlist_url
        self.cookies_path = cookies_path

    def get_playlist_videos(self) -> List[Dict]:
        """
        Obtener lista de videos de la playlist.

        Returns:
            Lista de diccionarios con información de cada video
        """
        try:
            ydl_opts = {
                "extract_flat": True,
                "ignoreerrors": True,
                "quiet": True,
                "no_warnings": True,
                "cachedir": str(Path(tempfile.gettempdir()) / "yt-dlp-cache"),
            }
            if self.cookies_path:
                ydl_opts["cookiefile"] = self.cookies_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.playlist_url, download=False)

                if not info:
                    return []

                if "entries" in info:
                    # Filtrar entradas nulas que a veces retorna yt-dlp
                    return [entry for entry in info["entries"] if entry]

                # Fallback: si es un solo video
                return [info]

        except Exception as e:
            logger.error(f"Error obteniendo videos de playlist: {e}")
            return []

    def get_playlist_info(self) -> Dict:
        """
        Obtener información general de la playlist.

        Returns:
            Diccionario con información de la playlist
        """
        try:
            ydl_opts = {
                "dump_single_json": True,
                "extract_flat": True,
                "ignoreerrors": True,
                "quiet": True,
                "no_warnings": True,
                "cachedir": str(Path(tempfile.gettempdir()) / "yt-dlp-cache"),
            }
            if self.cookies_path:
                ydl_opts["cookiefile"] = self.cookies_path

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.playlist_url, download=False)

                if not info:
                    return {}

                entries = info.get("entries", [])

                return {
                    "title": info.get("title", "Unknown Playlist"),
                    "uploader": info.get("uploader", "Unknown"),
                    "video_count": len(entries) if isinstance(entries, list) else 0,
                    "description": info.get("description", ""),
                    "upload_date": info.get("upload_date", ""),
                }

        except Exception as e:
            logger.error(f"Error obteniendo información de playlist: {e}")
            return {}
