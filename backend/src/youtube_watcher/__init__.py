"""
YouTube Playlist Watcher Package

Un watcher automático para descargar nuevas canciones de playlists de YouTube
en formato FLAC con metadatos y portada.
"""

try:
    from importlib.metadata import version, PackageNotFoundError

    __version__ = version("youtube-playlist-watcher")
except PackageNotFoundError:
    # En entorno de desarrollo sin instalar el paquete
    __version__ = "0+unknown"
__author__ = "David Lopez"
__description__ = "YouTube Playlist Watcher - Descarga automática a FLAC"
