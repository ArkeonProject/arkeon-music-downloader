"""
Tests para YouTube Playlist Watcher
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from youtube_watcher.watcher import YouTubeWatcher
from youtube_watcher.playlist_monitor import PlaylistMonitor
from youtube_watcher.downloader import YouTubeDownloader


class TestYouTubeWatcher:
    """Tests para la clase principal YouTubeWatcher"""

    def test_init(self):
        """Test de inicialización"""
        watcher = YouTubeWatcher(
            "https://example.com",
            "./test_downloads",
            30000,
            enable_sync_deletions=True,
            use_trash_folder=True,
            trash_retention_days=7,
        )

        assert watcher.playlist_url == "https://example.com"
        assert watcher.download_path == Path("./test_downloads")
        assert watcher.interval_ms == 30000
        assert watcher.enable_sync_deletions is True
        assert watcher.use_trash_folder is True
        assert watcher.trash_retention_days == 7
        assert len(watcher.downloaded_videos) == 0

    def test_get_stats(self):
        """Test de obtención de estadísticas"""
        watcher = YouTubeWatcher("https://example.com", "./test_downloads")
        stats = watcher.get_stats()

        assert stats["playlist_url"] == "https://example.com"
        assert stats["download_path"] == "./test_downloads"
        assert stats["interval_ms"] == 60000
        assert stats["downloaded_count"] == 0

    def test_detect_deleted_videos(self):
        """Test de detección de videos eliminados"""
        watcher = YouTubeWatcher(
            "https://example.com",
            "./test_downloads",
            enable_sync_deletions=True
        )
        
        # Simular estado previo
        watcher.downloaded_videos = {"vid1", "vid2"}
        watcher.downloads = {
            "vid1": {"filename": "song1.flac", "title": "Song 1"},
            "vid2": {"filename": "song2.flac", "title": "Song 2"}
        }
        
        # Simular playlist actual (vid2 eliminado)
        current_videos = [{"id": "vid1", "title": "Song 1"}]
        
        # Mock de _remove_file y _save_state
        watcher._remove_file = Mock()
        watcher._save_state = Mock()
        
        watcher._detect_and_remove_deleted_videos(current_videos)
        
        # Verificar que se llamó a remove para vid2
        watcher._remove_file.assert_called_once_with("song2.flac", "Song 2")
        
        # Verificar que se actualizó el estado
        assert "vid2" not in watcher.downloaded_videos
        assert "vid2" not in watcher.downloads
        watcher._save_state.assert_called_once()

    @patch("shutil.move")
    @patch("pathlib.Path.exists")
    def test_remove_file_trash(self, mock_exists, mock_move):
        """Test de mover a papelera"""
        watcher = YouTubeWatcher(
            "https://example.com",
            "./test_downloads",
            use_trash_folder=True
        )
        mock_exists.return_value = True
        
        watcher._remove_file("song.flac", "Song")
        
        mock_move.assert_called_once()
        args = mock_move.call_args[0]
        assert "song.flac" in str(args[0])
        assert ".trash" in str(args[1])

    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.exists")
    def test_remove_file_permanent(self, mock_exists, mock_unlink):
        """Test de eliminación permanente"""
        watcher = YouTubeWatcher(
            "https://example.com",
            "./test_downloads",
            use_trash_folder=False
        )
        mock_exists.return_value = True
        
        watcher._remove_file("song.flac", "Song")
        
        mock_unlink.assert_called_once()

    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.exists")
    def test_cleanup_trash(self, mock_exists, mock_glob):
        """Test de limpieza de papelera"""
        watcher = YouTubeWatcher(
            "https://example.com",
            "./test_downloads",
            trash_retention_days=7
        )
        mock_exists.return_value = True
        
        # Simular archivos: uno viejo, uno nuevo
        old_file = Mock()
        old_file.stem = "Song_2020-01-01_12-00-00"
        old_file.name = "Song_2020-01-01_12-00-00.flac"
        
        new_file = Mock()
        # Fecha muy futura para asegurar que es nuevo
        new_file.stem = "Song_2099-01-01_12-00-00"
        new_file.name = "Song_2099-01-01_12-00-00.flac"
        
        mock_glob.return_value = [old_file, new_file]
        
        watcher._cleanup_trash_folder()
        
        # El viejo debe ser eliminado
        old_file.unlink.assert_called_once()
        # El nuevo no
        new_file.unlink.assert_not_called()


class TestPlaylistMonitor:
    """Tests para PlaylistMonitor"""

    def test_init(self):
        """Test de inicialización"""
        monitor = PlaylistMonitor("https://example.com")
        assert monitor.playlist_url == "https://example.com"

    @patch("subprocess.run")
    def test_get_playlist_videos_success(self, mock_run):
        """Test de obtención exitosa de videos"""
        mock_result = Mock()
        mock_result.stdout = '{"id": "123", "title": "Test Video"}'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        monitor = PlaylistMonitor("https://example.com")
        videos = monitor.get_playlist_videos()

        assert len(videos) == 1
        assert videos[0]["id"] == "123"
        assert videos[0]["title"] == "Test Video"

    @patch("subprocess.run")
    def test_get_playlist_videos_failure(self, mock_run):
        """Test de fallo en obtención de videos"""
        mock_run.side_effect = Exception("yt-dlp error")

        monitor = PlaylistMonitor("https://example.com")
        videos = monitor.get_playlist_videos()

        assert len(videos) == 0


class TestYouTubeDownloader:
    """Tests para YouTubeDownloader"""

    def test_init(self):
        """Test de inicialización"""
        downloader = YouTubeDownloader("./test_downloads")
        assert downloader.download_path == Path("./test_downloads")

    def test_sanitize_filename(self):
        """Test de sanitización de nombres de archivo"""
        downloader = YouTubeDownloader("./test_downloads")

        # Test casos normales
        assert downloader._sanitize_filename("Test Song") == "Test Song"
        assert downloader._sanitize_filename("Test/Song") == "Test_Song"
        assert downloader._sanitize_filename("Test.Song.") == "Test.Song"

        # Test caracteres especiales
        assert downloader._sanitize_filename("Test@Song#") == "TestSong"
        assert downloader._sanitize_filename("Test Song (Remix)") == "Test Song Remix"


@pytest.fixture
def temp_dir(tmp_path):
    """Fixture para directorio temporal"""
    return tmp_path


@pytest.fixture
def sample_video_data():
    """Fixture para datos de video de ejemplo"""
    return {
        "id": "test123",
        "title": "Test Song",
        "artist": "Test Artist",
        "channel": "Test Channel",
        "uploader": "Test Uploader",
        "upload_date": "20230101",
        "thumbnail": "https://example.com/thumb.jpg",
    }
