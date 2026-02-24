# Contributing to Arkeon Music Downloader

¡Gracias por tu interés en contribuir! Este documento proporciona guías para contribuir al proyecto web Fullstack (Monorepo).

## 🚀 Proceso de Desarrollo

### 1. Fork y Clone

```bash
git clone https://github.com/TU-USUARIO/arkeon-music-downloader.git
cd arkeon-music-downloader
```

### 2. Configurar Entorno de Desarrollo (Backend)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate 
pip install -e '.[dev]'
```

### 3. Configurar Entorno de Desarrollo (Frontend)

```bash
cd frontend
npm install
```

## 📝 Estándares de Código

### Python (Backend)
Usamos **Black** (formateador) y **flake8** (linter). El código fuente corre estrictamente en `backend/src`.
```bash
cd backend
black src/ tests/
flake8 src/ tests/ --max-line-length=88
```

### TypeScript/React (Frontend)
Usamos eslint pre-configurado para React 18 / Node.
```bash
cd frontend
npm run lint
```

## 🧪 Testing

Asegúrate de ejecutar los tests de integración en backend antes de declarar listo un Pull Request.
```bash
cd backend
PYTHONPATH=src pytest
```
Cualquier modificación visual sobre el UI Board deberá validar su consistencia de empaquetado vía `npx tsc -b && npm run build`.

## 🔄 Pull Requests

1. **Asegúrate que los tests de backend pasen**
2. **Asegúrate que la build statica del frontend funcione**
3. Push tu rama (ej. `feature/nueva-ui` o `fix/bug-base-datos`) y crea PR directo hacia `develop`.

Nuestra CI vía GitHub Actions ejecutará rutinas paralelas revisando backend y frontend por separado. Todos los checks deben pasar para permitir Merge. ¡Gracias por participar en el ecosistema Arkeon!
