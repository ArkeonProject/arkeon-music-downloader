"""
Interfaz de línea de comandos para YouTube Playlist Watcher
"""

import os
import sys
import logging
import argparse
from pathlib import Path

from .watcher import YouTubeWatcher


def setup_logging():
    """Configurar logging para la aplicación"""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_environment_config():
    """
    Obtener configuración desde variables de entorno.

    Returns:
        Tupla con configuración
    """
    playlist_url = os.getenv("PLAYLIST_URL")
    download_path = os.getenv("DOWNLOAD_PATH", "./downloads")
    interval_ms = int(os.getenv("OBSERVER_INTERVAL_MS", "60000"))
    cookies_path = os.getenv("COOKIES_FILE")

    # Configuración de sincronización bidireccional
    enable_sync_deletions = os.getenv("ENABLE_SYNC_DELETIONS", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    use_trash_folder = os.getenv("USE_TRASH_FOLDER", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    trash_retention_days = int(os.getenv("TRASH_RETENTION_DAYS", "7"))

    return (
        playlist_url,
        download_path,
        interval_ms,
        cookies_path,
        enable_sync_deletions,
        use_trash_folder,
        trash_retention_days,
    )


def validate_config(playlist_url: str, download_path: str) -> bool:
    """
    Validar configuración.

    Args:
        playlist_url: URL de la playlist
        download_path: Directorio de descargas

    Returns:
        True si la configuración es válida
    """
    if not playlist_url:
        logging.error("PLAYLIST_URL no está configurado")
        return False

    valid_prefixes = (
        "https://www.youtube.com/",
        "https://music.youtube.com/",
        "https://youtu.be/",
        "https://www.youtube-nocookie.com/",
    )
    if not playlist_url.startswith(valid_prefixes):
        logging.error("PLAYLIST_URL debe ser una URL válida de YouTube o YouTube Music")
        return False

    # Crear directorio de descargas si no existe
    path = Path(download_path)
    path.mkdir(parents=True, exist_ok=True)

    # Verificar permisos de escritura
    try:
        test_file = path / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
    except Exception:
        logging.error(f"No hay permisos de escritura en: {path}")
        return False

    return True


def main():
    """Función principal de la CLI"""
    parser = argparse.ArgumentParser(
        description="YouTube Playlist Watcher - Descarga automática a FLAC"
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Descargar únicamente la última canción de la playlist",
    )
    parser.add_argument(
        "--playlist-url", help="URL de la playlist (sobrescribe PLAYLIST_URL)"
    )
    parser.add_argument(
        "--download-path", help="Directorio de descargas (sobrescribe DOWNLOAD_PATH)"
    )
    parser.add_argument(
        "--cookies",
        help="Ruta a archivo de cookies de YouTube para playlists privadas/edad/región",
    )
    parser.add_argument(
        "--enable-sync-deletions",
        action="store_true",
        help="Habilitar sincronización bidireccional (eliminar archivos cuando se eliminan de la playlist)",
    )
    parser.add_argument(
        "--disable-trash",
        action="store_true",
        help="Eliminar archivos permanentemente en lugar de moverlos a .trash",
    )
    parser.add_argument(
        "--trash-retention-days",
        type=int,
        help="Días de retención en carpeta .trash antes de eliminar permanentemente (default: 7)",
    )

    args = parser.parse_args()

    print("YouTube Playlist Watcher - Descarga automática a FLAC")
    print("Asegúrate de tener yt-dlp, ffmpeg, mutagen y Pillow instalados")
    print()

    # Configurar logging
    setup_logging()

    # Obtener configuración
    (
        playlist_url,
        download_path,
        interval_ms,
        cookies_path,
        enable_sync_deletions,
        use_trash_folder,
        trash_retention_days,
    ) = get_environment_config()

    # Sobrescribir con argumentos de línea de comandos si se proporcionan
    if args.playlist_url:
        playlist_url = args.playlist_url
    if args.download_path:
        download_path = args.download_path
    if args.cookies:
        cookies_path = args.cookies
    if args.enable_sync_deletions:
        enable_sync_deletions = True
    if args.disable_trash:
        use_trash_folder = False
    if args.trash_retention_days is not None:
        trash_retention_days = args.trash_retention_days

    # Validar configuración
    if not validate_config(playlist_url, download_path):
        sys.exit(1)

    try:
        # Crear watcher
        watcher = YouTubeWatcher(
            playlist_url,
            download_path,
            interval_ms,
            cookies_path=cookies_path,
            enable_sync_deletions=enable_sync_deletions,
            use_trash_folder=use_trash_folder,
            trash_retention_days=trash_retention_days,
        )

        if args.latest_only:
            # Descargar solo la última canción
            print("🎵 Modo: Descarga única de la última canción")
            result = watcher.download_latest_song()
            if result:
                print(f"✅ Descarga completada: {result.get('title', 'Unknown')}")
            else:
                print("❌ Error en la descarga")
                sys.exit(1)
        else:
            # Modo normal de monitoreo continuo
            print("🔄 Modo: Monitoreo continuo de la playlist")
            watcher.start()

    except KeyboardInterrupt:
        logging.info("Aplicación detenida por el usuario")
    except Exception as e:
        logging.error(f"Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
