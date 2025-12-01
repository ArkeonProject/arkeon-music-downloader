import logging
import os
from types import SimpleNamespace

from youtube_watcher import cli


def test_get_environment_config(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYLIST_URL", "https://music.youtube.com/playlist?list=PL123")
    monkeypatch.setenv("DOWNLOAD_PATH", str(tmp_path / "dl"))
    monkeypatch.setenv("OBSERVER_INTERVAL_MS", "12345")
    monkeypatch.setenv("COOKIES_FILE", "/tmp/cookies.txt")
    monkeypatch.setenv("ENABLE_SYNC_DELETIONS", "true")
    monkeypatch.setenv("USE_TRASH_FOLDER", "false")
    monkeypatch.setenv("TRASH_RETENTION_DAYS", "5")

    config = cli.get_environment_config()

    assert config[0] == "https://music.youtube.com/playlist?list=PL123"
    assert config[1] == str(tmp_path / "dl")
    assert config[2] == 12345
    assert config[3] == "/tmp/cookies.txt"
    assert config[4] is True
    assert config[5] is False
    assert config[6] == 5


def test_validate_config_rejects_invalid_url(caplog, tmp_path):
    caplog.set_level(logging.ERROR)
    ok = cli.validate_config("https://invalid.example.com", str(tmp_path))
    assert ok is False
    assert "URL válida de YouTube" in caplog.text


def test_validate_config_success(tmp_path, caplog):
    caplog.set_level(logging.ERROR)
    playlist_url = "https://music.youtube.com/playlist?list=PL123"
    download_dir = tmp_path / "downloads"

    ok = cli.validate_config(playlist_url, str(download_dir))

    assert ok is True
    assert download_dir.exists()
    assert ".write_test" not in os.listdir(download_dir)


def _build_args(**overrides):
    defaults = dict(
        latest_only=True,
        playlist_url=None,
        download_path=None,
        cookies=None,
        enable_sync_deletions=False,
        disable_trash=False,
        trash_retention_days=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_main_latest_only(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYLIST_URL", "https://music.youtube.com/playlist?list=PLENV")
    monkeypatch.setenv("DOWNLOAD_PATH", str(tmp_path / "dl"))

    args = _build_args(latest_only=True)
    monkeypatch.setattr(
        cli.argparse.ArgumentParser, "parse_args", lambda self: args, raising=False
    )

    class DummyWatcher:
        def __init__(self, *a, **kw):
            self.download_latest_song_called = False
            self.start_called = False

        def download_latest_song(self):
            self.download_latest_song_called = True
            return {"title": "Song", "success": True}

        def start(self):
            self.start_called = True

    created = {}

    def fake_watcher(*a, **kw):
        created["instance"] = DummyWatcher()
        return created["instance"]

    monkeypatch.setattr(cli, "YouTubeWatcher", fake_watcher)

    cli.main()

    assert created["instance"].download_latest_song_called is True
    assert created["instance"].start_called is False


def test_main_monitor_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("PLAYLIST_URL", "https://music.youtube.com/playlist?list=PLENV")
    monkeypatch.setenv("DOWNLOAD_PATH", str(tmp_path / "dl"))

    args = _build_args(latest_only=False)
    monkeypatch.setattr(
        cli.argparse.ArgumentParser, "parse_args", lambda self: args, raising=False
    )

    class DummyWatcher:
        def __init__(self, *a, **kw):
            self.download_latest_song_called = False
            self.start_called = False

        def download_latest_song(self):
            self.download_latest_song_called = True
            return None

        def start(self):
            self.start_called = True

    created = {}

    def fake_watcher(*a, **kw):
        created["instance"] = DummyWatcher()
        return created["instance"]

    monkeypatch.setattr(cli, "YouTubeWatcher", fake_watcher)

    cli.main()

    assert created["instance"].start_called is True
