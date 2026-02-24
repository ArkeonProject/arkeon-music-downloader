"""
Manejador de metadatos - Añade tags y portada a archivos FLAC
"""

import logging
import requests
from pathlib import Path
from typing import Optional
from PIL import Image
from io import BytesIO
from mutagen.flac import FLAC, Picture

logger = logging.getLogger(__name__)


class MetadataHandler:
    """
    Clase para manejar metadatos y portadas de archivos FLAC
    """

    def __init__(self):
        """Inicializar manejador de metadatos"""
        pass

    def add_metadata_and_cover(
        self,
        flac_path: Path,
        title: str,
        artist: str,
        album: str,
        year: Optional[str],
        thumbnail_url: Optional[str],
    ):
        """
        Añadir metadatos y portada al archivo FLAC.

        Args:
            flac_path: Path al archivo FLAC
            title: Título de la canción
            artist: Artista
            album: Álbum
            year: Año de lanzamiento
            thumbnail_url: URL de la portada
        """
        try:
            logger.debug("Abriendo FLAC para metadatos: %s", flac_path)
            audio = FLAC(flac_path)

            # Metadatos básicos
            audio["title"] = title
            audio["artist"] = artist
            audio["album"] = album
            if year:
                audio["date"] = year
                audio["originalyear"] = year

            # Portada
            if thumbnail_url:
                # Evitar duplicados de portadas
                try:
                    audio.clear_pictures()
                except Exception:
                    pass
                self._add_cover(audio, thumbnail_url, title)
            else:
                logger.debug("Sin thumbnail URL para '%s'; se omite portada", title)

            # Guardar cambios
            audio.save()
            try:
                pics = getattr(audio, "pictures", [])
                logger.debug("FLAC '%s' guardar ok; pictures=%s", title, len(pics))
            except Exception:
                logger.debug("FLAC '%s' guardado; no se pudo leer pictures", title)
            logger.info(f"Metadatos guardados para '{title}'")

        except Exception as e:
            logger.error(f"Error añadiendo metadatos: {e}")

    def _add_cover(self, audio: FLAC, thumbnail_url: str, title: str):
        """
        Añadir portada al archivo FLAC.

        Args:
            audio: Objeto FLAC
            thumbnail_url: URL de la portada
            title: Título de la canción
        """
        try:
            logger.info("Descargando portada para '%s'...", title)

            # Descargar imagen (con User-Agent para evitar bloqueos de CDN)
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            }
            response = requests.get(thumbnail_url, timeout=10, headers=headers)
            response.raise_for_status()
            ctype = response.headers.get("Content-Type")
            clen = response.headers.get("Content-Length")
            logger.debug(
                "Thumbnail HTTP ok para '%s': status=%s, type=%s, length=%s",
                title,
                response.status_code,
                ctype,
                clen,
            )

            # Procesar imagen
            img_data = self._process_image(response.content)
            if not img_data:
                return

            # Crear objeto Picture
            picture = Picture()
            picture.data = img_data
            picture.type = 3  # Front cover
            picture.mime = "image/jpeg"

            # Añadir portada
            audio.add_picture(picture)
            logger.info("Portada añadida para '%s'", title)

        except requests.exceptions.RequestException as e:
            logger.warning("Error al descargar la portada para '%s': %s", title, e)
        except Exception as e:
            logger.warning("Error al procesar la portada para '%s': %s", title, e)

    def _process_image(self, image_content: bytes) -> Optional[bytes]:
        """
        Procesar y redimensionar imagen.

        Args:
            image_content: Contenido de la imagen

        Returns:
            Bytes de la imagen procesada o None si falla
        """
        try:
            # Abrir imagen
            img = Image.open(BytesIO(image_content))
            orig_w, orig_h = img.size

            # Redimensionar manteniendo proporción
            img.thumbnail((1000, 1000), Image.LANCZOS)
            new_w, new_h = img.size

            # Convertir a bytes JPEG
            img_bytes = BytesIO()
            img.save(img_bytes, format="JPEG", quality=95)
            logger.debug(
                "Imagen portada procesada: %sx%s -> %sx%s, bytes=%s",
                orig_w,
                orig_h,
                new_w,
                new_h,
                img_bytes.tell(),
            )

            return img_bytes.getvalue()

        except Exception as e:
            logger.warning(f"Error procesando imagen: {e}")
            return None
