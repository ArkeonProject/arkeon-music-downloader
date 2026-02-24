from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

from youtube_watcher import metadata_handler
from youtube_watcher.metadata_handler import MetadataHandler


class DummyFLAC:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.tags = {}
        self.pictures = []
        self.saved = False

    def __setitem__(self, key, value):
        self.tags[key] = value

    def clear_pictures(self):
        self.pictures.clear()

    def add_picture(self, picture):
        self.pictures.append(picture)

    def save(self):
        self.saved = True


def _make_image_bytes(color: str = "red") -> bytes:
    image = Image.new("RGB", (10, 10), color=color)
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_add_metadata_and_cover_sets_tags(monkeypatch, tmp_path):
    dummy = DummyFLAC(tmp_path / "song.flac")
    monkeypatch.setattr(metadata_handler, "FLAC", lambda _: dummy)

    handler = MetadataHandler()
    add_cover_called = {"called": False}

    def fake_add_cover(audio, url, title):
        add_cover_called["called"] = True

    monkeypatch.setattr(handler, "_add_cover", fake_add_cover)

    handler.add_metadata_and_cover(
        flac_path=tmp_path / "song.flac",
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        year="2024",
        thumbnail_url="https://example.com/image.jpg",
    )

    assert dummy.tags["title"] == "Test Song"
    assert dummy.tags["artist"] == "Test Artist"
    assert dummy.tags["album"] == "Test Album"
    assert dummy.tags["date"] == "2024"
    assert add_cover_called["called"] is True
    assert dummy.saved is True


def test_process_image_returns_bytes():
    handler = MetadataHandler()
    img_bytes = handler._process_image(_make_image_bytes())
    assert isinstance(img_bytes, bytes)
    assert len(img_bytes) > 0


def test_add_cover_downloads_and_attaches_image(monkeypatch):
    handler = MetadataHandler()
    image_bytes = _make_image_bytes()

    class DummyResponse:
        status_code = 200
        headers = {"Content-Type": "image/png", "Content-Length": str(len(image_bytes))}

        def __init__(self):
            self.content = image_bytes

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        metadata_handler.requests, "get", lambda url, timeout, headers: DummyResponse()
    )

    audio = DummyFLAC(Path("fake.flac"))
    handler._add_cover(audio, "https://example.com/cover.png", "Song")

    assert len(audio.pictures) == 1
