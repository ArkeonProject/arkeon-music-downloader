#!/usr/bin/env python3
"""
Test de integración con playlist real de YouTube Music.

Este test usa una playlist pública de testing:
https://music.youtube.com/playlist?list=PLH_LluK-ePJ__EFdCYCMfPy4oZjDfZF2k

IMPORTANTE: Este test requiere conexión a internet y acceso a YouTube.
"""

import os
import sys
import time
import shutil
from pathlib import Path

import pytest

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from youtube_watcher.watcher import YouTubeWatcher

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_PLAYLIST_TESTS"),
    reason="RUN_INTEGRATION_PLAYLIST_TESTS no está definido; este test es interactivo",
)

# Playlist de testing pública
TEST_PLAYLIST_URL = (
    "https://music.youtube.com/playlist?list=PLH_LluK-ePJ__EFdCYCMfPy4oZjDfZF2k"
)


def test_integration_full_workflow():
    """
    Test completo de integración con playlist real.

    Workflow:
    1. Inicializar watcher con playlist vacía
    2. Esperar a que agregues canciones manualmente
    3. Verificar que se descargan
    4. Esperar a que elimines canciones
    5. Verificar sincronización bidireccional
    """
    print("🧪 TEST DE INTEGRACIÓN - Workflow Completo")
    print("=" * 60)

    # Setup
    test_dir = Path("./test_integration")
    download_path = test_dir / "downloads"

    # Limpiar directorio anterior
    if test_dir.exists():
        shutil.rmtree(test_dir)

    download_path.mkdir(parents=True)

    print(f"\n📁 Directorio de testing: {download_path}")
    print(f"🎵 Playlist: {TEST_PLAYLIST_URL}")
    print()

    # Crear watcher con sync habilitado
    watcher = YouTubeWatcher(
        playlist_url=TEST_PLAYLIST_URL,
        download_path=str(download_path),
        interval_ms=30000,  # 30 segundos para testing
        enable_sync_deletions=True,
        use_trash_folder=True,
        trash_retention_days=1,
    )

    print("✅ Watcher inicializado")
    print()
    print("=" * 60)
    print("📋 INSTRUCCIONES DE TESTING MANUAL")
    print("=" * 60)
    print()
    print("1️⃣  FASE 1: Agregar Canciones")
    print(
        "   - Ve a: https://music.youtube.com/playlist?list=PLH_LluK-ePJ__EFdCYCMfPy4oZjDfZF2k"
    )
    print("   - Agrega 2-3 canciones a la playlist")
    print("   - Presiona ENTER cuando hayas agregado las canciones")
    print()

    input("   Presiona ENTER para continuar...")

    print()
    print("🔍 Verificando playlist...")
    videos = watcher.monitor.get_playlist_videos()
    print(f"   Canciones detectadas: {len(videos)}")

    if len(videos) == 0:
        print(
            "   ⚠️  No se detectaron canciones. Asegúrate de agregar canciones a la playlist."
        )
        return False

    for i, video in enumerate(videos, 1):
        print(f"   {i}. {video.get('title', 'Unknown')}")

    print()
    print("2️⃣  FASE 2: Descargar Canciones")
    print("   El watcher descargará las canciones automáticamente...")
    print()

    # Procesar descargas
    for video_data in videos:
        watcher._process_video(video_data)

    # Verificar descargas
    downloaded_files = list(download_path.glob("*.flac"))
    print(f"   ✅ Archivos descargados: {len(downloaded_files)}")
    for file in downloaded_files:
        print(f"      - {file.name}")

    print()
    print("=" * 60)
    print("3️⃣  FASE 3: Probar Sincronización Bidireccional")
    print("=" * 60)
    print()
    print("   - Elimina 1 canción de la playlist")
    print("   - Presiona ENTER cuando hayas eliminado la canción")
    print()

    input("   Presiona ENTER para continuar...")

    print()
    print("🔍 Verificando eliminaciones...")

    # Obtener playlist actualizada
    current_videos = watcher.monitor.get_playlist_videos()
    print(f"   Canciones actuales en playlist: {len(current_videos)}")

    # Detectar eliminaciones
    watcher._detect_and_remove_deleted_videos(current_videos)

    # Verificar .trash
    trash_folder = download_path / ".trash"
    if trash_folder.exists():
        trash_files = list(trash_folder.glob("*.flac"))
        print(f"   ✅ Archivos en .trash/: {len(trash_files)}")
        for file in trash_files:
            print(f"      - {file.name}")
    else:
        print("   ℹ️  No se creó carpeta .trash (no se eliminaron canciones)")

    # Verificar archivos restantes
    remaining_files = list(download_path.glob("*.flac"))
    print(f"   📁 Archivos restantes: {len(remaining_files)}")

    print()
    print("=" * 60)
    print("✅ TEST COMPLETADO")
    print("=" * 60)
    print()
    print("📊 Resumen:")
    print(f"   - Canciones iniciales: {len(videos)}")
    print(f"   - Canciones actuales: {len(current_videos)}")
    print(f"   - Archivos descargados: {len(downloaded_files)}")
    print(
        f"   - Archivos en .trash: {len(trash_files) if trash_folder.exists() else 0}"
    )
    print(f"   - Archivos restantes: {len(remaining_files)}")
    print()

    # Cleanup
    print("🧹 ¿Deseas limpiar el directorio de testing? (s/n): ", end="")
    try:
        response = input().lower()
        if response in ["s", "y", "yes", "si", "sí"]:
            shutil.rmtree(test_dir)
            print("   ✅ Directorio limpiado")
    except:
        pass

    return True


if __name__ == "__main__":
    print()
    print("🎵 ARKEON MUSIC DOWNLOADER - Integration Test")
    print()
    print("Este test usa una playlist real de YouTube Music.")
    print("Requiere interacción manual para agregar/eliminar canciones.")
    print()
    print("⚠️  IMPORTANTE:")
    print("   - Necesitas conexión a internet")
    print("   - Necesitas yt-dlp y ffmpeg instalados")
    print("   - La playlist debe ser pública o accesible")
    print()

    try:
        success = test_integration_full_workflow()
        if success:
            print()
            print("✅ Test de integración completado exitosamente!")
            sys.exit(0)
        else:
            print()
            print("❌ Test de integración falló")
            sys.exit(1)
    except KeyboardInterrupt:
        print()
        print("⚠️  Test interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ Error durante el test: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
