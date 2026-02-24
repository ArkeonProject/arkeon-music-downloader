#!/bin/bash
# Script de instalación de dependencias del sistema para YouTube Playlist Watcher

set -e

echo "🎵 Instalando dependencias para YouTube Playlist Watcher..."
echo

# Detectar sistema operativo
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    echo "❌ Sistema operativo no soportado: $OSTYPE"
    exit 1
fi

echo "📱 Sistema operativo detectado: $OS"
echo

# Instalar yt-dlp
echo "📥 Instalando yt-dlp..."
if command -v yt-dlp &> /dev/null; then
    echo "✅ yt-dlp ya está instalado"
else
    if [[ "$OS" == "macos" ]]; then
        brew install yt-dlp
    elif [[ "$OS" == "linux" ]]; then
        sudo apt update
        sudo apt install -y yt-dlp
    else
        echo "⚠️  Instala yt-dlp manualmente desde: https://github.com/yt-dlp/yt-dlp"
    fi
fi

# Instalar ffmpeg
echo "🎬 Instalando ffmpeg..."
if command -v ffmpeg &> /dev/null; then
    echo "✅ ffmpeg ya está instalado"
else
    if [[ "$OS" == "macos" ]]; then
        brew install ffmpeg
    elif [[ "$OS" == "linux" ]]; then
        sudo apt update
        sudo apt install -y ffmpeg
    else
        echo "⚠️  Instala ffmpeg manualmente desde: https://ffmpeg.org/download.html"
    fi
fi

# Verificar Python
echo "🐍 Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "✅ Python $PYTHON_VERSION encontrado"
else
    echo "❌ Python 3 no está instalado"
    echo "Instala Python 3.11+ desde: https://www.python.org/downloads/"
    exit 1
fi

# Crear entorno virtual
echo "🔧 Configurando entorno virtual Python..."
if [[ ! -d "venv" ]]; then
    python3 -m venv venv
    echo "✅ Entorno virtual creado"
else
    echo "✅ Entorno virtual ya existe"
fi

# Activar entorno virtual e instalar dependencias
echo "📦 Instalando dependencias Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "🎉 ¡Instalación completada!"
echo
echo "Para usar el watcher:"
echo "1. Activa el entorno virtual: source venv/bin/activate"
echo "2. Configura las variables de entorno:"
echo "   export PLAYLIST_URL='https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID'"
echo "   export DOWNLOAD_PATH='./downloads'"
echo "3. Ejecuta: python youtube_watcher.py"
echo
echo "O usa Docker: docker-compose up -d"
