# Arkeon Music Downloader

[![CI](https://github.com/ArkeonProject/arkeon-music-downloader/actions/workflows/ci.yml/badge.svg)](https://github.com/ArkeonProject/arkeon-music-downloader/actions/workflows/ci.yml)
[![CD](https://github.com/ArkeonProject/arkeon-music-downloader/actions/workflows/cd.yml/badge.svg)](https://github.com/ArkeonProject/arkeon-music-downloader/actions/workflows/cd.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Este proyecto observa playlists de YouTube y descarga automáticamente nuevas canciones a FLAC con metadatos y portadas, gestionado a través de una **interfaz web (Dashboard)** interactiva.

## 🏗️ Arquitectura del Proyecto (Monorepo)

El proyecto está dividido en dos servicios principales:

```
.
├── backend/                        # Backend REST API (FastAPI) + Watcher
│   ├── src/youtube_watcher/        # Lógica de descarga y base de datos
│   ├── tests/                      # Tests unitarios (pytest)
│   ├── Dockerfile                  # Imagen del backend
│   └── requirements.txt            # Dependencias de Python
├── frontend/                       # Frontend Web UI (React + Vite)
│   ├── src/                        # Componentes y vistas
│   ├── Dockerfile                  # Imagen del frontend (Nginx)
│   └── package.json                # Dependencias de Node
└── docker-compose.yml              # Orquestación (Traefik, Backend, Frontend)
```

## 🚀 Funcionalidades

### Interfaz Web (Dashboard)
- **Gestión de Descargas**: Ver pistas descargadas, en progreso, ignoradas y fallidas.
- **Acciones Rápidas**: Descargar pistas individuales por URL, pausar/reanudar fuentes (playlists) y eliminar pistas.
- **Gestión de Cookies**: Subir el archivo `cookies.txt` directamente desde la interfaz de configuración (Settings) para evitar errores 403.
- **Ignore-on-Delete**: Las pistas eliminadas pasan a estado "ignorado" para evitar que se vuelvan a descargar en pasadas futuras del watcher, con la opción de restaurarlas.

### Motor de Descarga (Watcher)
- **Monitoreo continuo**: Observa periódicamente playlists de YouTube en segundo plano.
- **Descargas asíncronas**: No bloquea la API mientras se descargan pistas pesadas.
- **Calidad FLAC**: Convierte audio a formato FLAC sin pérdida usando `ffmpeg` y `yt-dlp`.
- **Metadatos completos**: Añade título, artista, álbum, año y portada (usando `mutagen` y `Pillow`).

## 🐳 Despliegue en Servidor (Paso a Paso)

Recomendamos usar Docker Compose para desplegar el proyecto en tu servidor (ej. VPS o NAS). El `docker-compose.yml` base incluye el backend, el frontend y un proxy inverso Traefik.

### Paso 1: Archivo Compose

Crea un archivo `docker-compose.yml` en tu servidor basado en el de este repositorio. Las imágenes oficiales ya están publicadas en GHCR.

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v3.1
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:8080"
    ports:
      - "8080:8080"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"

  backend:
    image: ghcr.io/arkeonproject/arkeon-music-downloader/backend:latest
    volumes:
      - /ruta/a/tu/musica:/downloads
      - ./data:/app/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=PathPrefix(`/api`)"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"

  frontend:
    image: ghcr.io/arkeonproject/arkeon-music-downloader/frontend:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=PathPrefix(`/`)"
      - "traefik.http.services.frontend.loadbalancer.server.port=80"
```

### Paso 2: Integración con Navidrome (u otros servidores multimedia)

La potencia de este proyecto radica en alimentar automáticamente tu servidor de música personal. En tu `docker-compose.yml`, donde dice `/ruta/a/tu/musica`, debes poner **la misma ruta que tu servidor Navidrome (o Plex/Jellyfin) está leyendo**.

Por ejemplo, si Navidrome lee de `/mnt/storage/media/music/`, el volumen del backend debe ser:
```yaml
    volumes:
      - /mnt/storage/media/music/:/downloads
```
De esta manera, tan pronto como el Watcher descarga un nuevo FLAC, aparecerá mágicamente en tu Navidrome.

### Paso 3: Arrancar el servicio

Levanta los contenedores:
```bash
docker compose up -d
```
Accede al Dashboard en la web visitando: `http://localhost:8080` (o la IP de tu servidor en el puerto 8080).

### Paso 4: Evitar Error 403 (Configurar Cookies)

YouTube bloquea descargas automatizadas frecuentemente. Para solucionarlo, debes proveer tus cookies de sesión usando el menú "Settings" ⚙️ del Dashboard web:

1. **Obtener tus cookies**:
   - Descarga una extensión como [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflccgomilekfcg) para Chrome/Brave.
   - Entra a [YouTube](https://www.youtube.com) habiendo iniciado sesión.
   - Haz clic en la extensión y selecciona "Export As cookies.txt".
2. **Subirlas a la App**:
   - En el Dashboard de la aplicación (`http://tu-servidor:8080`), ve a ⚙️ **Settings**.
   - Usa el botón de subida de archivos en la sección "Cookies de YouTube" y selecciona el `cookies.txt` que acabas de descargar.
   - Esto reiniciará internamente el motor local (`yt-dlp`) autorizando tus descargas sin necesitar reiniciar contenedores.

## 🛠️ Entorno de Desarrollo Local

Si deseas contribuir o modificar el código:

### Backend
Requiere Python 3.12+ e instalaciones de sistema (`ffmpeg`).
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e '.[dev]'

# Ejecutar servidor FastAPI de desarrollo
uvicorn src.youtube_watcher.api.main:app --reload --port 8000
```

### Frontend
Requiere Node.js 20+.
```bash
cd frontend
npm install

# Ejecutar servidor Vite de desarrollo
npm run dev
```

El frontend en desarrollo correrá en el puerto `5173` y estará configurado para atacar la API en el puerto `8000`.

## 🧩 Versionado, Releases y CI/CD

El proyecto utiliza GitHub Actions integradas con `ArkeonProject/organization-tools`.

- **CI (`ci.yml`)**: Verifica linting, tipos de TypeScript, y ejecuta tests de Python para cualquier PR hacia `develop` o `main`.
- **CD (`cd.yml`)**: Al hacer push a `main`, construye y publica las imágenes Docker duales (`ghcr.io/.../backend` y `ghcr.io/.../frontend`) en GHCR. Si Portainer usa tags fijos por SHA en su compose, el webhook no actualiza esos tags automáticamente; consulta [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#actualizaciones-y-cicd) antes de asumir que producción quedó desplegada.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.
