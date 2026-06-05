from unittest.mock import Mock, patch

from youtube_watcher.navidrome_client import NavidromeClient


class TestNavidromeClient:
    def test_update_playlist_serializes_song_ids_to_add_as_repeated_params(self):
        client = NavidromeClient("https://example.com", "user", "pass")

        with patch("youtube_watcher.navidrome_client.requests.get") as mock_get:
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {"subsonic-response": {"status": "ok"}}
            mock_get.return_value = response

            client.update_playlist("playlist-1", song_ids_to_add=["song-1", "song-2"])

        called_params = mock_get.call_args.kwargs["params"]
        song_params = [item for item in called_params if item[0] == "songIdToAdd"]
        assert song_params == [("songIdToAdd", "song-1"), ("songIdToAdd", "song-2")]

    def test_start_scan_sends_full_scan_when_requested(self):
        client = NavidromeClient("https://example.com", "user", "pass")

        with patch("youtube_watcher.navidrome_client.requests.get") as mock_get:
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {"subsonic-response": {"status": "ok"}}
            mock_get.return_value = response

            client.start_scan(full_scan=True)

        called_params = mock_get.call_args.kwargs["params"]
        assert ("fullScan", "true") in called_params

    def test_playlist_exists_returns_false_when_not_found(self):
        client = NavidromeClient("https://example.com", "user", "pass")
        client._make_request = Mock(return_value=None)

        assert client.playlist_exists("missing-id") is False

    def test_playlist_exists_returns_true_when_found(self):
        client = NavidromeClient("https://example.com", "user", "pass")
        client._make_request = Mock(return_value={"playlist": {"id": "abc"}})

        assert client.playlist_exists("abc") is True

    def test_ensure_playlist_reuses_existing_playlist(self):
        client = NavidromeClient("https://example.com", "user", "pass")
        client.get_playlists = Mock(
            return_value=[{"id": "existing-1", "name": "Lo más nuevo"}]
        )
        client.create_playlist = Mock()

        playlist_id = client.ensure_playlist("Lo más nuevo")

        assert playlist_id == "existing-1"
        client.create_playlist.assert_not_called()

    def test_ensure_playlist_creates_missing_playlist(self):
        client = NavidromeClient("https://example.com", "user", "pass")
        client.get_playlists = Mock(return_value=[])
        client.create_playlist = Mock(return_value="new-1")

        playlist_id = client.ensure_playlist("Toda la Musica")

        assert playlist_id == "new-1"
        client.create_playlist.assert_called_once_with("Toda la Musica")

    def test_get_playlists_returns_none_when_lookup_fails(self):
        client = NavidromeClient("https://example.com", "user", "pass")
        client._make_request = Mock(return_value=None)

        assert client.get_playlists() is None

    def test_ensure_playlist_does_not_create_when_lookup_fails(self):
        client = NavidromeClient("https://example.com", "user", "pass")
        client.get_playlists = Mock(return_value=None)
        client.create_playlist = Mock(return_value="should-not-create")

        playlist_id = client.ensure_playlist("Toda la Musica")

        assert playlist_id is None
        client.create_playlist.assert_not_called()

    def test_get_playlists_normalizes_single_playlist_response(self):
        client = NavidromeClient("https://example.com", "user", "pass")
        client._make_request = Mock(
            return_value={
                "playlists": {"playlist": {"id": "one", "name": "Toda la Musica"}}
            }
        )

        assert client.get_playlists() == [{"id": "one", "name": "Toda la Musica"}]

    def test_ensure_playlist_reuses_largest_matching_playlist_when_duplicates_exist(
        self,
    ):
        client = NavidromeClient("https://example.com", "user", "pass")
        client.get_playlists = Mock(
            return_value=[
                {"id": "duplicate-small", "name": "Toda la Musica", "songCount": 1},
                {"id": "canonical-large", "name": "Toda la Musica", "songCount": 452},
            ]
        )
        client.create_playlist = Mock()

        assert client.ensure_playlist("Toda la Musica") == "canonical-large"
        client.create_playlist.assert_not_called()
