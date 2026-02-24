from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from ..db.database import engine, Base
from . import routes
import threading
from ..watcher import YouTubeWatcher

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background watcher thread
    logger.info("Starting YouTube Watcher background thread...")
    import os
    # Por defecto usa carpeta local en desarrollo, en Docker será sobreescrita por /downloads
    download_path = os.getenv("DOWNLOAD_PATH", str(Path(__file__).parent.parent.parent.parent / "downloads"))
    interval = int(os.getenv("OBSERVER_INTERVAL_MS", "60000"))
    
    watcher = YouTubeWatcher(download_path=download_path, interval_ms=interval)
    watcher_thread = threading.Thread(target=watcher.start, daemon=True)
    watcher_thread.start()
    
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
