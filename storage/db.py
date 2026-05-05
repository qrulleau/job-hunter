import sqlite3
from datetime import datetime

DB_PATH = "job_hunter.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                company     TEXT,
                location    TEXT,
                contract    TEXT,
                source      TEXT,           -- 'france_travail', 'wttj', 'indeed'
                url         TEXT UNIQUE,    -- clé de déduplication
                description TEXT,
                status      TEXT DEFAULT 'new',  -- new | applied | ignored
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    print("✅ Base de données initialisée.")

def insert_job(title, company, location, contract, source, url, description=""):
    """Insère une offre. Retourne True si nouvelle, False si déjà connue."""
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (title, company, location, contract, source, url, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, company, location, contract, source, url, description))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # URL déjà en base = doublon

def get_new_jobs():
    """Retourne toutes les offres non traitées."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT id, title, company, location, source, url
            FROM jobs WHERE status = 'new'
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()

def mark_applied(job_id):
    with get_connection() as conn:
        conn.execute("UPDATE jobs SET status = 'applied' WHERE id = ?", (job_id,))
        conn.commit()

def mark_ignored(job_id):
    with get_connection() as conn:
        conn.execute("UPDATE jobs SET status = 'ignored' WHERE id = ?", (job_id,))
        conn.commit()

def get_job_by_id(job_id):
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        return cursor.fetchone()
