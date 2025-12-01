# Contributing to Arkeon Music Downloader

¡Gracias por tu interés en contribuir! Este documento proporciona guías para contribuir al proyecto.

## 🚀 Proceso de Desarrollo

### 1. Fork y Clone

```bash
# Fork el repositorio en GitHub
# Luego clona tu fork
git clone https://github.com/TU-USUARIO/arkeon-music-downloader.git
cd arkeon-music-downloader
```

### 2. Configurar Entorno de Desarrollo

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias de desarrollo
pip install -e '.[dev]'

# Instalar pre-commit hooks
pre-commit install
```

### 3. Crear Rama de Feature

```bash
# Crear rama desde main
git checkout -b feature/mi-nueva-funcionalidad

# O para bugfixes
git checkout -b fix/descripcion-del-bug
```

## 📝 Estándares de Código

### Formateo

Usamos **Black** para formateo automático:

```bash
# Formatear código
black src/ tests/

# Verificar formato
black --check src/ tests/
```

### Linting

Usamos **flake8** para linting:

```bash
# Ejecutar linting
flake8 src/ tests/ --max-line-length=88
```

### Type Checking

Usamos **mypy** para type checking:

```bash
# Ejecutar type checking
mypy src/ --ignore-missing-imports
```

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Con coverage
pytest --cov=src --cov-report=term-missing

# Tests específicos
pytest tests/test_watcher.py
```

### Escribir Tests

- Coloca tests en el directorio `tests/`
- Nombra archivos como `test_*.py`
- Usa fixtures de pytest cuando sea apropiado
- Apunta a >80% de coverage

Ejemplo:

```python
def test_watcher_initialization():
    watcher = YouTubeWatcher(
        playlist_url="https://youtube.com/playlist?list=test",
        download_path="./test",
    )
    assert watcher.playlist_url == "https://youtube.com/playlist?list=test"
```

## 📋 Commits

### Formato de Commits

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Cambios en documentación
- `style`: Formateo, sin cambios de código
- `refactor`: Refactorización de código
- `test`: Agregar o modificar tests
- `chore`: Mantenimiento (deps, config, etc.)

**Ejemplos:**

```bash
git commit -m "feat(watcher): agregar sincronización bidireccional"
git commit -m "fix(downloader): corregir manejo de thumbnails"
git commit -m "docs: actualizar README con nuevas features"
```

## 🔄 Pull Requests

### Antes de Crear PR

1. **Asegúrate que los tests pasen:**
   ```bash
   pytest
   ```

2. **Verifica el formato:**
   ```bash
   black --check src/ tests/
   flake8 src/ tests/
   ```

3. **Actualiza documentación** si es necesario

4. **Actualiza CHANGELOG.md** en sección `Unreleased`

### Crear Pull Request

1. Push tu rama:
   ```bash
   git push origin feature/mi-nueva-funcionalidad
   ```

2. Crea PR en GitHub con:
   - **Título descriptivo** siguiendo Conventional Commits
   - **Descripción detallada** de los cambios
   - **Referencias** a issues relacionados
   - **Screenshots** si hay cambios visuales

### Template de PR

```markdown
## Descripción
Breve descripción de los cambios

## Tipo de cambio
- [ ] Bug fix
- [ ] Nueva funcionalidad
- [ ] Breaking change
- [ ] Documentación

## Checklist
- [ ] Tests pasan localmente
- [ ] Código formateado con Black
- [ ] Linting pasa (flake8)
- [ ] Documentación actualizada
- [ ] CHANGELOG.md actualizado

## Testing
Describe cómo probaste los cambios
```

## 🏗️ Estructura del Proyecto

```
.
├── src/youtube_watcher/    # Código fuente
│   ├── cli.py             # CLI
│   ├── watcher.py         # Watcher principal
│   ├── downloader.py      # Descarga y conversión
│   ├── playlist_monitor.py # Monitor de playlist
│   └── metadata_handler.py # Metadatos
├── tests/                 # Tests
├── scripts/               # Scripts de utilidad
├── docs/                  # Documentación
└── .github/              # CI/CD workflows
```

## 🐛 Reportar Bugs

Usa [GitHub Issues](https://github.com/ArkeonProject/arkeon-music-downloader/issues) con:

- **Descripción clara** del problema
- **Pasos para reproducir**
- **Comportamiento esperado** vs actual
- **Logs** relevantes
- **Entorno** (OS, Python version, Docker version)

## 💡 Sugerir Features

Abre un [GitHub Issue](https://github.com/ArkeonProject/arkeon-music-downloader/issues) con:

- **Descripción** de la feature
- **Caso de uso** / problema que resuelve
- **Propuesta de implementación** (opcional)

## 📜 Licencia

Al contribuir, aceptas que tus contribuciones serán licenciadas bajo la licencia MIT del proyecto.

## ❓ Preguntas

Si tienes preguntas, abre un [GitHub Discussion](https://github.com/ArkeonProject/arkeon-music-downloader/discussions) o contacta a los mantenedores.

---

¡Gracias por contribuir! 🎉
