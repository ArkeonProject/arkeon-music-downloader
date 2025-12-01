FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    build-essential \
    python3-dev \
    zlib1g-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libtiff5 \
    libwebp-dev \
    libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/*

# Instalar yt-dlp version fija para reproducibilidad
ARG YT_DLP_VERSION=2024.08.06
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/download/${YT_DLP_VERSION}/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod +x /usr/local/bin/yt-dlp

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código Python
COPY src ./src

# Asegurar que los módulos del paquete estén en el PYTHONPATH
ENV PYTHONPATH="/app/src"

# Crear directorio de descargas
RUN mkdir -p /downloads

# Ejecutará con un usuario mapeado desde docker-compose (UID/GID)

# Variables de entorno por defecto
ENV PLAYLIST_URL=""
ENV DOWNLOAD_PATH="/downloads"
ENV OBSERVER_INTERVAL_MS="60000"

# Volumen para descargas
VOLUME ["/downloads"]

# Comando por defecto
CMD ["python", "-m", "youtube_watcher"]
