from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

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
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
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


def _sqlite_column_exists(conn, table_name: str, column_name: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(row[1] == column_name for row in rows)


def _sqlite_index_exists(conn, index_name: str) -> bool:
    rows = conn.execute(text("PRAGMA index_list(tracks)")).fetchall()
    source_rows = conn.execute(text("PRAGMA index_list(sources)")).fetchall()
    return any(row[1] == index_name for row in [*rows, *source_rows])


def ensure_database_schema() -> None:
    """Create tables and run lightweight SQLite-safe migrations.

    The project currently has no Alembic migration stack. Keep this helper
    idempotent so existing Docker volumes can be upgraded on startup without
    dropping data.
    """
    # Import models lazily so metadata is populated without circular imports.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    if not DATABASE_URL.startswith("sqlite"):
        return

    column_migrations = {
        "tracks": {
            "published_at": "VARCHAR",
            "artist": "VARCHAR",
            "navidrome_song_id": "VARCHAR",
            "navidrome_synced_at": "DATETIME",
            "navidrome_sync_status": "VARCHAR",
            "navidrome_sync_error": "VARCHAR",
            "navidrome_sync_attempted_at": "DATETIME",
        },
        "sources": {
            "navidrome_playlist_id": "VARCHAR",
        },
    }

    with engine.begin() as conn:
        for table, columns in column_migrations.items():
            for column, ddl_type in columns.items():
                if not _sqlite_column_exists(conn, table, column):
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
                    )
                    logger.info("Added SQLite column %s.%s", table, column)

        index_statements = {
            "ix_tracks_source_status": "CREATE INDEX ix_tracks_source_status ON tracks (source_id, download_status)",
            "ix_tracks_navidrome_sync_status": "CREATE INDEX ix_tracks_navidrome_sync_status ON tracks (navidrome_sync_status)",
            "ix_sources_status": "CREATE INDEX ix_sources_status ON sources (status)",
        }
        for index_name, statement in index_statements.items():
            if not _sqlite_index_exists(conn, index_name):
                conn.execute(text(statement))
                logger.info("Created SQLite index %s", index_name)
