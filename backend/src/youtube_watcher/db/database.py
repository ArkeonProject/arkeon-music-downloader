from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pathlib import Path
import os

# Create a data directory in the project root if it doesn't exist
# This is where our SQLite DB will live
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Create the data directory if it doesn't exist
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except PermissionError:
    # Si estamos en Docker con un usuario mapeado y no se puede crear, asumimos
    # que docker-compose ya mapeó el volumen correctamente de todos modos.
    pass

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/watcher.db")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency for FastAPI to get a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
