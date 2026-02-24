#!/usr/bin/env python3
"""
Script manual para descargar la última canción de una playlist.
Uso:
  python scripts/test_latest_download.py [PLAYLIST_URL] [DOWNLOAD_PATH]
"""

import os
import sys
from pathlib import Path

# Asegurar imports del paquete
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from youtube_watcher.watcher import YouTubeWatcher  # noqa: E402


def main():
    playlist_url = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.getenv(
            "PLAYLIST_URL",
            "https://music.youtube.com/playlist?list=PLFgquLnL59anUbTCum31nHshzm-3pAMP-",
        )
    )
    download_path = (
        sys.argv[2] if len(sys.argv) > 2 else os.getenv("DOWNLOAD_PATH", "./downloads")
    )

    print("🎵 Probando descarga de última canción...")
    print(f"Playlist: {playlist_url}")
    print(f"Directorio: {download_path}")
    print()

    try:
        watcher = YouTubeWatcher(playlist_url, download_path)
        result = watcher.download_latest_song()

        if result:
            print(f"✅ Descarga completada: {result.get('title', 'Unknown')}")
        else:
            print("❌ Error en la descarga")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
