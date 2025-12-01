# Documentación del Proyecto

## Estructura del Código

### Módulos Principales

- **`watcher.py`**: Clase principal que coordina todo el proceso
- **`playlist_monitor.py`**: Monitorea playlists de YouTube
- **`downloader.py`**: Descarga y convierte videos a FLAC
- **`metadata_handler.py`**: Maneja metadatos y portadas
- **`cli.py`**: Interfaz de línea de comandos

### Flujo de Trabajo

1. **Inicialización**: El watcher se configura con URL y directorio
2. **Monitoreo**: Verifica la playlist cada intervalo configurado
3. **Detección**: Identifica videos nuevos no descargados
4. **Descarga**: Usa yt-dlp para obtener audio en Opus
5. **Conversión**: Convierte a FLAC con ffmpeg
6. **Metadatos**: Añade tags y portada embebida

## Configuración

### Variables de Entorno

- `PLAYLIST_URL`: URL de la playlist (requerido)
- `DOWNLOAD_PATH`: Directorio de salida (default: `./downloads`)
- `OBSERVER_INTERVAL_MS`: Intervalo en ms (default: `60000`)

### Herramientas Externas

- **yt-dlp**: Descarga de videos
- **ffmpeg**: Conversión de audio
- **Python 3.11+**: Runtime

## Desarrollo

### Instalación en Modo Desarrollo

```bash
# Clonar y configurar
git clone <repo>
cd arkeon-music-downloader
python -m venv venv
source venv/bin/activate

# Instalar en modo desarrollo
pip install -e ".[dev]"

# Ejecutar tests
pytest
```

### Estructura de Tests

- **`test_watcher.py`**: Tests para la clase principal
- **`test_playlist_monitor.py`**: Tests para monitoreo
- **`test_downloader.py`**: Tests para descarga
- **`test_metadata_handler.py`**: Tests para metadatos

### Herramientas de Calidad

- **pytest**: Framework de testing
- **black**: Formateador de código
- **flake8**: Linter
- **mypy**: Verificación de tipos

## Docker

### Construcción

```bash
docker build -t youtube-watcher .
```

### Ejecución

```bash
docker run -e PLAYLIST_URL="..." -v ./downloads:/downloads youtube-watcher
```

### Compose

```bash
export PLAYLIST_URL="..."
docker-compose up -d
```

## Troubleshooting

### Problemas Comunes

1. **yt-dlp no encontrado**: Instalar con `pip install yt-dlp`
2. **ffmpeg no encontrado**: Instalar con `brew install ffmpeg` (macOS)
3. **Dependencias Python**: Usar `pip install -r requirements.txt`

### Logs

El watcher proporciona logs detallados en stdout. Usar `docker logs` para contenedores.
