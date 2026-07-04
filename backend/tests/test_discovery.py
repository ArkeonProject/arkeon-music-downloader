from youtube_watcher.discovery import (
    INITIAL_IMPORT,
    PLAYLIST_DELTA,
    REPAIR,
    RESYNC,
    UI_SINGLE,
    is_latest_eligible,
)


def test_latest_eligible_reasons_are_only_user_or_playlist_delta_events():
    assert is_latest_eligible(UI_SINGLE) is True
    assert is_latest_eligible(PLAYLIST_DELTA) is True
    assert is_latest_eligible(INITIAL_IMPORT) is False
    assert is_latest_eligible(RESYNC) is False
    assert is_latest_eligible(REPAIR) is False
    assert is_latest_eligible(None) is False
