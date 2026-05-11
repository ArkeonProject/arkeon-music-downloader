from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy import text

from ..db.database import engine, Base
from . import routes
import threading
from ..watcher import YouTubeWatcher
from . import deps

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Run simple migrations for new columns
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE tracks ADD COLUMN published_at VARCHAR"))
except Exception:
    pass

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE tracks ADD COLUMN artist VARCHAR"))
except Exception:
    pass

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE sources ADD COLUMN navidrome_playlist_id VARCHAR"))
except Exception:
    pass


def _sync_existing_sources_to_navidrome():
    """Create missing Navidrome playlists for existing sources on startup"""
    import os
    from ..navidrome_client import NavidromeClient
    from ..db.database import SessionLocal
    from ..db.models import Source
    
    navidrome_url = os.getenv("NAVIDROME_URL")
    navidrome_user = os.getenv("NAVIDROME_USER")
    navidrome_password = os.getenv("NAVIDROME_PASSWORD")
    
    if not all([navidrome_url, navidrome_user, navidrome_password]):
        return
    
    try:
        client = NavidromeClient(navidrome_url, navidrome_user, navidrome_password)
        if not client.ping():
            logger.warning("Could not connect to Navidrome, skipping source sync")
            return
        
        with SessionLocal() as db:
            sources = db.query(Source).filter(
                Source.type.in_(["playlist", "artist"]),
                Source.navidrome_playlist_id.is_(None)
            ).all()
        
        for source in sources:
            playlist_id = client.ensure_playlist(source.name)
            if playlist_id:
                logger.info(f"Ensured Navidrome playlist '{source.name}' with ID: {playlist_id}")
            
            if playlist_id:
                with SessionLocal() as db:
                    db.query(Source).filter(Source.id == source.id).update(
                        {"navidrome_playlist_id": playlist_id}
                    )
                    db.commit()
                
                # Sync existing tracks to the playlist
                routes._sync_existing_tracks_to_navidrome(source.id, playlist_id, source.name)
        
        if sources:
            logger.info(f"✅ Synced {len(sources)} sources to Navidrome playlists")
        else:
            logger.info("All sources already have Navidrome playlists")
            
    except Exception as e:
        logger.error(f"Error syncing sources to Navidrome: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background watcher thread
    logger.info("Starting YouTube Watcher background thread...")
    import os
    # Por defecto usa carpeta local en desarrollo, en Docker será sobreescrita por /downloads
    download_path = os.getenv("DOWNLOAD_PATH", str(Path(__file__).parent.parent.parent.parent / "downloads"))
    interval = int(os.getenv("OBSERVER_INTERVAL_MS", "60000"))
    
    # Parse sync settings from environment
    enable_sync_deletions = str(os.getenv("ENABLE_SYNC_DELETIONS", "true")).lower() == "true"
    use_trash_folder = str(os.getenv("USE_TRASH_FOLDER", "true")).lower() == "true"
    trash_retention_days = int(os.getenv("TRASH_RETENTION_DAYS", "7"))
    
    # Comprobar si existe cookies.txt guardado en el volumen de data
    default_cookies = os.getenv("COOKIES_PATH", str(Path(__file__).parent.parent.parent.parent / "data" / "cookies.txt"))
    active_cookies = default_cookies if os.path.exists(default_cookies) else None
    
    watcher = YouTubeWatcher(
        download_path=download_path, 
        interval_ms=interval, 
        cookies_path=active_cookies,
        enable_sync_deletions=enable_sync_deletions,
        use_trash_folder=use_trash_folder,
        trash_retention_days=trash_retention_days
    )
    deps.set_watcher(watcher)
    
    watcher_thread = threading.Thread(target=watcher.start, daemon=True)
    watcher_thread.start()
    
    # Sync existing sources to Navidrome playlists (in background thread to not block startup)
    threading.Thread(target=_sync_existing_sources_to_navidrome, daemon=True).start()
    
    yield
    # Shutdown
    logger.info("Shutting down API and Watcher...")

app = FastAPI(
    title="YouTube Music Downloader API",
    description="API to manage multiple YouTube sources for automatic FLAC downloads",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "online", "message": "YouTube Music Downloader API running"}
