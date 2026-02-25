import logging
import sqlite3
import yt_dlp
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MetadataBackfill")

DB_PATH = Path("/data/watcher.db") if Path("/data/watcher.db").exists() else Path("data/watcher.db")

def main():
    if not DB_PATH.exists():
        logger.error(f"Base de datos no encontrada en {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Obtener todas las canciones completadas para revisar si el artista está mal o falta fecha
    cursor.execute("SELECT id, youtube_id, title, artist, published_at FROM tracks")
    tracks = cursor.fetchall()
    
    if not tracks:
        logger.info("🎉 ¡No hay canciones en la base de datos!")
        return

    logger.info(f"🔎 Analizando metadatos de {len(tracks)} canciones en Youtube...")

    ydl_opts = {
        "extract_flat": False,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for idx, (db_id, y_id, title, current_artist, current_date) in enumerate(tracks, 1):
            url = f"https://www.youtube.com/watch?v={y_id}"
            try:
                info = ydl.extract_info(url, download=False)
                upload_date = info.get("upload_date")
                if upload_date and len(upload_date) == 8:
                    formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                elif upload_date:
                    formatted_date = upload_date
                else:
                    formatted_date = None
                
                # Fetch best possible artist
                yt_artist = (
                    info.get("artist")
                    or info.get("channel")
                    or info.get("uploader", "Unknown Artist")
                )

                # Verificamos si hay discrepancia de artista o fecha
                if current_artist != yt_artist or current_date != formatted_date:
                    cursor.execute(
                        "UPDATE tracks SET published_at=?, artist=? WHERE id=?", 
                        (formatted_date, yt_artist, db_id)
                    )
                    conn.commit()
                    logger.info(f"[{idx}/{len(tracks)}] ✅ DB Actualizada: '{title}' -> Artista: {yt_artist} | Fecha: {formatted_date}")
            except Exception as e:
                logger.error(f"[{idx}/{len(tracks)}] ❌ Error con '{title}': {e}")

    conn.close()
    logger.info("🚀 Proceso de 'backfill' (retro-relleno) finalizado.")

if __name__ == "__main__":
    main()
