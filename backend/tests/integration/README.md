# Integration Tests

Tests de integración con playlist real de YouTube Music.

## Playlist de Testing

**URL:** https://music.youtube.com/playlist?list=PLH_LluK-ePJ__EFdCYCMfPy4oZjDfZF2k

Esta es una playlist pública creada específicamente para testing del proyecto.

## Ejecutar Tests de Integración

### Requisitos

- Conexión a internet
- `yt-dlp` instalado
- `ffmpeg` instalado
- Dependencias Python instaladas

### Test Manual Interactivo

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar test de integración
python3 tests/integration/test_real_playlist.py
```

### Workflow del Test

El test guía a través de un workflow completo:

1. **Inicialización** - Crea watcher con la playlist de testing
2. **Agregar Canciones** - Te pide que agregues 2-3 canciones manualmente
3. **Verificar Descarga** - Verifica que las canciones se descarguen correctamente
4. **Eliminar Canción** - Te pide que elimines 1 canción de la playlist
5. **Verificar Sync** - Verifica que el archivo se mueva a `.trash/`

### Ejemplo de Salida

```
🧪 TEST DE INTEGRACIÓN - Workflow Completo
============================================================

📁 Directorio de testing: ./test_integration/downloads
🎵 Playlist: https://music.youtube.com/playlist?list=...

✅ Watcher inicializado

============================================================
📋 INSTRUCCIONES DE TESTING MANUAL
============================================================

1️⃣  FASE 1: Agregar Canciones
   - Ve a: https://music.youtube.com/playlist?list=...
   - Agrega 2-3 canciones a la playlist
   - Presiona ENTER cuando hayas agregado las canciones

   Presiona ENTER para continuar...

🔍 Verificando playlist...
   Canciones detectadas: 3
   1. Song Title 1
   2. Song Title 2
   3. Song Title 3

2️⃣  FASE 2: Descargar Canciones
   El watcher descargará las canciones automáticamente...

   ✅ Archivos descargados: 3
      - Artist1 - Song1.flac
      - Artist2 - Song2.flac
      - Artist3 - Song3.flac

============================================================
3️⃣  FASE 3: Probar Sincronización Bidireccional
============================================================

   - Elimina 1 canción de la playlist
   - Presiona ENTER cuando hayas eliminado la canción

   Presiona ENTER para continuar...

🔍 Verificando eliminaciones...
   Canciones actuales en playlist: 2
   ✅ Archivos en .trash/: 1
      - Artist3 - Song3_2025-12-01_21-30-00.flac
   📁 Archivos restantes: 2

============================================================
✅ TEST COMPLETADO
============================================================

📊 Resumen:
   - Canciones iniciales: 3
   - Canciones actuales: 2
   - Archivos descargados: 3
   - Archivos en .trash: 1
   - Archivos restantes: 2
```

## Casos de Prueba Sugeridos

### Test 1: Descarga Básica
1. Agregar 1 canción a la playlist
2. Verificar que se descarga correctamente
3. Verificar metadatos y portada

### Test 2: Sincronización Bidireccional
1. Agregar 3 canciones
2. Descargar todas
3. Eliminar 1 canción de la playlist
4. Verificar que se mueve a `.trash/`

### Test 3: Auto-limpieza
1. Configurar `TRASH_RETENTION_DAYS=0.001` (muy corto)
2. Eliminar canción
3. Esperar unos minutos
4. Verificar que se limpia automáticamente

### Test 4: Caracteres Especiales
1. Agregar canción con título que incluya:
   - Emojis: 🎵 🎶
   - Acentos: á é í ó ú ñ
   - Caracteres especiales: / \ : * ? " < > |
2. Verificar que el nombre del archivo es válido

### Test 5: Duplicados
1. Agregar canción
2. Descargar
3. Eliminar de playlist
4. Volver a agregar la misma canción
5. Verificar que no se descarga duplicado

## Notas

- La playlist está vacía por defecto
- Puedes agregar/eliminar canciones libremente para testing
- Los archivos descargados se guardan en `./test_integration/downloads/`
- El test limpia automáticamente al finalizar (opcional)

## Troubleshooting

### Error: "No se detectaron canciones"
- Verifica que agregaste canciones a la playlist
- Verifica que la playlist es pública
- Espera unos segundos después de agregar canciones

### Error: "yt-dlp not found"
```bash
# macOS
brew install yt-dlp

# Ubuntu/Debian
sudo apt install yt-dlp

# pip
pip install yt-dlp
```

### Error: "ffmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```
