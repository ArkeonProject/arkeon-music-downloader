FROM python:3.14-slim

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
    libtiff-dev \
    libwebp-dev \
    libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/*



# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código Python
COPY src ./src
COPY backfill_dates.py ./backfill_dates.py

# Asegurar que los módulos del paquete estén en el PYTHONPATH
ENV PYTHONPATH="/app/src"

# Crear directorio de descargas y base de datos con permisos abiertos
RUN mkdir -p /downloads /app/data /data && chmod -R 777 /downloads /app/data /data

# Ejecutará con un usuario mapeado desde docker-compose (UID/GID)

# Variables de entorno por defecto
ENV DOWNLOAD_PATH="/downloads"
ENV OBSERVER_INTERVAL_MS="60000"

# Exponer puerto de la API
EXPOSE 8000

# Volumen para descargas
VOLUME ["/downloads", "/data"]

# Comando por defecto para iniciar FastAPI backend
CMD ["uvicorn", "src.youtube_watcher.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
