from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
import os
from pathlib import Path

from ..db.database import get_db
from ..db.models import Source, Track
from .deps import get_watcher

router = APIRouter()

# --- Schemas ---

class SourceCreate(BaseModel):
    url: str
    name: str
    type: str = "playlist" # playlist, artist, channel

class SourceResponse(BaseModel):
    id: int
    url: str
    name: str
    type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class TrackResponse(BaseModel):
    id: int
    youtube_id: str
    title: str
    source_id: int | None
    source_name: str | None = None
    source_type: str | None = None
    file_path: str | None
    download_status: str
    downloaded_at: datetime | None
    created_at: datetime
    published_at: str | None = None
    artist: str | None = None

    class Config:
        from_attributes = True

class PaginatedTracks(BaseModel):
    items: List[TrackResponse]
    total: int
    page: int
    pages: int

class SingleDownloadRequest(BaseModel):
    url: str
    
# --- Source Routes ---

@router.get("/sources", response_model=List[SourceResponse])
def get_sources(db: Session = Depends(get_db)):
    """List all configured download sources"""
    sources = db.query(Source).all()
    return sources

@router.post("/sources", response_model=SourceResponse)
def create_source(source: SourceCreate, db: Session = Depends(get_db)):
    """Add a new source to monitor"""
    db_source = db.query(Source).filter(Source.url == source.url).first()
    if db_source:
        raise HTTPException(status_code=400, detail="Source URL already registered")
    
    new_source = Source(**source.model_dump())
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return new_source

@router.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Remove a source"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    db.delete(source)
    db.commit()
    return {"status": "success", "message": f"Source {source_id} deleted"}

@router.put("/sources/{source_id}/status")
def update_source_status(source_id: int, status: str, db: Session = Depends(get_db)):
    """Pause or resume a source"""
    if status not in ["active", "paused"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
        
    source.status = status
    db.commit()
    return {"status": "success", "new_status": status}

# --- Track Routes ---

@router.get("/tracks", response_model=PaginatedTracks)
def get_tracks(
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    source_id: int | None = None,
    artist: str | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    """List downloaded and pending tracks with optional filters and pagination"""
    query = db.query(Track)
    
    if status and status != 'all':
        query = query.filter(Track.download_status == status)
    if source_id:
        query = query.filter(Track.source_id == source_id)
    if artist:
        query = query.filter(Track.artist == artist)
    if search:
        query = query.filter(Track.title.ilike(f"%{search}%"))
        
    valid_sort_columns = {"created_at": Track.created_at, "downloaded_at": Track.downloaded_at, "published_at": Track.published_at}
    sort_column = valid_sort_columns.get(sort_by, Track.created_at)
    
    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.is_(None), sort_column.asc(), Track.id.desc())
    else:
        query = query.order_by(sort_column.is_(None), sort_column.desc(), Track.id.desc())
        
    total = query.count()
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    skip = (page - 1) * page_size
    tracks = query.offset(skip).limit(page_size).all()
    
    # Enrich with source name
    result = []
    for t in tracks:
        data = TrackResponse.model_validate(t).model_dump()
        if t.source:
            data["source_name"] = t.source.name
            data["source_type"] = t.source.type
        result.append(data)
    
    return {"items": result, "total": total, "page": page, "pages": pages}

@router.get("/tracks/artists", response_model=List[str])
def get_artists(db: Session = Depends(get_db)):
    """Get unique list of artists for filtering"""
    artists = db.query(Track.artist).filter(Track.artist.isnot(None)).distinct().all()
    # Filter out empty strings if any crept in
    valid_artists = [a[0] for a in artists if a[0] and a[0].strip()]
    return sorted(valid_artists)

@router.post("/tracks/download-single")
def trigger_single_download(req: SingleDownloadRequest, db: Session = Depends(get_db)):
    """Extract video info and trigger download immediately"""
    import re
    import threading
    
    # Extract youtube video ID from URL
    url = req.url.strip()
    match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if not match:
        raise HTTPException(status_code=400, detail="URL de YouTube no válida")
    
    video_id = match.group(1)
    
    # Check if already exists
    existing = db.query(Track).filter(Track.youtube_id == video_id).first()
    if existing:
        if existing.download_status == "completed":
            return {"status": "already_exists", "title": existing.title}
        if existing.download_status == "ignored":
            existing.download_status = "pending"
            db.commit()
    
    if not existing:
        # Create pending record — the title will be updated after download
        existing = Track(
            youtube_id=video_id,
            title=f"Descargando... ({video_id})",
            source_id=None,
            download_status="pending"
        )
        db.add(existing)
        db.commit()
    
    # Trigger download via the watcher in a background thread
    watcher = get_watcher()
    if watcher:
        video_data = {"id": video_id, "title": existing.title, "url": url}
        def _download():
            try:
                from ..db.database import SessionLocal
                with SessionLocal() as bg_db:
                    watcher._process_video(video_data, source_id=None, db=bg_db)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error descargando {video_id}: {e}")
        
        threading.Thread(target=_download, daemon=True).start()
    
    return {"status": "downloading", "video_id": video_id}

@router.delete("/tracks/{track_id}")
def delete_track(track_id: int, db: Session = Depends(get_db)):
    """Delete a track's file and mark it as ignored so it won't be re-downloaded"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    # 1. Physically delete the file if it exists
    import os
    if track.file_path and os.path.exists(track.file_path):
        try:
            os.remove(track.file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not delete file: {e}")
            
    # 2. Mark as ignored instead of removing from DB — prevents re-download
    track.download_status = "ignored"
    track.file_path = None
    db.commit()
    
    return {"status": "success", "message": f"Track {track_id} ignored (won't be re-downloaded)"}

@router.put("/tracks/{track_id}/restore")
def restore_track(track_id: int, db: Session = Depends(get_db)):
    """Restore an ignored or failed track so it's queued for re-download"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    # 1. Reset status to pending
    track.download_status = "pending"
    db.commit()
    
    # 2. Clear from watcher's failed cache to bypass the 24h block list
    watcher = get_watcher()
    if watcher and track.youtube_id in watcher.failed_downloads:
        watcher.failed_downloads.pop(track.youtube_id, None)
    
    return {"status": "success", "message": f"Track {track_id} queued for re-download"}

# --- Config Routes ---

@router.get("/config/cookies")
def get_cookies_status():
    """Check if a custom cookies.txt is currently loaded"""
    # Use the mounted volume at /data if inside docker, fallback to local path otherwise
    base_dir = "/data" if os.path.exists("/data") else str(Path(__file__).parent.parent.parent.parent / "data")
    cookies_path = Path(base_dir) / "cookies.txt"
    exists = cookies_path.exists()
    return {"status": "success", "exists": exists}

@router.post("/config/cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """Upload a cookies.txt file and reload the watcher instance"""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are allowed")

    base_dir = "/data" if os.path.exists("/data") else str(Path(__file__).parent.parent.parent.parent / "data")
    cookies_path = Path(base_dir) / "cookies.txt"
    cookies_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the file
    try:
        content = await file.read()
        cookies_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save cookies: {str(e)}")
        
    # Reload watcher instance
    watcher = get_watcher()
    if watcher:
        watcher.update_cookies(str(cookies_path))
        
    return {"status": "success", "message": "Cookies uploaded and watcher reloaded."}

@router.delete("/config/cookies")
def delete_cookies():
    """Delete the custom cookies.txt file and reload the watcher instance"""
    base_dir = "/data" if os.path.exists("/data") else str(Path(__file__).parent.parent.parent.parent / "data")
    cookies_path = Path(base_dir) / "cookies.txt"
    
    if cookies_path.exists():
        try:
            cookies_path.unlink()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete cookies: {str(e)}")
            
    # Reload watcher instance removing cookies
    watcher = get_watcher()
    if watcher:
        watcher.update_cookies(None)
        
    return {"status": "success", "message": "Cookies deleted and watcher reloaded."}
