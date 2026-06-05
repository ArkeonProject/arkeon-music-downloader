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

El workflow `.github/workflows/cd.yml` se ejecuta en cada push a `main` y delega en
`ArkeonProject/organization-tools/.github/workflows/reusable-docker-build.yml` para
construir y publicar dos imágenes en GHCR:

- `ghcr.io/arkeonproject/arkeon-music-downloader/backend:<sha-corto>`
- `ghcr.io/arkeonproject/arkeon-music-downloader/frontend:<sha-corto>`

El mismo workflow puede llamar a los webhooks configurados en los secretos
`PORTAINER_WEBHOOK_BACKEND` y `PORTAINER_WEBHOOK_FRONTEND`, pero hay una limitación
importante: **un webhook de Portainer solo repuebla/recrea el stack con el compose
que Portainer ya tiene guardado**. Si ese compose usa tags estáticos por commit
como `backend:e598b5d` y `frontend:e598b5d`, el webhook no cambia el
`StackFileContent` a `backend:<nuevo-sha>` / `frontend:<nuevo-sha>` por sí solo.

Por tanto, el despliegue automático requiere una de estas estrategias:

1. **Tags móviles**: el compose de Portainer referencia un tag estable, por ejemplo
   `main` o `latest`, y el CD publica ese tag además del SHA. El webhook hace
   `pull`/redeploy del mismo tag.
2. **Actualización explícita del stack**: el CD o un operador actualiza el
   `StackFileContent` de Portainer para sustituir ambos tags por el nuevo SHA y
   redeployar el stack.

Mientras el stack de producción esté fijado a tags SHA, después de cada merge a
`main` hay que verificar que Portainer quedó apuntando al SHA nuevo. Una comprobación
rápida es revisar el stack file o los contenedores en ejecución:

```bash
# Ejemplo con Docker directo en el host
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' \
  | grep music-downloader
```

Para actualizar un servidor Docker Compose sin Portainer ni watchtower:

```bash
docker compose pull
docker compose up -d
```
