from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from ..db.database import get_db
from ..db.models import Source, Track

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
    file_path: str | None
    download_status: str
    downloaded_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True

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

@router.get("/tracks", response_model=List[TrackResponse])
def get_tracks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List downloaded and pending tracks"""
    tracks = db.query(Track).order_by(Track.created_at.desc()).offset(skip).limit(limit).all()
    return tracks

@router.post("/tracks/download-single")
def trigger_single_download(req: SingleDownloadRequest, db: Session = Depends(get_db)):
    """Queue a specific track for immediate download"""
    # Simply add it to DB as pending with a 'track' pseudo-source to be picked up
    # Let the watcher process it
    # TODO: Implement triggering immediate download vs enqueuing
    return {"status": "enqueued", "url": req.url}

@router.delete("/tracks/{track_id}")
def delete_track(track_id: int, db: Session = Depends(get_db)):
    """Delete a track physically and from DB"""
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    
    # 1. Physically delete or move to trash (We will need to delegate this to Watcher or duplicate logic)
    import os
    if track.file_path and os.path.exists(track.file_path):
        try:
            os.remove(track.file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not delete file: {e}")
            
    # 2. Remove from DB
    db.delete(track)
    db.commit()
    
    return {"status": "success", "message": f"Track {track_id} deleted"}
