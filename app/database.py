import sqlite3
import os

DB_NAME = os.getenv("DATABASE_PATH", "astrology.db")


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_user_columns(cursor):
    """Add subscription columns to existing users tables (safe to run repeatedly)."""
    cursor.execute("PRAGMA table_info(users)")
    existing = {row[1] for row in cursor.fetchall()}

    migrations = {
        "subscription_tier": "ALTER TABLE users ADD COLUMN subscription_tier TEXT NOT NULL DEFAULT 'free'",
        "daily_usage_count": "ALTER TABLE users ADD COLUMN daily_usage_count INTEGER NOT NULL DEFAULT 0",
        "daily_usage_date": "ALTER TABLE users ADD COLUMN daily_usage_date TEXT",
    }

    for column, statement in migrations.items():
        if column not in existing:
            cursor.execute(statement)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        birth_date TEXT NOT NULL,
        birth_time TEXT NOT NULL,
        birth_place TEXT NOT NULL,
        subscription_tier TEXT NOT NULL DEFAULT 'free',
        daily_usage_count INTEGER NOT NULL DEFAULT 0,
        daily_usage_date TEXT
    )
    """)

    _ensure_user_columns(cursor)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_user_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        person_name TEXT NOT NULL,
        relationship_type TEXT,
        birth_date TEXT NOT NULL,
        birth_time TEXT NOT NULL,
        birth_place TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_user_id) REFERENCES users(id)
)
""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_user_id INTEGER NOT NULL,
        profile_id INTEGER,
        title TEXT NOT NULL,
        messages_json TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_user_id) REFERENCES users(id),
        FOREIGN KEY (profile_id) REFERENCES profiles(id)
    )
    """)
    conn.commit()
    conn.close()
