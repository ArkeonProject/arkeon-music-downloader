# Guía de Despliegue

Con la transición a arquitectura Monorepo (Frontend + Backend separados), el despliegue está ideado para ser orquestado exclusivamente vía **Docker Compose**. 

## Archivos Críticos de Despliegue

El directorio raíz contiene:
- `docker-compose.yml`: Archivo base principal orientado a producción (utilizado por el CD y despliegues estables vía Portainer o servidores privados).
- `docker-compose.dev.yml`: Archivo iterativo para pruebas que soporta "hot-reloading".

## Despliegue de Producción (Servidor Linux)

1. Ingresa a tu servidor u orquestador y crea un archivo `docker-compose.yml` utilizando las imágenes publicadas en GHCR:

```yaml
version: '3.8'

services:
  reverse-proxy:
    image: traefik:v3.1
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:8080"
      - "--accesslog=true"
    ports:
      - "8080:8080"
      - "8081:8080"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"

  backend:
    image: ghcr.io/arkeonproject/arkeon-music-downloader/backend:latest
    volumes:
      - /mnt/syncthing/music/downloads:/downloads
      - arkeon_music_db_data:/app/data
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

volumes:
  arkeon_music_db_data:
```

2. Ejecuta el stack:
```bash
docker compose up -d
```

3. El Dashboard de la aplicación estará disponible en modo reverso en el puerto configurado (ej: `http://localhost:8080`).

## Volumenes Importantes

El backend requiere persistencia de datos crucial.
- `/downloads`: Aquí se escriben los archivos `.flac`. Asegúrate de mapear esta ruta contra la carpeta física donde tienes montado Plex o Jellyfin.
- `/app/data`: Allí FastAPI creará `watcher.db` (base de datos relacional) donde habitan todas las fuentes y pistas.

---

## Actualizaciones y CI/CD

El pipeline CI/CD de GitHub empuja dos imágenes concurrentes cuando se completan merges hacia `main`:
- `ghcr.io/arkeonproject/arkeon-music-downloader/backend`
- `ghcr.io/arkeonproject/arkeon-music-downloader/frontend`

Para actualizar tu servidor (sin dependencias de watchtower):
```bash
docker compose pull
docker compose up -d
```
