"""
Downloader de YouTube - Descarga y convierte videos a FLAC
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional

import yt_dlp

from .metadata_handler import MetadataHandler

logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """
    Clase para descargar y convertir videos de YouTube a FLAC
    """

    def __init__(self, download_path: str, cookies_path: str | None = None):
        """
        Inicializar downloader.

        Args:
            download_path: Directorio donde guardar archivos
        """
        self.download_path = Path(download_path)
        self.metadata_handler = MetadataHandler()
        self.cookies_path = cookies_path

        # Crear directorio si no existe
        self.download_path.mkdir(parents=True, exist_ok=True)
        
        # Plantilla de salida de yt-dlp
        # Usamos %(id)s para que yt-dlp maneje el nombre dinámicamente según el video,
        # lo que nos permite usar una sola instancia persistente de YoutubeDL
        out_tmpl = str(self.download_path / "temp_%(id)s.%(ext)s")
        
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_tmpl,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "cachedir": str(Path(tempfile.gettempdir()) / "yt-dlp-cache"),
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "nocheckcertificate": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "opus",
                    "preferredquality": "0",
                }
            ],
        }

        if self.cookies_path:
            ydl_opts["cookiefile"] = self.cookies_path
            
        self._ydl = yt_dlp.YoutubeDL(ydl_opts)

    def download_and_convert(self, video_data: Dict) -> Optional[Dict]:
        """
        Descargar y convertir un video a FLAC con metadatos.

        Args:
            video_data: Diccionario con información del video

        Returns:
            Dict con información de descarga o None si falla
        """
        title = video_data.get("title", "Unknown Title")
        artist = (
            video_data.get("artist")
            or video_data.get("channel")
            or video_data.get("uploader", "Unknown Artist")
        )
        album = video_data.get("album", f"YouTube - {artist}")
        upload_date = video_data.get("upload_date")
        year = upload_date[:4] if upload_date and len(upload_date) >= 4 else None
        # Resolver URL de portada
        thumbnail_url = video_data.get("thumbnail")
        if not thumbnail_url:
            thumbs = video_data.get("thumbnails")
            if isinstance(thumbs, list) and thumbs:
                try:
                    best = max(
                        (t for t in thumbs if isinstance(t, dict) and t.get("url")),
                        key=lambda t: t.get("width", 0) or 0,
                    )
                    thumbnail_url = best.get("url")
                except Exception:
                    # Último recurso: tomar el último elemento
                    for t in reversed(thumbs):
                        if isinstance(t, dict) and t.get("url"):
                            thumbnail_url = t.get("url")
                            break
            if not thumbnail_url and video_data.get("id"):
                # Fallback estable de YouTube
                thumbnail_url = (
                    f"https://i.ytimg.com/vi/{video_data['id']}/hqdefault.jpg"
                )

        logger.debug(
            "Thumbnail URL resolved for '%s': %s", title, thumbnail_url or "<none>"
        )

        # Sanitizar nombres
        safe_title = self._sanitize_filename(title)
        safe_artist = self._sanitize_filename(artist)

        # Crear nombre de archivo
        filename = f"{safe_artist} - {safe_title}.flac"
        filename = self._trim_filename(filename, max_len=200)
        output_path = self.download_path / filename

        # Evitar duplicados: si el archivo ya existe, no volver a descargar
        if output_path.exists():
            logger.info(f"Archivo ya existe, omitiendo descarga: {filename}")
            return {
                "success": True,
                "filename": filename,
                "title": title,
                "artist": artist,
            }

        # Paso 1: Descargar audio en Opus
        opus_result = self._download_opus(video_data, title)
        if not opus_result:
            return None
        temp_opus, full_info = opus_result
        
        if full_info:
            new_upload_date = full_info.get("upload_date")
            if new_upload_date and len(new_upload_date) >= 4:
                year = new_upload_date[:4]

        # Paso 2: Convertir a FLAC
        if not self._convert_to_flac(temp_opus, output_path, title):
            return None

        # Limpiar archivo temporal
        temp_opus.unlink(missing_ok=True)

        # Paso 3: Añadir metadatos y portada
        self.metadata_handler.add_metadata_and_cover(
            output_path, title, artist, album, year, thumbnail_url
        )

        logger.info(f"FLAC listo: {filename}")
        return {
            "success": True,
            "filename": filename,
            "title": title,
            "artist": artist,
            "published_at": year,
        }

    def _download_opus(self, video_data: Dict, title: str) -> Optional[tuple[Path, Dict]]:
        """
        Descargar audio en formato Opus.

        Args:
            video_data: Información del video
            title: Título del video

        Returns:
            Path al archivo Opus temporal o None si falla
        """
        base_filename = f"temp_{video_data['id']}"
        # Template de salida esperado por yt-dlp
        try:
            logger.info(f"Descargando '{title}' en Opus...")

            # Descargar usando la URL del video y capturar información completa
            url = f"https://www.youtube.com/watch?v={video_data['id']}"
            info = self._ydl.extract_info(url, download=True)

            # Buscar el archivo descargado (puede tener extensión .opus o .webm)
            for ext in ["opus", "webm"]:
                downloaded_file = self.download_path / f"{base_filename}.{ext}"
                if downloaded_file.exists():
                    return downloaded_file, info

            logger.error(f"No se encontró archivo descargado para '{title}'")
            return None

        except Exception as e:
            logger.error(f"Error descargando '{title}': {e}")
            return None

    def _convert_to_flac(self, opus_path: Path, flac_path: Path, title: str) -> bool:
        """
        Convertir archivo Opus a FLAC.

        Args:
            opus_path: Path al archivo Opus
            flac_path: Path de salida para FLAC
            title: Título del video

        Returns:
            True si la conversión fue exitosa
        """
        ffmpeg_cmd = [
            "ffmpeg",
            "-i",
            str(opus_path),
            "-vn",
            "-acodec",
            "flac",
            "-compression_level",
            "8",
            "-sample_fmt",
            "s16",
            "-y",
            str(flac_path),
        ]

        try:
            logger.info(f"Convirtiendo a FLAC: {flac_path.name}")
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error convirtiendo a FLAC para '{title}': {e}")
            if e.stderr:
                logger.error(f"ffmpeg stderr: {e.stderr}")
            if e.stdout:
                logger.error(f"ffmpeg stdout: {e.stdout}")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitizar nombre de archivo.

        Args:
            filename: Nombre original

        Returns:
            Nombre sanitizado
        """
        # Reemplazar caracteres problemáticos
        filename = filename.replace("/", "_").replace("\\", "_")

        # Mantener solo caracteres seguros
        safe_chars = []
        for char in filename:
            if char.isalnum() or char in (" ", ".", "-", "_"):
                safe_chars.append(char)

        filename = "".join(safe_chars).strip()

        # Eliminar punto final
        if filename.endswith("."):
            filename = filename[:-1]
        # Colapsar espacios múltiples
        filename = " ".join(filename.split())

        return filename

    def _trim_filename(self, filename: str, max_len: int = 200) -> str:
        """
        Truncar el nombre del archivo manteniendo la extensión si excede max_len.
        """
        try:
            if len(filename) <= max_len:
                return filename
            stem, dot, ext = filename.rpartition(".")
            if not dot:  # no extension
                return filename[:max_len]
            keep = max_len - len(ext) - 1  # account for dot
            stem = stem[:keep]
            return f"{stem}.{ext}"
        except Exception:
            return filename[:max_len]

    def __del__(self):
        """Asegurar el cierre de la instancia de YoutubeDL."""
        if hasattr(self, '_ydl') and self._ydl:
            try:
                self._ydl.close()
            except Exception:
                pass
