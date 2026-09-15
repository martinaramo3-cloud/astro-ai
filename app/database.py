import sqlite3
import os

DB_NAME = os.getenv("DATABASE_PATH", "astrology.db")


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _add_missing_columns(cursor, table: str, migrations: dict[str, str]) -> None:
    """Apply ALTERs for columns this table doesn't have yet. Safe to re-run."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    for column, statement in migrations.items():
        if column not in existing:
            cursor.execute(statement)


def _ensure_user_columns(cursor):
    _add_missing_columns(cursor, "users", {
        "subscription_tier": "ALTER TABLE users ADD COLUMN subscription_tier TEXT NOT NULL DEFAULT 'free'",
        "daily_usage_count": "ALTER TABLE users ADD COLUMN daily_usage_count INTEGER NOT NULL DEFAULT 0",
        "daily_usage_date": "ALTER TABLE users ADD COLUMN daily_usage_date TEXT",
        # Most people don't know their birth time. Without it there is no
        # Ascendant, no houses and no reliable Moon degree — so the reading has
        # to know to leave those out rather than invent them. Existing rows
        # default to 1: they were required to supply a time.
        "birth_time_known": "ALTER TABLE users ADD COLUMN birth_time_known INTEGER NOT NULL DEFAULT 1",
        # 1 once the person has clicked the link in their verification email.
        # Existing accounts default to 1 — they predate verification and
        # shouldn't be retroactively told to verify.
        "email_verified": "ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 1",
    })


def _ensure_profile_columns(cursor):
    _add_missing_columns(cursor, "profiles", {
        "birth_time_known": "ALTER TABLE profiles ADD COLUMN birth_time_known INTEGER NOT NULL DEFAULT 1",
    })


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
        birth_time_known INTEGER NOT NULL DEFAULT 1,
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
        birth_time_known INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_user_id) REFERENCES users(id)
)
""")

    _ensure_profile_columns(cursor)

    # Login sessions. Only a hash of each token is stored, so a copy of the
    # database can't be used to impersonate anyone.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)"
    )

    # Single-use links sent by email: a password reset or an email
    # verification. Only the hash of each token is stored, so a leaked database
    # can't be used to reset anyone's password. `purpose` keeps the two kinds
    # apart so a verification link can't be replayed as a reset.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auth_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        purpose TEXT NOT NULL,
        token_hash TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used_at TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_auth_tokens_hash ON auth_tokens(token_hash)"
    )

    # A link asking someone for their birth details. Only the hash is kept, so
    # the database is not a list of working invitations.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_hash TEXT NOT NULL,
        owner_user_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        person_name TEXT,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used_at TEXT,
        FOREIGN KEY (owner_user_id) REFERENCES users(id)
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_invites_hash ON invites(token_hash)"
    )

    # What someone tells us is wrong, in their words. The error log catches
    # what crashes; this catches what is merely broken — an answer that made no
    # sense, a button that did nothing, a chart that looks wrong. Neither one
    # finds the other's bugs.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bug_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        email TEXT,
        message TEXT NOT NULL,
        page TEXT,
        user_agent TEXT,
        resolved INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_bug_reports_created ON bug_reports(created_at)"
    )

    # One row per unhandled failure, so "is it working" has an answer that
    # doesn't depend on someone complaining.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS error_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL,
        method TEXT,
        kind TEXT,
        message TEXT,
        traceback TEXT,
        user_id INTEGER,
        status_code INTEGER,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_error_events_created ON error_events(created_at)"
    )

    # One row per AI call. This is how spend is tracked per user and per model
    # — the provider dashboards only ever show the whole bill blended together.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usage_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        model_key TEXT,
        model_id TEXT NOT NULL,
        tokens_in INTEGER NOT NULL DEFAULT 0,
        tokens_out INTEGER NOT NULL DEFAULT 0,
        cost_usd REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_events(user_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_events(created_at)"
    )

    # Images attached to a question. The file lives on disk beside this
    # database; only the pointer is stored here.
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_user_id INTEGER NOT NULL,
        stored_name TEXT NOT NULL,
        content_type TEXT NOT NULL,
        byte_size INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (owner_user_id) REFERENCES users(id)
    )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_attachments_owner ON attachments(owner_user_id)"
    )

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
