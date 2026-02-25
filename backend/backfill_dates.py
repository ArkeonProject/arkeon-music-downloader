import logging
import sqlite3
import yt_dlp
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DateBackfill")

DB_PATH = Path("data/arkeon.db")

def main():
    if not DB_PATH.exists():
        logger.error(f"Base de datos no encontrada en {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Obtener todas las canciones completadas que no tienen fecha de publicación
    cursor.execute("SELECT id, youtube_id, title FROM tracks WHERE download_status='completed' AND (published_at IS NULL OR published_at = '')")
    tracks = cursor.fetchall()
    
    if not tracks:
        logger.info("🎉 ¡No hay canciones pendientes de revisar! Todas tienen fecha.")
        return

    logger.info(f"🔎 Encontradas {len(tracks)} canciones antiguas sin fecha de Salida Oficial.")
    logger.info("Comenzando el proceso de recuperación desde YouTube...")

    ydl_opts = {
        "extract_flat": False, # necesitamos la info completa
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for idx, (db_id, y_id, title) in enumerate(tracks, 1):
            url = f"https://www.youtube.com/watch?v={y_id}"
            try:
                info = ydl.extract_info(url, download=False)
                upload_date = info.get("upload_date")
                
                if upload_date and len(upload_date) >= 4:
                    year = upload_date[:4]
                    cursor.execute("UPDATE tracks SET published_at=? WHERE id=?", (year, db_id))
                    conn.commit()
                    logger.info(f"[{idx}/{len(tracks)}] ✅ Actualizada: '{title}' -> Año {year}")
                else:
                    # Rellenar con 'Desconocido' para no volver a intentarlo indefinidamente
                    cursor.execute("UPDATE tracks SET published_at='—' WHERE id=?", (db_id,))
                    conn.commit()
                    logger.info(f"[{idx}/{len(tracks)}] ⚠️ Sin fecha en YouTube: '{title}'")
                    
            except Exception as e:
                logger.error(f"[{idx}/{len(tracks)}] ❌ Error con '{title}': {e}")

    conn.close()
    logger.info("🚀 Proceso de 'backfill' (retro-relleno) finalizado.")

if __name__ == "__main__":
    main()
