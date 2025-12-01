# Guía de Despliegue - Rama de Testing

## 🚀 Desplegar Rama en Servidor

### Opción 1: Docker Compose con Rama Específica

#### Método A: Usando docker-compose.test.yml

```bash
# 1. Copiar docker-compose.test.yml a tu servidor
scp docker-compose.test.yml user@tu-servidor:/ruta/al/proyecto/

# 2. En el servidor, crear/editar .env
cat > .env << 'EOF'
PLAYLIST_URL=https://www.youtube.com/playlist?list=TU_PLAYLIST_ID
HOST_DOWNLOAD_PATH=/mnt/syncthing/music/
DOWNLOAD_PATH=/downloads
UID=1000
GID=1000

# Testing de sincronización bidireccional
ENABLE_SYNC_DELETIONS=true
USE_TRASH_FOLDER=true
TRASH_RETENTION_DAYS=7
LOG_LEVEL=DEBUG
EOF

# 3. Ejecutar con el archivo de test
docker-compose -f docker-compose.test.yml up -d

# 4. Ver logs
docker-compose -f docker-compose.test.yml logs -f
```

#### Método B: Modificar docker-compose.yml Temporal

```bash
# En tu servidor, editar docker-compose.yml
nano docker-compose.yml

# Cambiar la línea de build context a:
build:
  context: https://github.com/ArkeonProject/arkeon-music-downloader.git#feature-16-sincronizacion-bidireccional-de-playlist
```

### Opción 2: Clonar Rama Directamente en Servidor

```bash
# 1. SSH a tu servidor
ssh user@tu-servidor

# 2. Clonar el repositorio con la rama específica
git clone -b feature-16-sincronizacion-bidireccional-de-playlist \
  https://github.com/ArkeonProject/arkeon-music-downloader.git \
  arkeon-music-test

# 3. Entrar al directorio
cd arkeon-music-test

# 4. Configurar .env
cp env.example .env
nano .env

# Configurar:
PLAYLIST_URL=https://www.youtube.com/playlist?list=TU_PLAYLIST
HOST_DOWNLOAD_PATH=/mnt/syncthing/music/
ENABLE_SYNC_DELETIONS=true
USE_TRASH_FOLDER=true
TRASH_RETENTION_DAYS=7
LOG_LEVEL=DEBUG

# 5. Ejecutar con Docker Compose
docker-compose up -d

# 6. Ver logs
docker logs -f youtube-playlist-watcher
```

### Opción 3: Portainer con Rama Específica

Si usas Portainer:

#### Paso 1: Crear Stack de Testing

1. Ve a **Stacks** → **Add stack**
2. Nombre: `arkeon-music-test`
3. Build method: **Repository**
4. Repository URL: `https://github.com/ArkeonProject/arkeon-music-downloader`
5. Repository reference: `refs/heads/feature-16-sincronizacion-bidireccional-de-playlist`
6. Compose path: `docker-compose.yml`

#### Paso 2: Configurar Variables de Entorno

En la sección "Environment variables":

```
PLAYLIST_URL=https://www.youtube.com/playlist?list=TU_PLAYLIST
HOST_DOWNLOAD_PATH=/mnt/syncthing/music/
DOWNLOAD_PATH=/downloads
UID=1000
GID=1000
ENABLE_SYNC_DELETIONS=true
USE_TRASH_FOLDER=true
TRASH_RETENTION_DAYS=7
LOG_LEVEL=DEBUG
```

#### Paso 3: Deploy

Click en **Deploy the stack**

### Opción 4: Build Manual de Imagen Docker

```bash
# 1. En tu máquina local, hacer push de la rama
git push origin feature-16-sincronizacion-bidireccional-de-playlist

# 2. En el servidor, clonar y construir
ssh user@tu-servidor
git clone https://github.com/ArkeonProject/arkeon-music-downloader.git
cd arkeon-music-downloader
git checkout feature-16-sincronizacion-bidireccional-de-playlist

# 3. Construir imagen
docker build -t arkeon-music:test .

# 4. Ejecutar contenedor
docker run -d \
  --name arkeon-music-test \
  -e PLAYLIST_URL="https://www.youtube.com/playlist?list=TU_PLAYLIST" \
  -e DOWNLOAD_PATH="/downloads" \
  -e ENABLE_SYNC_DELETIONS=true \
  -e USE_TRASH_FOLDER=true \
  -e TRASH_RETENTION_DAYS=7 \
  -e LOG_LEVEL=DEBUG \
  -v /mnt/syncthing/music/:/downloads \
  arkeon-music:test

# 5. Ver logs
docker logs -f arkeon-music-test
```

## 🔍 Verificación

### Verificar que está usando la rama correcta

```bash
# Entrar al contenedor
docker exec -it youtube-playlist-watcher bash

# Verificar versión/rama (si agregaste info al código)
cat /app/src/youtube_watcher/__init__.py

# Ver logs de inicio
docker logs youtube-playlist-watcher 2>&1 | grep "Sincronización bidireccional"
```

Deberías ver:
```
Sincronización bidireccional habilitada (trash=True, retention=7d)
```

### Verificar Funcionalidad

```bash
# Ver archivos en el servidor
ls -lh /mnt/syncthing/music/

# Ver carpeta .trash si se crea
ls -lh /mnt/syncthing/music/.trash/

# Ver estado persistente
cat /mnt/syncthing/music/.downloaded.json | jq
```

## 🧹 Limpieza Después de Testing

### Si usaste docker-compose.test.yml

```bash
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.test.yml down -v  # Eliminar volúmenes también
```

### Si usaste stack separado

```bash
# Detener y eliminar contenedor
docker stop arkeon-music-test
docker rm arkeon-music-test

# Eliminar imagen de test (opcional)
docker rmi arkeon-music:test
```

### Volver a Main

```bash
# Cambiar de vuelta a main
cd arkeon-music-downloader
git checkout main
docker-compose up -d --build
```

## 📊 Monitoreo Durante Testing

```bash
# Ver logs en tiempo real
docker logs -f youtube-playlist-watcher

# Filtrar logs de sync
docker logs youtube-playlist-watcher 2>&1 | grep "🗑️"

# Ver uso de recursos
docker stats youtube-playlist-watcher

# Ver archivos creados recientemente
find /mnt/syncthing/music/ -type f -mmin -60  # Últimos 60 minutos
```

## ⚠️ Recomendaciones

1. **Usa un directorio de prueba** diferente al de producción:
   ```bash
   HOST_DOWNLOAD_PATH=/mnt/syncthing/music-test/
   ```

2. **Configura retención corta** para testing rápido:
   ```bash
   TRASH_RETENTION_DAYS=1  # 1 día en lugar de 7
   ```

3. **Habilita logs DEBUG** para ver todo:
   ```bash
   LOG_LEVEL=DEBUG
   ```

4. **Usa una playlist de prueba** pequeña, no tu playlist principal

5. **Monitorea los primeros días** antes de confiar completamente

## 🎯 Checklist de Testing en Servidor

- [ ] Rama desplegada correctamente
- [ ] Logs muestran "Sincronización bidireccional habilitada"
- [ ] Nueva canción se descarga correctamente
- [ ] Canción eliminada se mueve a `.trash/`
- [ ] Archivo en `.trash/` tiene timestamp correcto
- [ ] Auto-limpieza funciona después del período de retención
- [ ] No hay errores en logs
- [ ] Permisos de archivos son correctos

Una vez validado todo, puedes hacer merge a main y actualizar tu servidor a la versión estable! 🚀
