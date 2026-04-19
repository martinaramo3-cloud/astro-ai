import sqlite3
import os

DB_NAME = os.getenv("DATABASE_PATH", "astrology.db")


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


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
        birth_place TEXT NOT NULL
    )
    """)

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
    conn.commit()
    conn.close()
