"""
Tests para YouTube Playlist Watcher
"""

import pytest
from pathlib import Path
import json
from unittest.mock import Mock, patch

from youtube_watcher.watcher import YouTubeWatcher
from youtube_watcher.playlist_monitor import PlaylistMonitor
from youtube_watcher.downloader import YouTubeDownloader


class TestYouTubeWatcher:
    """Tests para la clase principal YouTubeWatcher"""

    def test_process_video_success(self, tmp_path, monkeypatch):
        watcher = YouTubeWatcher("https://example.com", str(tmp_path))
        video_data = {"id": "abc123", "title": "Song", "channel": "Artist"}

        def fake_download_and_convert(data):
            return {
                "success": True,
                "filename": "Artist - Song.flac",
                "title": "Song",
                "artist": "Artist",
            }

        monkeypatch.setattr(
            watcher.downloader, "download_and_convert", fake_download_and_convert
        )
        watcher._save_state = Mock()

        watcher._process_video(video_data)

        assert "abc123" in watcher.downloaded_videos
        assert watcher.downloads["abc123"]["filename"].endswith(".flac")
        watcher._save_state.assert_called_once()

    def test_process_video_skips_invalid_entries(self, tmp_path, monkeypatch):
        watcher = YouTubeWatcher("https://example.com", str(tmp_path))
        watcher.downloader.download_and_convert = Mock()

        watcher._process_video({"id": None, "title": None})
        watcher._process_video({"id": "abc", "title": "[Deleted video]"})
        watcher._process_video({"id": "def", "title": "   "})

        assert len(watcher.downloaded_videos) == 0
        watcher.downloader.download_and_convert.assert_not_called()

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

    def test_load_state_populates_downloaded_videos_from_downloads(self, tmp_path):
        """Debe cargar downloaded_videos desde las claves de downloads si falta video_ids"""
        state_file = tmp_path / ".downloaded.json"
        state_file.write_text(
            json.dumps(
                {
                    "downloads": {
                        "vid1": {"filename": "a.flac"},
                        "vid2": {"filename": "b.flac"},
                    }
                }
            ),
            encoding="utf-8",
        )

        watcher = YouTubeWatcher("https://example.com", str(tmp_path))

        assert watcher.downloads.keys() == {"vid1", "vid2"}
        assert watcher.downloaded_videos == {"vid1", "vid2"}

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
            "https://example.com", "./test_downloads", enable_sync_deletions=True
        )

        # Simular estado previo con 10 videos (para pasar el umbral del 80%)
        watcher.downloaded_videos = {f"vid{i}" for i in range(1, 11)}
        watcher.downloads = {
            f"vid{i}": {"filename": f"song{i}.flac", "title": f"Song {i}"}
            for i in range(1, 11)
        }

        # Simular playlist actual (vid10 eliminado, 9 de 10 = 90% > 80% threshold)
        current_videos = [{"id": f"vid{i}", "title": f"Song {i}"} for i in range(1, 10)]

        # Mock de _remove_file y _save_state
        watcher._remove_file = Mock()
        watcher._save_state = Mock()

        watcher._detect_and_remove_deleted_videos(current_videos)

        # Verificar que se llamó a remove para vid10
        watcher._remove_file.assert_called_once_with("song10.flac", "Song 10")

        # Verificar que se actualizó el estado
        assert "vid10" not in watcher.downloaded_videos
        assert "vid10" not in watcher.downloads
        watcher._save_state.assert_called_once()

    def test_detect_deleted_videos_ignores_invalid_entries(self):
        """Entradas inválidas ([Deleted], sin título) se tratan como ausentes"""
        watcher = YouTubeWatcher(
            "https://example.com", "./test_downloads", enable_sync_deletions=True
        )

        # Simular estado previo con 10 videos (para pasar el umbral del 80%)
        watcher.downloaded_videos = {f"vid{i}" for i in range(1, 11)}
        watcher.downloads = {
            f"vid{i}": {"filename": f"song{i}.flac", "title": f"Song {i}"}
            for i in range(1, 11)
        }

        # Playlist actual: 9 válidos + 1 inválido (vid10 como [Deleted video])
        current_videos = [{"id": f"vid{i}", "title": f"Song {i}"} for i in range(1, 10)]
        current_videos.append({"id": "vid10", "title": "[Deleted video]"})

        watcher._remove_file = Mock()
        watcher._save_state = Mock()

        watcher._detect_and_remove_deleted_videos(current_videos)

        # vid10 debe ser eliminado porque su entrada es inválida
        watcher._remove_file.assert_called_once_with("song10.flac", "Song 10")
        assert "vid10" not in watcher.downloaded_videos
        assert "vid10" not in watcher.downloads
        watcher._save_state.assert_called_once()

    @patch("shutil.move")
    @patch("pathlib.Path.exists")
    def test_remove_file_trash(self, mock_exists, mock_move):
        """Test de mover a papelera"""
        watcher = YouTubeWatcher(
            "https://example.com", "./test_downloads", use_trash_folder=True
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
            "https://example.com", "./test_downloads", use_trash_folder=False
        )
        mock_exists.return_value = True

        watcher._remove_file("song.flac", "Song")

        mock_unlink.assert_called_once()

    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.exists")
    def test_cleanup_trash(self, mock_exists, mock_glob):
        """Test de limpieza de papelera"""
        watcher = YouTubeWatcher(
            "https://example.com", "./test_downloads", trash_retention_days=7
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

    def test_download_latest_song_success(self, tmp_path):
        watcher = YouTubeWatcher("https://example.com", str(tmp_path))

        videos = [
            {"id": "old", "title": "Old Song", "upload_date": "20240101"},
            {"id": "new", "title": "New Song", "upload_date": "20241212"},
        ]

        watcher.monitor.get_playlist_videos = Mock(return_value=videos)
        watcher.downloader.download_and_convert = Mock(
            return_value={
                "success": True,
                "filename": "Artist - New Song.flac",
                "title": "New Song",
                "artist": "Artist",
            }
        )

        result = watcher.download_latest_song()

        assert result["id"] == "new"
        assert "new" in watcher.downloaded_videos

    def test_save_and_load_state(self, tmp_path):
        watcher = YouTubeWatcher("https://example.com", str(tmp_path))
        watcher.downloaded_videos = {"abc", "def"}
        watcher.downloads = {"abc": {"filename": "file.flac"}}
        watcher._save_state()

        reloaded = YouTubeWatcher("https://example.com", str(tmp_path))
        assert reloaded.downloaded_videos == {"abc", "def"}
        assert reloaded.downloads["abc"]["filename"] == "file.flac"

    def test_check_playlist_links_components(self, tmp_path):
        watcher = YouTubeWatcher(
            "https://example.com",
            str(tmp_path),
            enable_sync_deletions=True,
            use_trash_folder=True,
            trash_retention_days=1,
        )
        watcher.monitor.get_playlist_videos = Mock(
            return_value=[{"id": "x", "title": "Song"}]
        )
        watcher._process_video = Mock()
        watcher._detect_and_remove_deleted_videos = Mock()
        watcher._cleanup_trash_folder = Mock()

        watcher._check_playlist()

        watcher._process_video.assert_called_once()
        watcher._detect_and_remove_deleted_videos.assert_called_once()
        watcher._cleanup_trash_folder.assert_called_once()


class TestPlaylistMonitor:
    """Tests para PlaylistMonitor"""

    def test_init(self):
        """Test de inicialización"""
        monitor = PlaylistMonitor("https://example.com")
        assert monitor.playlist_url == "https://example.com"

    @patch("yt_dlp.YoutubeDL")
    def test_get_playlist_videos_success(self, mock_ydl_class):
        """Test de obtención exitosa de videos"""
        # Configurar el mock del context manager
        mock_ydl = mock_ydl_class.return_value.__enter__.return_value
        mock_ydl.extract_info.return_value = {
            "entries": [{"id": "123", "title": "Test Video"}]
        }

        monitor = PlaylistMonitor("https://example.com")
        videos = monitor.get_playlist_videos()

        assert len(videos) == 1
        assert videos[0]["id"] == "123"
        assert videos[0]["title"] == "Test Video"

    @patch("yt_dlp.YoutubeDL")
    def test_get_playlist_videos_failure(self, mock_ydl_class):
        """Test de fallo en obtención de videos"""
        # Configurar el mock del context manager
        mock_ydl = mock_ydl_class.return_value.__enter__.return_value
        mock_ydl.extract_info.side_effect = Exception("yt-dlp error")

        monitor = PlaylistMonitor("https://example.com")
        videos = monitor.get_playlist_videos()

        assert len(videos) == 0

    @patch("yt_dlp.YoutubeDL")
    def test_get_playlist_info_success(self, mock_ydl_class):
        mock_ydl = mock_ydl_class.return_value.__enter__.return_value
        mock_ydl.extract_info.return_value = {
            "title": "My Playlist",
            "uploader": "Tester",
            "entries": [{"id": "1"}, {"id": "2"}],
            "description": "Sample",
        }

        monitor = PlaylistMonitor("https://example.com")
        info = monitor.get_playlist_info()

        assert info["title"] == "My Playlist"
        assert info["video_count"] == 2


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
