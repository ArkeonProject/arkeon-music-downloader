# Documentación Arquitectónica

El proyecto `arkeon-music-downloader` evolucionó de un script CLI monolítico a una aplicación web completa con separación de responsabilidades (Backend RESTful + Frontend React).

## Backend (FastAPI + SQLAlchemy)

Ubicado en la carpeta `/backend/`.

### Componentes Principales

- **`api/main.py` y `api/routes.py`**: Definen los endpoints REST. Sirven datos a la UI sobre el estado de las descargas (`/tracks`), gestionan las fuentes/playlists (`/sources`), manejan la subida de cookies (`/settings/cookies`), y encolan descargas individuales (`/tracks/download-single`).
- **`watcher.py` (WatcherThread)**: Un hilo en segundo plano que se ejecuta de forma paralela a FastAPI. Es el motor principal que procesa las fuentes (playlists) activas, sincroniza los cambios contra la base de datos (SQLite) utilizando la estrategia _ignore-on-delete_, e invoca a `yt-dlp`.
- **`downloader.py`**: Envuelve las llamadas a `yt-dlp` y `ffmpeg`. Configura las rutas de salida, incrusta las cookies si existen, y maneja la conversión a FLAC sin pérdida.
- **`metadata_handler.py`**: Usa la librería `mutagen` para etiquetar los archivos generados con ID3 estándar y portadas de álbum, preparando los archivos para ser indexados por servidores multimedia (como Plex o Jellyfin).

### Flujo de Estados de Descarga (Lifecycle)
Cada pista (`Track`) insertada en SQLite transita por varios estados representados en el modelo:
1. `pending`: El watcher la vio o la UI solicitó una descarga puntual.
2. `downloading` (implicito, manejado durante la ejecución activa).
3. `completed`: El archivo físico fue escrito en el disco duro exitosamente.
4. `failed`: Error en red, baneos de IP o restricciones territoriales de YouTube.
5. `ignored`: Si un usuario borra la canción en la UI, o si el source la borró remotamente en YouTube. Al marcarse como `ignored`, el watcher no intentará re-descargarla a menos que el usuario la restaure.

## Frontend (React + Vite)

Ubicado en la carpeta `/frontend/`.

Es una SPA (Single Page Application) minimalista enfocada en la usabilidad y legibilidad de datos.

### Características Clave
- **Renderizado Adaptativo**: Uso de CSS Vanilla (`index.css`) con variables HSL y soporte First-class para "Dark Mode" estilo Glassmorphism.
- **Estados Reactivos**: El `App.tsx` principal expone un dashboard unificado con filtros (`all`, `active`, `ignored`, `failed`). Refresca automáticamente el estado del servidor haciendo polling preventivo mínimo.
- **Gestión de Settings**: Un modal permite habilitar/pausar las descargas de un Source específico sin borrar el Source de la base de datos, y subir directamente el archivo `cookies.txt` enviando un multipart-form.

## Comunicación API

El Frontend llama al Backend a través de `/api`. Cuando corren en contenedores orquestados con `docker-compose.yml`, Traefik actúa como API Gateway, ruteando `http://[host]/api/*` directamente al contenedor FastAPI, y el tráfico restante al servidor estático Nginx que sirve el Frontend React.
