from __future__ import annotations

from pathlib import Path
from typing import Any

from youtube_watcher import downloader as downloader_module
from youtube_watcher.downloader import YouTubeDownloader


def test_download_and_convert_success(monkeypatch, tmp_path):
    downloader = YouTubeDownloader(str(tmp_path))
    temp_file = tmp_path / "temp_testid.opus"

    def mock_download(video_data, title):
        temp_file.write_text("opus")
        return temp_file, {"upload_date": "20230101"}

    def mock_convert(opus_path, output_path, title):
        output_path.write_text("flac")
        return True

    metadata_calls = {"called": False}

    def mock_metadata(*args, **kwargs):
        metadata_calls["called"] = True

    monkeypatch.setattr(downloader, "_download_opus", mock_download)
    monkeypatch.setattr(downloader, "_convert_to_flac", mock_convert)
    downloader.metadata_handler.add_metadata_and_cover = mock_metadata

    data = {"id": "testid", "title": "Song", "channel": "Artist"}
    result = downloader.download_and_convert(data)

    assert result is not None
    assert Path(result["filename"]).suffix == ".flac"
    assert (tmp_path / result["filename"]).exists()
    assert metadata_calls["called"] is True


def test_download_and_convert_download_failure(monkeypatch, tmp_path):
    downloader = YouTubeDownloader(str(tmp_path))
    monkeypatch.setattr(downloader, "_download_opus", lambda data, title: None)

    result = downloader.download_and_convert({"id": "fail", "title": "Song"})

    assert result is None


def test_download_opus_returns_downloaded_file(monkeypatch, tmp_path):
    downloader = YouTubeDownloader(str(tmp_path))
    video_id = "abc123"

    class DummyYDL:
        def __init__(self, opts: dict[str, Any]):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

        def download(self, urls):
            (tmp_path / f"temp_{video_id}.webm").write_text("data")
            
        def extract_info(self, url, download=True):
            (tmp_path / f"temp_{video_id}.webm").write_text("data")
            return {"upload_date": "20230101"}

    monkeypatch.setattr(
        downloader_module.yt_dlp, "YoutubeDL", lambda opts: DummyYDL(opts)
    )
    
    # Reinicializar downloader para que coja el mock
    downloader._ydl = DummyYDL({})

    path, info = downloader._download_opus({"id": video_id}, "Test Title")

    assert path is not None
    assert path.name == f"temp_{video_id}.webm"
    assert path.exists()
    assert info.get("upload_date") == "20230101"
