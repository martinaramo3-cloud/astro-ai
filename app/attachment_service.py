"""Images people attach to a question — a chart from another app, a screenshot
of a conversation.

These are the most sensitive things the app holds: a screenshot of someone's
messages contains a third party's words, given without that person's knowledge.
So the rules here are deliberately tight — owner-scoped paths, an allowlist of
types, a size ceiling, and deletion that takes the file with the row.
"""
from __future__ import annotations

import os
import io
import warnings
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException
import secrets
from datetime import datetime, timezone
from pathlib import Path

from app.database import DB_NAME, get_db_connection

# Only formats every vision model accepts. No SVG: it can carry script, and
# nothing that reaches a browser should be able to.
ALLOWED_TYPES: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

# A phone screenshot is well under 2MB; this leaves room for a photo of a
# printed chart without letting anyone fill the disk.
MAX_BYTES = 8 * 1024 * 1024

# One question, a couple of pictures. More than this is a different feature.
MAX_PER_MESSAGE = 3


def uploads_root() -> Path:
    """Alongside the database, so it lands on Render's persistent disk too.

    `DATABASE_PATH` is `/var/data/astrology.db` in production and a bare
    filename in development, hence the fallback to the working directory.
    """
    parent = Path(DB_NAME).parent
    root = (parent if str(parent) not in ("", ".") else Path.cwd()) / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path_for(owner_user_id: int, stored_name: str) -> Path:
    return uploads_root() / str(owner_user_id) / stored_name


def save_attachment(owner_user_id: int, content: bytes, content_type: str) -> dict:
    """Write one image to disk and record it. Caller validates the tier."""
    formats = {"image/png":"PNG", "image/jpeg":"JPEG", "image/webp":"WEBP", "image/gif":"GIF"}
    if not content or len(content) > MAX_BYTES or content_type not in formats:
        raise HTTPException(400, "Please send a supported image under 8 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                frames = getattr(image, "n_frames", 1)
                if image.format != formats[content_type] or image.width * image.height * frames > 40_000_000 or frames > 50:
                    raise ValueError("Invalid image format or dimensions")
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                for frame in range(frames):
                    image.seek(frame)
                    image.load()
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(400, "That image is invalid or too large to process. Please send a smaller image.")

    stored_name = f"{secrets.token_urlsafe(16)}{ALLOWED_TYPES[content_type]}"
    path = _path_for(owner_user_id, stored_name)
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT id FROM users WHERE id=?", (owner_user_id,)).fetchone():
            raise HTTPException(401, "Please log in again.")
        owned = conn.execute("SELECT COALESCE(SUM(byte_size),0) FROM attachments WHERE owner_user_id=?", (owner_user_id,)).fetchone()[0]
        total = conn.execute("SELECT COALESCE(SUM(byte_size),0) FROM attachments").fetchone()[0]
        if owned + len(content) > 50 * 1024 * 1024 or total + len(content) > 400 * 1024 * 1024:
            raise HTTPException(413, "Image storage is full. Please delete older attachments first.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        cursor = conn.execute("""INSERT INTO attachments
            (owner_user_id, stored_name, content_type, byte_size, created_at)
            VALUES (?, ?, ?, ?, ?)""", (owner_user_id,stored_name,content_type,len(content),datetime.now(timezone.utc).isoformat()))
        attachment_id = cursor.lastrowid
        conn.commit()
    except Exception:
        conn.rollback()
        path.unlink(missing_ok=True)
        raise
    finally:
        conn.close()
    return {"id":attachment_id,"content_type":content_type,"byte_size":len(content)}


def get_attachment(attachment_id: int) -> dict | None:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM attachments WHERE id = ?", (attachment_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def read_attachment_bytes(attachment: dict) -> bytes | None:
    """The file itself, or None if it has gone missing from disk.

    A missing file is survivable — the answer it belonged to is already in the
    transcript — so callers degrade rather than fail.
    """
    path = _path_for(attachment["owner_user_id"], attachment["stored_name"])
    try:
        return path.read_bytes()
    except OSError:
        return None


def load_owned_attachments(attachment_ids: list[int], owner_user_id: int) -> list[dict]:
    """Fetch these attachments, keeping only the ones this person owns.

    Ownership is re-checked here rather than trusted from the request, so a
    guessed id can't pull someone else's screenshot into an answer.
    """
    loaded = []
    for attachment_id in attachment_ids[:MAX_PER_MESSAGE]:
        attachment = get_attachment(attachment_id)
        if not attachment or attachment["owner_user_id"] != owner_user_id:
            continue
        content = read_attachment_bytes(attachment)
        if content is None:
            continue
        loaded.append({**attachment, "content": content})
    return loaded


def delete_attachment(attachment_id: int, owner_user_id: int) -> bool:
    attachment = get_attachment(attachment_id)
    if not attachment or attachment["owner_user_id"] != owner_user_id:
        return False

    _remove_file(owner_user_id, attachment["stored_name"])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
    conn.commit()
    conn.close()
    return True


def _remove_file(owner_user_id: int, stored_name: str) -> None:
    try:
        _path_for(owner_user_id, stored_name).unlink()
    except OSError:
        # Already gone, or never written. The row still needs to go.
        pass


def delete_attachments_for_user(user_id: int) -> int:
    """Erase every image this person uploaded, files included.

    Deleting an account has to take the pictures with it, or "erases
    everything" in the privacy policy is not true.
    """
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT stored_name FROM attachments WHERE owner_user_id = ?", (user_id,)
    ).fetchall()

    for row in rows:
        _remove_file(user_id, row["stored_name"])

    conn.execute("DELETE FROM attachments WHERE owner_user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    # Tidy the now-empty per-user folder; harmless if it isn't empty.
    try:
        os.rmdir(uploads_root() / str(user_id))
    except OSError:
        pass

    return len(rows)
