#!/bin/bash
# Script de inicio rápido para YouTube Playlist Watcher

set -e

echo "🎵 YouTube Playlist Watcher - Inicio Rápido"
echo "=========================================="
echo

# Verificar si existe archivo .env
if [[ ! -f ".env" ]]; then
    echo "📝 Creando archivo de configuración..."
    if [[ -f "env.example" ]]; then
        cp env.example .env
        echo "✅ Archivo .env creado desde env.example"
        echo "⚠️  IMPORTANTE: Edita .env con tu PLAYLIST_URL antes de continuar"
        echo
        echo "Ejecuta: nano .env"
        echo "Luego vuelve a ejecutar este script"
        exit 1
    else
        echo "❌ No se encontró env.example"
        exit 1
    fi
fi

# Verificar PLAYLIST_URL
if ! grep -q "PLAYLIST_URL=" .env || grep -q "YOUR_PLAYLIST_ID" .env; then
    echo "❌ PLAYLIST_URL no está configurado en .env"
    echo "Edita .env y configura tu playlist antes de continuar"
    exit 1
fi

echo "✅ Configuración verificada"
echo

# Preguntar método de ejecución
echo "¿Cómo quieres ejecutar el watcher?"
echo "1) Docker Compose (Recomendado)"
echo "2) Python local"
echo "3) Docker manual"
echo
read -p "Selecciona una opción (1-3): " choice

case $choice in
    1)
        echo "🐳 Iniciando con Docker Compose..."
        docker-compose up -d
        echo "✅ Watcher iniciado en segundo plano"
        echo "Ver logs: docker-compose logs -f"
        echo "Detener: docker-compose down"
        ;;
    2)
        echo "🐍 Iniciando con Python local..."
        echo "Verificando dependencias..."
        
        if ! command -v python3 &> /dev/null; then
            echo "❌ Python 3 no está instalado"
            exit 1
        fi
        
        if ! command -v yt-dlp &> /dev/null; then
            echo "❌ yt-dlp no está instalado"
            echo "Ejecuta: ./scripts/install_dependencies.sh"
            exit 1
        fi
        
        if ! command -v ffmpeg &> /dev/null; then
            echo "❌ ffmpeg no está instalado"
            echo "Ejecuta: ./scripts/install_dependencies.sh"
            exit 1
        fi
        
        echo "✅ Dependencias verificadas"
        echo "Iniciando watcher..."
        
        # Cargar variables de entorno de forma segura
        set -a
        source ./.env
        set +a
        python3 -m youtube_watcher
        ;;
    3)
        echo "🐳 Iniciando con Docker manual..."
        echo "Construyendo imagen..."
        docker build -t youtube-watcher .
        
        echo "Ejecutando contenedor..."
        docker run -d \
            --name youtube-watcher \
            --env-file .env \
            -v $(pwd)/downloads:/downloads \
            youtube-watcher
        
        echo "✅ Watcher iniciado"
        echo "Ver logs: docker logs -f youtube-watcher"
        echo "Detener: docker stop youtube-watcher"
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac
