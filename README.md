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

## 🐳 Instalación con Docker (Recomendado)

La forma más sencilla de ejecutar el proyecto es usando Docker Compose, el cual lanzará el backend, el frontend y Traefik (para enrutamiento inverso).

### 1. Variables de Entorno

Configura las variables de entorno principales en el `docker-compose.yml` local o a través de Portainer. Ya no se usa un archivo `.env` por defecto porque gran parte de la configuración ahora se maneja vía base de datos local y la UI.

### 2. Ejecutar

```bash
docker-compose up -d
```

### 3. Acceso

- **Frontend (Dashboard)**: `http://localhost:8080`
- **Backend (API Docs)**: `http://localhost:8080/api/docs`

## ⚙️ Configuración Vía Interfaz Web

En la esquina superior derecha del Dashboard, haz clic en **⚙️ Settings**:
1. **Fuentes Activas**: Aquí puedes añadir, pausar (⏸) o reanudar (▶) las playlists que el watcher está observando.
2. **Cookies de YouTube**: Sube un archivo `cookies.txt` exportado desde tu navegador para permitir la descarga de contenido bloqueado o privado.

> [!IMPORTANT]  
> YouTube bloquea descargas automatizadas frecuentemente. Es altamente recomendado subir tu `cookies.txt` en la vista de *Settings* de la UI para evitar errores 403.

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
- **CD (`cd.yml`)**: Al hacer push a `main`, construye y publica las imágenes Docker duales (`ghcr.io/.../backend` y `ghcr.io/.../frontend`) en GHCR de forma automática.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.
