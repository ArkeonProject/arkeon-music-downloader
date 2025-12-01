# Guía de Testing - Sincronización Bidireccional

## ✅ Tests Automatizados (PASADOS)

Los tests automatizados han verificado que la funcionalidad está funcionando correctamente:

### Test 1: Detección de Videos Eliminados ✅
- Crea 3 archivos FLAC simulados
- Simula que 1 video fue eliminado de la playlist
- Verifica que el archivo se mueve a `.trash/` con timestamp
- Verifica que el estado persistente se actualiza correctamente

### Test 2: Auto-limpieza de .trash/ ✅
- Crea archivos antiguos (>7 días) y recientes en `.trash/`
- Ejecuta la auto-limpieza
- Verifica que solo se eliminan archivos antiguos
- Verifica que archivos recientes permanecen

## 🧪 Cómo Ejecutar los Tests

### Opción 1: Test Automatizado (Recomendado)

```bash
# Crear entorno virtual e instalar dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ejecutar tests
python3 scripts/test_sync_local.py
```

**Resultado esperado:**
```
✅ TEST 1 PASADO: Detección funcionando correctamente
✅ TEST 2 PASADO: Auto-limpieza funcionando correctamente
✅ TODOS LOS TESTS PASARON
```

### Opción 2: Test Manual con Playlist Real

#### Paso 1: Configurar Variables de Entorno

```bash
# Crear archivo .env
cp env.example .env

# Editar .env con tu configuración
nano .env
```

Configuración recomendada para testing:
```bash
PLAYLIST_URL=https://www.youtube.com/playlist?list=YOUR_TEST_PLAYLIST
DOWNLOAD_PATH=./test_downloads
ENABLE_SYNC_DELETIONS=true
USE_TRASH_FOLDER=true
TRASH_RETENTION_DAYS=1  # 1 día para testing rápido
LOG_LEVEL=DEBUG
```

#### Paso 2: Ejecutar el Watcher

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar watcher
python3 -m youtube_watcher
```

#### Paso 3: Probar Funcionalidades

**Test A: Descarga Nueva Canción**
1. Agrega una canción a tu playlist de YouTube Music
2. Espera ~60 segundos (intervalo de verificación)
3. Verifica que se descarga en `./test_downloads/`

**Test B: Eliminación con Papelera**
1. Elimina una canción de tu playlist
2. Espera ~60 segundos
3. Verifica que el archivo se movió a `./test_downloads/.trash/`
4. Verifica que el nombre incluye timestamp: `Artist - Title_2025-12-01_21-00-00.flac`

**Test C: Auto-limpieza**
1. Con `TRASH_RETENTION_DAYS=1`, espera 24 horas
2. El watcher eliminará automáticamente archivos antiguos de `.trash/`
3. Verifica logs: `🗑️ Auto-limpieza: eliminados X archivos de .trash/ (>1 días)`

## 🐳 Testing con Docker

### Opción 1: Docker Compose

```bash
# Editar docker-compose.yml o .env
ENABLE_SYNC_DELETIONS=true
USE_TRASH_FOLDER=true
TRASH_RETENTION_DAYS=7

# Construir y ejecutar
docker-compose up --build
```

### Opción 2: Docker Manual

```bash
# Construir imagen
docker build -t arkeon-music-downloader:test .

# Ejecutar con sync habilitado
docker run -d \
  --name music-watcher-test \
  -e PLAYLIST_URL="https://www.youtube.com/playlist?list=YOUR_PLAYLIST" \
  -e DOWNLOAD_PATH="/downloads" \
  -e ENABLE_SYNC_DELETIONS=true \
  -e USE_TRASH_FOLDER=true \
  -e TRASH_RETENTION_DAYS=7 \
  -e LOG_LEVEL=DEBUG \
  -v ./test_downloads:/downloads \
  arkeon-music-downloader:test

# Ver logs
docker logs -f music-watcher-test
```

## 📊 Logs Esperados

### Inicio con Sync Habilitado
```
Watcher iniciado para playlist: https://...
Directorio de descargas: /downloads
Intervalo de observación: 60000ms
Sincronización bidireccional habilitada (trash=True, retention=7d)
```

### Detección de Eliminación
```
🗑️ Detectadas 1 canciones eliminadas de la playlist
🗑️ Movido a .trash: Song Title -> Artist - Song Title_2025-12-01_21-00-00.flac
```

### Auto-limpieza
```
🗑️ Auto-limpieza: eliminados 3 archivos de .trash/ (>7 días)
```

## 🔍 Verificación Manual

### Verificar Estado Persistente

```bash
# Ver contenido de .downloaded.json
cat ./test_downloads/.downloaded.json | jq
```

Estructura esperada:
```json
{
  "video_ids": ["abc123", "def456"],
  "downloads": {
    "abc123": {
      "filename": "Artist - Title.flac",
      "downloaded_at": "2025-12-01T20:00:00",
      "title": "Title",
      "artist": "Artist"
    }
  }
}
```

### Verificar Carpeta .trash/

```bash
# Listar archivos en .trash con timestamps
ls -lh ./test_downloads/.trash/
```

## ⚠️ Troubleshooting

### Problema: Archivos no se eliminan

**Solución:**
- Verificar que `ENABLE_SYNC_DELETIONS=true`
- Verificar logs para errores
- Verificar permisos de escritura en directorio

### Problema: Auto-limpieza no funciona

**Solución:**
- Verificar que `TRASH_RETENTION_DAYS > 0`
- Verificar que archivos tienen timestamp válido en el nombre
- Verificar que han pasado suficientes días

### Problema: No se puede recuperar archivo de .trash

**Solución:**
```bash
# Mover archivo de vuelta a downloads
mv ./test_downloads/.trash/"Artist - Title_2025-12-01_21-00-00.flac" \
   ./test_downloads/"Artist - Title.flac"
```

## ✅ Checklist de Validación

Antes de usar en producción, verifica:

- [ ] Tests automatizados pasan correctamente
- [ ] Descarga de nuevas canciones funciona
- [ ] Eliminación mueve archivos a `.trash/`
- [ ] Archivos en `.trash/` tienen timestamp correcto
- [ ] Auto-limpieza elimina archivos antiguos
- [ ] Estado persistente se actualiza correctamente
- [ ] Logs son claros y descriptivos
- [ ] Funciona correctamente en Docker
- [ ] Permisos de archivos son correctos

## 🚀 Listo para Producción

Una vez validado todo, configura en tu servidor:

```bash
# En Portainer o docker-compose
ENABLE_SYNC_DELETIONS=true
USE_TRASH_FOLDER=true
TRASH_RETENTION_DAYS=7
```

Y disfruta de la sincronización bidireccional automática! 🎵
