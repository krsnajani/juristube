import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "juristube.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS videos (
        vid             TEXT PRIMARY KEY,
        url             TEXT NOT NULL,
        title           TEXT NOT NULL,
        channel         TEXT,
        summary         TEXT,
        duration_sec    INTEGER DEFAULT 0,
        upload_date     TEXT,
        content_type    TEXT,
        shelf_life      TEXT,
        score           REAL DEFAULT 0.0,
        ht_score        REAL DEFAULT 0.0,
        authority_tier  INTEGER DEFAULT 3,
        sources         TEXT,
        scholar_matches TEXT,
        blog_sources    TEXT,
        channel_source  TEXT,
        disciplines     TEXT,
        tags            TEXT,
        ht_categories   TEXT,
        watched         INTEGER DEFAULT 0,
        starred         INTEGER DEFAULT 0,
        notes           TEXT,
        duplicate_of    TEXT,
        title_normalized TEXT,
        has_subtitles   INTEGER DEFAULT 0,
        discovered_at   TEXT,
        updated_at      TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_score ON videos(score DESC);
    CREATE INDEX IF NOT EXISTS idx_watched ON videos(watched);
    CREATE INDEX IF NOT EXISTS idx_starred ON videos(starred);
    CREATE INDEX IF NOT EXISTS idx_duplicate ON videos(duplicate_of);

    CREATE TABLE IF NOT EXISTS scholars (
        name            TEXT PRIMARY KEY,
        discipline      TEXT,
        video_count     INTEGER DEFAULT 0,
        last_searched   TEXT
    );

    CREATE TABLE IF NOT EXISTS channels (
        channel_id      TEXT PRIMARY KEY,
        name            TEXT,
        tier            INTEGER DEFAULT 3,
        subjects        TEXT,
        last_scraped    TEXT
    );

    CREATE TABLE IF NOT EXISTS ingest_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp       TEXT,
        vector          TEXT,
        new_videos      INTEGER,
        skipped         INTEGER,
        errors          INTEGER,
        duration_sec    REAL
    );
    """)
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
