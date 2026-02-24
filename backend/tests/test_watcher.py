import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from youtube_watcher.watcher import YouTubeWatcher
from youtube_watcher.playlist_monitor import PlaylistMonitor
from youtube_watcher.db.models import Track, Source

class TestYouTubeWatcher:
    """Tests para la clase principal YouTubeWatcher (con DB mocking)"""

    def test_init(self):
        """Test de inicialización sin estado JSON"""
        watcher = YouTubeWatcher(
            download_path="./test_downloads",
            interval_ms=30000,
            enable_sync_deletions=True,
            use_trash_folder=True,
            trash_retention_days=7,
        )

        assert watcher.download_path == Path("./test_downloads")
        assert watcher.interval_ms == 30000
        assert watcher.enable_sync_deletions is True
        assert watcher.use_trash_folder is True
        assert watcher.trash_retention_days == 7
        assert isinstance(watcher.failed_downloads, dict)

    def test_process_video_skips_invalid_entries(self, tmp_path):
        watcher = YouTubeWatcher(str(tmp_path))
        watcher.downloader.download_and_convert = Mock()
        
        db_mock = MagicMock()
        
        watcher._process_video({"id": None, "title": None}, 1, db_mock)
        watcher._process_video({"id": "abc", "title": "[Deleted video]"}, 1, db_mock)
        watcher._process_video({"id": "def", "title": "   "}, 1, db_mock)

        # DB must not have been queried or inserted into
        db_mock.query.assert_not_called()
        db_mock.add.assert_not_called()
        watcher.downloader.download_and_convert.assert_not_called()

    def test_process_video_success_new_track(self, tmp_path):
        watcher = YouTubeWatcher(str(tmp_path))
        video_data = {"id": "abc123", "title": "Song", "channel": "Artist"}

        db_mock = MagicMock()
        # Mock para que retorne None al buscar el track (simulando que es nuevo)
        db_mock.query.return_value.filter.return_value.first.return_value = None

        def fake_download_and_convert(data):
            return {
                "success": True,
                "filename": "Artist - Song.flac",
                "title": "Song",
            }
        watcher.downloader.download_and_convert = Mock(side_effect=fake_download_and_convert)
        
        watcher._process_video(video_data, source_id=1, db=db_mock)

        # Verifica que se haya intentando añadir a la base de datos
        assert db_mock.add.called
        assert db_mock.commit.called
        assert watcher.downloader.download_and_convert.called

    def test_process_video_skips_completed_track(self, tmp_path):
        watcher = YouTubeWatcher(str(tmp_path))
        video_data = {"id": "abc123", "title": "Song"}

        db_mock = MagicMock()
        # Mock para que devuelva un track completado
        existing_track = Track(youtube_id="abc123", download_status="completed")
        db_mock.query.return_value.filter.return_value.first.return_value = existing_track
        watcher.downloader.download_and_convert = Mock()
        
        watcher._process_video(video_data, source_id=1, db=db_mock)

        # No se debe intentar descargar si ya está "completed"
        watcher.downloader.download_and_convert.assert_not_called()

    @patch("youtube_watcher.watcher.PlaylistMonitor")
    @patch("youtube_watcher.watcher.SessionLocal")
    def test_check_all_sources(self, mock_session_class, mock_monitor_class, tmp_path):
        """Testea el ciclo principal de revisión de fuentes en BD"""
        watcher = YouTubeWatcher(str(tmp_path), enable_sync_deletions=False)
        
        db_mock = MagicMock()
        mock_session_class.return_value.__enter__.return_value = db_mock
        
        # Simular una fuente activa devuelta por BD
        mock_source = Source(id=1, url="http://youtube", name="P1", status="active", type="playlist")
        db_mock.query.return_value.filter.return_value.all.return_value = [mock_source]
        
        # Simular que el monitor devuelve 1 video
        mock_monitor_instance = MagicMock()
        mock_monitor_instance.get_playlist_videos.return_value = [{"id": "vid1", "title": "Song"}]
        mock_monitor_class.return_value = mock_monitor_instance
        
        watcher._process_video = Mock()
        
        watcher._check_all_sources()
        
        # Verificar que se procesó el video con sus respectivos DB arguments
        watcher._process_video.assert_called_once_with({"id": "vid1", "title": "Song"}, 1, db_mock)


class TestPlaylistMonitor:
    """Tests para PlaylistMonitor"""

    def test_init(self):
        monitor = PlaylistMonitor("https://example.com")
        assert monitor.playlist_url == "https://example.com"

    @patch("yt_dlp.YoutubeDL")
    def test_get_playlist_videos_success(self, mock_ydl_class):
        mock_instance = mock_ydl_class.return_value
        
        # yt-dlp extract_info no longer accessed from context manager __enter__
        mock_instance.extract_info.side_effect = [{
            "entries": [{"id": "123", "title": "Test Video"}],
            "title": "Mock Playlist"
        }]

        monitor = PlaylistMonitor("https://example.com")
        videos = monitor.get_playlist_videos()
        assert len(videos) == 1
        assert videos[0]["id"] == "123"
        assert videos[0]["title"] == "Test Video"

    @patch("yt_dlp.YoutubeDL")
    def test_get_playlist_videos_failure(self, mock_ydl_class):
        mock_instance = mock_ydl_class.return_value
        mock_instance.extract_info.side_effect = Exception("yt-dlp error")
        monitor = PlaylistMonitor("https://example.com")
        videos = monitor.get_playlist_videos()
        
        assert len(videos) == 0

    @patch("yt_dlp.YoutubeDL")
    def test_get_playlist_info_success(self, mock_ydl_class):
        mock_instance = mock_ydl_class.return_value
        
        mock_instance.extract_info.return_value = {
            "title": "My Playlist",
            "uploader": "Tester",
            "entries": [{"id": "1"}, {"id": "2"}],
            "description": "Sample",
        }
        monitor = PlaylistMonitor("https://example.com")
        info = monitor.get_playlist_info()
        assert info["title"] == "My Playlist"
        assert info["video_count"] == 2
