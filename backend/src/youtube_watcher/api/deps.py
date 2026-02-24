from typing import Optional
from ..watcher import YouTubeWatcher

_global_watcher: Optional[YouTubeWatcher] = None

def get_watcher() -> Optional[YouTubeWatcher]:
    return _global_watcher

def set_watcher(watcher: YouTubeWatcher):
    global _global_watcher
    _global_watcher = watcher
