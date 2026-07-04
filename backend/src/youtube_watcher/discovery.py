"""Discovery reason constants for playlist/source sync decisions."""

UI_SINGLE = "ui_single"
PLAYLIST_DELTA = "playlist_delta"
INITIAL_IMPORT = "initial_import"
RESYNC = "resync"
REPAIR = "repair"
RETRY = "retry"

LATEST_ELIGIBLE_REASONS = {UI_SINGLE, PLAYLIST_DELTA}


def is_latest_eligible(reason: str | None) -> bool:
    """Return True when a discovery reason may add tracks to "Lo más nuevo"."""
    return reason in LATEST_ELIGIBLE_REASONS
