# Guía de Testing y Validación

Con la arquitectura Monorepo (Backend + Frontend), el testing ahora cubre ambos dominios de manera separada, garantizando robustez en la API y fiabilidad en la Interfaz Web.

## 🧪 Backend (FastAPI + YouTube Watcher)

El backend de Python incluye una suite de tests robusta con `pytest` que verifica la lógica central en `src/youtube_watcher/` (Watcher, Downloader, Base de datos, API).

### Requisitos Previos (Local)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -e '.[dev]'
```

### Ejecutar Suite Entera de Tests (Unitarios)
Dado que los tests simulan las llamadas a red a YouTube (`yt-dlp`), se ejecutan super rápido sin descargar datos reales.

```bash
cd backend
PYTHONPATH=src pytest -v
```

### Tests de Integración Específicos
En `backend/tests/integration/` se encuentran tests valiosos para comprobar comportamientos que implican la interacción del watcher multihilo con dependencias como el manejo de errores en base de datos (`Ignore-on-Delete`) y descargas individuales asíncronas (`/tracks/download-single`).

## 🧪 Frontend (React + Vite)

El frontend contiene chequeos de tipado estricto y configuración unificada para linting, que ocurren previo al build production en la CI.

### Requisitos Previos
```bash
cd frontend
npm install
```

### Type Checking & Build Verification
El comando base que ejecuta el CI de Github Actions comprueba que la estructura estática en Typescript sea coherente:

```bash
cd frontend
# Verificar lint
npx eslint .
# Verificar compilación TypeScript
npx tsc -b
# Simular build estricto
npm run build
```

## 🐳 Validando el Despliegue en Docker (E2E)

Para asegurar que ambas partes colisionen y operen en coherencia (junto con el Traefik Router inverso), puedes montar una prueba funcional de Extremo a Extremo en local:

1. Levanta los contenedores en modo desarrollo con orquestación total:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d --build
   ```
2. Accede a `http://localhost:8080/` para ver si la UI levanta.
3. Asegurate de que la API de estado reporte las estadísticas haciendo click en Refresh List (`Fetch Data`).
4. Haz una carga temporal de `cookies.txt` en Settings y valida que tu navegador envía la petición HTTP multipart adecuadamente.

> [!NOTE]
> Es sumamente importante certificar que el endpoint `GET /api/tracks` responda de manera óptima ya que es la principal arteria del sistema.
