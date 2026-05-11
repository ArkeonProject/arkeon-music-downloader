"""
Navidrome Subsonic API Client
Handles playlist creation and management in Navidrome
"""

import hashlib
import logging
import requests
from typing import Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class NavidromeClient:
    """Client for Navidrome's Subsonic API"""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

    def _build_auth_params(self) -> dict[str, str]:
        """Build Subsonic authentication parameters"""
        import random
        import string
        salt = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        token = hashlib.md5(f"{self.password}{salt}".encode()).hexdigest()
        return {
            "u": self.username,
            "t": token,
            "s": salt,
            "v": "1.16.1",
            "c": "arkeon-music-downloader",
            "f": "json",
        }

    def _normalize_params(self, params: Optional[dict]) -> list[tuple[str, str]]:
        normalized = list(self._build_auth_params().items())
        if not params:
            return normalized

        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    normalized.append((key, str(item)))
            elif value is not None:
                normalized.append((key, str(value)))

        return normalized

    def _make_request(self, endpoint: str, params: Optional[dict] = None, method: str = "GET") -> Optional[dict]:
        """Make a request to the Subsonic API"""
        endpoint_path = f"rest/{endpoint}"
        url = urljoin(f"{self.base_url}/", endpoint_path)
        request_params = self._normalize_params(params)

        try:
            response = requests.get(url, params=request_params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            subsonic_response = data.get("subsonic-response", {})
            if subsonic_response.get("status") != "ok":
                error = subsonic_response.get("error", {})
                logger.error(f"Navidrome API error: {error.get('message', 'Unknown')} (code: {error.get('code')})")
                return None
            
            return subsonic_response
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Navidrome: {e}")
            return None
        except ValueError as e:
            logger.error(f"Failed to parse Navidrome response: {e}")
            return None

    def ping(self) -> bool:
        """Test connection to Navidrome"""
        result = self._make_request("ping")
        return result is not None

    def get_playlists(self) -> list[dict]:
        """Get all playlists from Navidrome"""
        result = self._make_request("getPlaylists")
        if result and "playlists" in result:
            return result["playlists"].get("playlist", [])
        return []

    def find_playlist_by_name(self, name: str) -> Optional[dict]:
        """Find a playlist by name"""
        playlists = self.get_playlists()
        normalized_name = name.strip().casefold()
        for playlist in playlists:
            playlist_name = str(playlist.get("name", "")).strip().casefold()
            if playlist_name == normalized_name:
                return playlist
        return None

    def ensure_playlist(self, name: str) -> Optional[str]:
        """Find playlist by name or create it if missing"""
        existing_playlist = self.find_playlist_by_name(name)
        if existing_playlist:
            return existing_playlist.get("id")

        return self.create_playlist(name)

    def create_playlist(self, name: str, song_ids: Optional[list[str]] = None) -> Optional[str]:
        """
        Create a new playlist in Navidrome
        Returns the playlist ID if successful, None otherwise
        """
        params = {"name": name}
        if song_ids:
            params["songId"] = song_ids

        result = self._make_request("createPlaylist", params)
        if result and "playlist" in result:
            playlist_id = result["playlist"].get("id")
            logger.info(f"Created Navidrome playlist '{name}' with ID: {playlist_id}")
            return playlist_id
        return None

    def update_playlist(
        self,
        playlist_id: str,
        name: Optional[str] = None,
        song_ids_to_add: Optional[list[str]] = None,
        song_indexes_to_remove: Optional[list[int]] = None,
    ) -> bool:
        """Update a playlist (add/remove songs, rename)"""
        params = {"playlistId": playlist_id}
        if name:
            params["name"] = name
        if song_ids_to_add:
            params["songIdToAdd"] = song_ids_to_add
        if song_indexes_to_remove:
            params["songIndexToRemove"] = song_indexes_to_remove

        result = self._make_request("updatePlaylist", params)
        return result is not None

    def start_scan(self, full_scan: bool = False) -> bool:
        """Trigger a Navidrome library scan"""
        params = {"fullScan": "true"} if full_scan else None
        result = self._make_request("startScan", params)
        return result is not None

    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist from Navidrome (songs remain in library)"""
        result = self._make_request("deletePlaylist", {"id": playlist_id})
        if result:
            logger.info(f"Deleted Navidrome playlist ID: {playlist_id}")
        return result is not None

    def get_playlist_songs(self, playlist_id: str) -> list[dict]:
        """Get all songs in a playlist"""
        result = self._make_request("getPlaylist", {"id": playlist_id})
        if result and "playlist" in result:
            return result["playlist"].get("entry", [])
        return []

    def playlist_exists(self, playlist_id: str) -> bool:
        """Check if a playlist exists by ID"""
        result = self._make_request("getPlaylist", {"id": playlist_id})
        return bool(result and "playlist" in result)

    def search_songs(self, query: str) -> list[dict]:
        """Search for songs in Navidrome"""
        result = self._make_request("search3", {"query": query})
        if result and "searchResult3" in result:
            return result["searchResult3"].get("song", [])
        return []

    def find_song_by_youtube_id(self, youtube_id: str) -> Optional[str]:
        """
        Find a song in Navidrome by YouTube ID stored in comment or title
        Returns the Navidrome song ID if found
        """
        songs = self.search_songs(youtube_id)
        for song in songs:
            comment = song.get("comment", "")
            title = song.get("title", "")
            if youtube_id in comment or youtube_id in title:
                return song.get("id")
        return None
