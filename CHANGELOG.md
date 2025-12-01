Changelog

Este proyecto sigue el formato Keep a Changelog y Semantic Versioning (SemVer).

Guía rápida de SemVer (X.Y.Z)
- X (MAJOR): cambios incompatibles (rompes CLI, variables obligatorias, formato de salida, rutas…)
- Y (MINOR): nuevas funcionalidades compatibles (nuevas flags/opciones, mejoras sin romper contratos)
- Z (PATCH): correcciones y mejoras internas (bugs, rendimiento, logs)

Cómo publicar una versión
1) En “Unreleased”, lista los cambios hechos. Cuando cortes versión, muévelos a una nueva sección `X.Y.Z - YYYY-MM-DD`.
2) Crea el tag Git `vX.Y.Z` y haz push. La versión del paquete se deriva del tag vía `setuptools_scm`.
3) El workflow de GitHub Actions crea la Release, adjunta artefactos y (opcional) publica la imagen Docker.

Unreleased
- Added: Sincronización bidireccional - detecta y elimina archivos cuando se eliminan canciones de la playlist
- Added: Modo papelera de reciclaje para recuperación de archivos eliminados (.trash/)
- Added: Auto-limpieza de carpeta .trash/ con retención configurable
- Added: Variables de entorno ENABLE_SYNC_DELETIONS, USE_TRASH_FOLDER y TRASH_RETENTION_DAYS
- Added: Argumentos CLI --enable-sync-deletions, --disable-trash y --trash-retention-days
- Changed: downloader.download_and_convert() ahora retorna dict con metadata en lugar de bool
- Changed: Estado persistente (.downloaded.json) ahora incluye mapeo de video_id a filename y metadata
- Fixed:


3.0.7 - 2025-09-02
- Fixed: Cumplimiento flake8 E501 (línea larga) en `downloader.py` al envolver la URL de fallback de thumbnail; CI verde de nuevo.

3.0.6 - 2025-09-02
- Fixed: Portadas embebidas de forma robusta aunque `yt-dlp` no entregue `thumbnail` plano; ahora se resuelve desde `thumbnails` y, si falta, se usa fallback `i.ytimg.com/…/hqdefault.jpg`.
- Fixed: Soporte de portadas servidas como WEBP convirtiéndolas a JPEG antes de incrustar (Mutagen/FLAC).
- Added: Trazas DEBUG detalladas para diagnóstico de portadas (URL resuelta, respuesta HTTP, dimensiones/bytes procesados y `pictures` tras guardar).
- Changed: Descarga de portada con User‑Agent para evitar bloqueos de CDN.

3.0.5 - 2025-09-02
- Fixed: `PlaylistMonitor.get_playlist_videos()` soporta stdout con JSON de video único (compat con tests y casos edge).
- Fixed: CI fallos por parser — tolerancia de formatos de salida (`-J --flat-playlist`) y fallback por líneas.
- Docs: aclaraciones de pruebas locales (Docker/Compose) y uso de intervalos en ms.

3.0.4 - 2025-09-02
- Added: Publicación de imagen en GitHub Container Registry (GHCR) en el workflow de Release.
- Changed: CI con matriz de Python 3.11 y 3.12 y checkout con `fetch-depth: 0`.
- Changed: Dockerfile simplificado (sin runner antiguo) y ejecución como usuario mapeado por docker-compose.
- Changed: Makefile/CI instalan extras con comillas para evitar problemas de zsh (`'.[dev]'`).
- Fixed: `pyproject.toml` `tag_regex` corregido (escape de `\` en TOML) para `setuptools_scm`.
- Fixed: Workflow de Release — corrección de condiciones con secrets (mapeo a env) y validación tag/paquete.
- Fixed: Lint y estilo (líneas largas, imports no usados) y `get_stats()` devuelve la ruta cruda esperada por tests.
- Added: Variable `YT_DLP_VERSION` en build de compose y `COOKIES_FILE` expuesta en env.
- Changed: Listado de playlist con `yt-dlp -J --flat-playlist` y `check=False` para tolerar elementos problemáticos.
- Changed: Forzado `--cache-dir /tmp/yt-dlp-cache` y `--ignore-errors` en yt-dlp (listado y descarga).
- Fixed: `.dockerignore` permite `requirements.txt` para el build.
- Fixed: El watcher solo marca como descargado si se genera el FLAC (downloader retorna bool y se comprueba).

3.0.3 - 2025-09-02
- Changed: release.yml Fue modificado para configuraciones de github actions
- Fixed: Control de .env en referencia a docker hub

3.0.2 - 2025-09-02
- Added: Documentación de versionado y releases en README y este CHANGELOG.
- Added: Workflow de GitHub Actions para releases (paquete + GitHub Release, Docker opcional).
- Added: Pre-commit, EditorConfig, Makefile y configuraciones de flake8/black para un flujo profesional.
- Changed: Versionado dinámico desde tags (`setuptools_scm`) y validación tag/paquete en el workflow.
- Changed: Docker Compose con healthcheck y mapeo de usuario configurable (`UID`/`GID`).

3.0.1 - 2025-09-02
- Added: `LOG_LEVEL`, soporte de `COOKIES_FILE`, y guía de despliegue en Portainer.
- Changed: Reorganización del proyecto (runner vía `python -m youtube_watcher`, scripts en `scripts/`, retirada de `setup.py`).
- Changed: Docker ejecuta como usuario no-root y `yt-dlp` pinneado por ARG.
- Changed: Parsing de playlist más robusto y selección de “última canción” por `upload_date` cuando esté.
- Fixed: Logs de error detallados de `yt-dlp/ffmpeg`, limpieza de portadas duplicadas, truncado seguro de nombres largos.
- Fixed: Estado persistente de descargas (`.downloaded.json`) y backoff exponencial en el watcher.

3.0.0 - 2025-09-02
- Added: Migración mayor y estructura base del watcher en Python (CLI, monitor, downloader y metadatos) con soporte de Docker/Compose.
