#!/usr/bin/env python3
"""
Script de testing para verificar la funcionalidad de sincronización bidireccional
sin necesidad de una playlist real de YouTube.

Uso: python3 scripts/test_sync_local.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from youtube_watcher.watcher import YouTubeWatcher


def create_test_environment():
    """Crear entorno de testing con archivos simulados"""
    test_dir = Path("./test_sync_demo")
    download_path = test_dir / "downloads"
    
    print("🧪 Creando entorno de testing...")
    test_dir.mkdir(exist_ok=True)
    download_path.mkdir(exist_ok=True)
    
    # Crear archivos FLAC de prueba
    files = [
        "Artist1 - Song1.flac",
        "Artist2 - Song2.flac",
        "Artist3 - Song3.flac",
    ]
    
    for filename in files:
        (download_path / filename).write_text("fake flac content")
    
    print(f"✅ Creados {len(files)} archivos de prueba")
    
    # Crear estado inicial
    state = {
        "video_ids": ["video1", "video2", "video3"],
        "downloads": {
            "video1": {
                "filename": "Artist1 - Song1.flac",
                "downloaded_at": datetime.now().isoformat(),
                "title": "Song1",
                "artist": "Artist1",
            },
            "video2": {
                "filename": "Artist2 - Song2.flac",
                "downloaded_at": datetime.now().isoformat(),
                "title": "Song2",
                "artist": "Artist2",
            },
            "video3": {
                "filename": "Artist3 - Song3.flac",
                "downloaded_at": datetime.now().isoformat(),
                "title": "Song3",
                "artist": "Artist3",
            },
        },
    }
    
    state_file = download_path / ".downloaded.json"
    state_file.write_text(json.dumps(state, indent=2))
    print("✅ Estado persistente creado")
    
    return download_path


def test_deletion_detection():
    """Test de detección de eliminaciones"""
    print("\n" + "="*60)
    print("TEST 1: Detección de Videos Eliminados")
    print("="*60)
    
    download_path = create_test_environment()
    
    # Crear watcher con sync habilitado
    watcher = YouTubeWatcher(
        playlist_url="https://www.youtube.com/playlist?list=test",
        download_path=str(download_path),
        interval_ms=60000,
        enable_sync_deletions=True,
        use_trash_folder=True,
        trash_retention_days=7,
    )
    
    print("\n📊 Estado inicial:")
    print(f"   Videos descargados: {len(watcher.downloaded_videos)}")
    print(f"   Archivos FLAC: {len(list(download_path.glob('*.flac')))}")
    
    # Simular playlist actual (sin video3)
    current_videos = [
        {"id": "video1", "title": "Song1"},
        {"id": "video2", "title": "Song2"},
        # video3 eliminado
    ]
    
    print("\n🔍 Simulando playlist actual (2 videos)...")
    print(f"   Videos en playlist: {len(current_videos)}")
    
    # Detectar eliminaciones
    watcher._detect_and_remove_deleted_videos(current_videos)
    
    print("\n📊 Estado después de detección:")
    print(f"   Videos descargados: {len(watcher.downloaded_videos)}")
    print(f"   Archivos FLAC: {len(list(download_path.glob('*.flac')))}")
    
    # Verificar .trash
    trash_folder = download_path / ".trash"
    if trash_folder.exists():
        trash_files = list(trash_folder.glob("*.flac"))
        print(f"   Archivos en .trash/: {len(trash_files)}")
        if trash_files:
            print(f"   └─ {trash_files[0].name}")
    
    # Verificar estado
    state_file = download_path / ".downloaded.json"
    state = json.loads(state_file.read_text())
    print("\n💾 Estado persistente:")
    print(f"   video_ids: {state['video_ids']}")
    print(f"   downloads keys: {list(state['downloads'].keys())}")
    
    # Validaciones
    assert len(watcher.downloaded_videos) == 2, "❌ Debería haber 2 videos"
    assert "video3" not in watcher.downloaded_videos, "❌ video3 debería estar eliminado"
    assert trash_folder.exists(), "❌ Carpeta .trash debería existir"
    assert len(list(trash_folder.glob("*.flac"))) == 1, "❌ Debería haber 1 archivo en .trash"
    
    print("\n✅ TEST 1 PASADO: Detección funcionando correctamente")
    return download_path


def test_trash_cleanup():
    """Test de auto-limpieza de .trash"""
    print("\n" + "="*60)
    print("TEST 2: Auto-limpieza de .trash/")
    print("="*60)
    
    download_path = Path("./test_sync_demo/downloads")
    trash_folder = download_path / ".trash"
    trash_folder.mkdir(exist_ok=True)
    
    # Crear archivo antiguo en .trash (simulando timestamp de hace 10 días)
    old_timestamp = "2025-11-21_20-00-00"
    old_file = trash_folder / f"OldSong_{old_timestamp}.flac"
    old_file.write_text("old content")
    
    # Crear archivo reciente
    recent_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    recent_file = trash_folder / f"RecentSong_{recent_timestamp}.flac"
    recent_file.write_text("recent content")
    
    print("\n📁 Archivos en .trash/ antes de limpieza:")
    for f in trash_folder.glob("*.flac"):
        print(f"   - {f.name}")
    
    # Crear watcher y ejecutar limpieza
    watcher = YouTubeWatcher(
        playlist_url="https://www.youtube.com/playlist?list=test",
        download_path=str(download_path),
        interval_ms=60000,
        enable_sync_deletions=True,
        use_trash_folder=True,
        trash_retention_days=7,  # 7 días de retención
    )
    
    print("\n🧹 Ejecutando auto-limpieza (retención: 7 días)...")
    watcher._cleanup_trash_folder()
    
    print("\n📁 Archivos en .trash/ después de limpieza:")
    remaining_files = list(trash_folder.glob("*.flac"))
    for f in remaining_files:
        print(f"   - {f.name}")
    
    # Validaciones
    assert not old_file.exists(), "❌ Archivo antiguo debería estar eliminado"
    assert recent_file.exists(), "❌ Archivo reciente debería permanecer"
    
    print("\n✅ TEST 2 PASADO: Auto-limpieza funcionando correctamente")


def cleanup_test_environment():
    """Limpiar entorno de testing"""
    import shutil
    test_dir = Path("./test_sync_demo")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("\n🧹 Entorno de testing limpiado")


def main():
    """Ejecutar todos los tests"""
    print("🧪 TESTING DE SINCRONIZACIÓN BIDIRECCIONAL")
    print("="*60)
    
    try:
        # Test 1: Detección de eliminaciones
        test_deletion_detection()
        
        # Test 2: Auto-limpieza
        test_trash_cleanup()
        
        print("\n" + "="*60)
        print("✅ TODOS LOS TESTS PASARON")
        print("="*60)
        print("\n💡 La funcionalidad está lista para usar en producción!")
        print("   Configura las variables de entorno y prueba con tu playlist real.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FALLIDO: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Preguntar si limpiar
        print("\n¿Deseas limpiar el entorno de testing? (s/n): ", end="")
        try:
            response = input().lower()
            if response in ['s', 'y', 'yes', 'si', 'sí']:
                cleanup_test_environment()
        except (EOFError, KeyboardInterrupt):
            pass


if __name__ == "__main__":
    main()
