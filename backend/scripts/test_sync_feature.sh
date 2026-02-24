#!/bin/bash
# Script de testing para sincronización bidireccional
# Uso: ./scripts/test_sync_feature.sh

set -e

echo "🧪 Testing de Sincronización Bidireccional"
echo "=========================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Directorio de testing
TEST_DIR="./test_sync_demo"
DOWNLOAD_PATH="$TEST_DIR/downloads"

echo "📁 Creando directorio de testing: $TEST_DIR"
rm -rf "$TEST_DIR"
mkdir -p "$DOWNLOAD_PATH"

# Crear archivos de prueba simulando descargas previas
echo ""
echo "📝 Creando archivos de prueba..."
touch "$DOWNLOAD_PATH/Artist1 - Song1.flac"
touch "$DOWNLOAD_PATH/Artist2 - Song2.flac"
touch "$DOWNLOAD_PATH/Artist3 - Song3.flac"
echo "   ✅ Creados 3 archivos FLAC de prueba"

# Crear estado simulado
echo ""
echo "💾 Creando estado persistente simulado..."
cat > "$DOWNLOAD_PATH/.downloaded.json" << 'EOF'
{
  "video_ids": [
    "video1",
    "video2",
    "video3"
  ],
  "downloads": {
    "video1": {
      "filename": "Artist1 - Song1.flac",
      "downloaded_at": "2025-12-01T20:00:00",
      "title": "Song1",
      "artist": "Artist1"
    },
    "video2": {
      "filename": "Artist2 - Song2.flac",
      "downloaded_at": "2025-12-01T20:00:00",
      "title": "Song2",
      "artist": "Artist2"
    },
    "video3": {
      "filename": "Artist3 - Song3.flac",
      "downloaded_at": "2025-12-01T20:00:00",
      "title": "Song3",
      "artist": "Artist3"
    }
  }
}
EOF
echo "   ✅ Estado persistente creado"

# Mostrar estado inicial
echo ""
echo "📊 Estado Inicial:"
echo "   Archivos en downloads/:"
ls -1 "$DOWNLOAD_PATH"/*.flac 2>/dev/null | wc -l | xargs echo "   -"
echo "   Videos en estado:"
cat "$DOWNLOAD_PATH/.downloaded.json" | grep -o '"video[0-9]"' | wc -l | xargs echo "   -"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "${YELLOW}⚠️  INSTRUCCIONES DE TESTING MANUAL${NC}"
echo ""
echo "Para probar la funcionalidad completa, necesitas:"
echo ""
echo "1️⃣  ${GREEN}Configurar variables de entorno:${NC}"
echo "    export PLAYLIST_URL='<tu_playlist_de_prueba>'"
echo "    export DOWNLOAD_PATH='$DOWNLOAD_PATH'"
echo "    export ENABLE_SYNC_DELETIONS=true"
echo "    export USE_TRASH_FOLDER=true"
echo "    export TRASH_RETENTION_DAYS=7"
echo "    export LOG_LEVEL=DEBUG"
echo ""
echo "2️⃣  ${GREEN}Ejecutar el watcher:${NC}"
echo "    python3 -m youtube_watcher"
echo ""
echo "3️⃣  ${GREEN}Verificar que:${NC}"
echo "    - Detecta nuevas canciones y las descarga"
echo "    - Si eliminas canciones de la playlist, mueve archivos a .trash/"
echo "    - Los archivos en .trash/ tienen timestamp"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "${YELLOW}🔬 TESTING RÁPIDO (sin playlist real):${NC}"
echo ""
echo "Puedes probar la lógica de eliminación manualmente:"
echo ""
echo "1. Edita $DOWNLOAD_PATH/.downloaded.json"
echo "2. Elimina 'video3' de la lista"
echo "3. Ejecuta el watcher"
echo "4. Verifica que Artist3 - Song3.flac se movió a .trash/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Directorio de testing creado en: $TEST_DIR"
echo ""
