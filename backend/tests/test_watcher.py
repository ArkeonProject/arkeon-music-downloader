from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

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
        watcher._add_to_navidrome_playlist = Mock()

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
        watcher._add_to_navidrome_playlist.assert_called_once_with(
            1,
            "abc123",
            "Song",
            is_new_download=True,
        )

    def test_process_video_skips_completed_track(self, tmp_path):
        watcher = YouTubeWatcher(str(tmp_path))
        video_data = {"id": "abc123", "title": "Song"}
        watcher._add_to_navidrome_playlist = Mock()

        db_mock = MagicMock()
        # Mock para que devuelva un track completado
        existing_track = Track(youtube_id="abc123", title="Song", download_status="completed")
        db_mock.query.return_value.filter.return_value.first.return_value = existing_track
        watcher.downloader.download_and_convert = Mock()
        
        watcher._process_video(video_data, source_id=1, db=db_mock)

        # No se debe intentar descargar si ya está "completed"
        watcher.downloader.download_and_convert.assert_not_called()
        watcher._add_to_navidrome_playlist.assert_called_once_with(
            1,
            "abc123",
            "Song",
            is_new_download=False,
        )

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

    def test_add_song_to_playlist_by_id_uses_song_id_to_add(self, tmp_path):
        watcher = YouTubeWatcher(str(tmp_path))
        client = Mock()
        client.get_playlist_songs.return_value = [{"id": "existing-song"}]
        client.update_playlist.return_value = True

        watcher._add_song_to_playlist_by_id(
            client,
            "playlist-1",
            "new-song",
            "Song",
            "Test Playlist",
        )

        client.update_playlist.assert_called_once_with("playlist-1", song_ids_to_add=["new-song"])

    @patch("youtube_watcher.watcher.time.sleep", return_value=None)
    def test_add_to_navidrome_playlist_triggers_scan_and_retries(self, _mock_sleep, tmp_path):
        watcher = YouTubeWatcher(str(tmp_path))
        watcher._add_song_to_playlist_by_id = Mock()
        watcher._find_navidrome_song_id = Mock(side_effect=[None, "song-nav"])

        source = Source(id=1, name="Playlist A", type="playlist", navidrome_playlist_id="pl-source")

        db_mock = MagicMock()
        db_mock.query.return_value.filter.return_value.first.return_value = source

        client_instance = Mock()
        client_instance.search_songs.side_effect = [[], [], [{"id": "song-nav", "title": "Song", "comment": ""}]]
        client_instance.start_scan.return_value = True
        client_instance.ensure_playlist.side_effect = ["pl-global", "pl-new"]

        with patch("youtube_watcher.navidrome_client.NavidromeClient", return_value=client_instance), \
             patch("youtube_watcher.db.database.SessionLocal") as mock_session, \
             patch("os.getenv") as mock_getenv:
            mock_session.return_value.__enter__.return_value = db_mock
            env = {
                "NAVIDROME_URL": "https://music.example.com",
                "NAVIDROME_USER": "user",
                "NAVIDROME_PASSWORD": "pass",
                "NAVIDROME_GLOBAL_PLAYLIST_NAME": "Toda la Musica",
                "NAVIDROME_NEW_PLAYLIST_NAME": "Lo más nuevo",
            }
            mock_getenv.side_effect = lambda key, default=None: env.get(key, default)

            watcher._add_to_navidrome_playlist(1, "yt123", "Song", is_new_download=True)

        client_instance.start_scan.assert_called_once_with()
        assert watcher._add_song_to_playlist_by_id.call_count == 3


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
