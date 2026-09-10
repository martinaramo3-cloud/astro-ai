"""Nightly, consistent copies of the database.

Render already snapshots the disk every 24 hours and keeps them about a week,
which covers the disk itself failing. Three gaps that leaves, and this fills
them:

  * A disk snapshot copies the database file mid-write. Render's own docs say
    not to rely on that for a database, because the copy can be a corrupted
    state. `VACUUM INTO` asks SQLite for a clean copy instead, so what lands is
    always a database that opens.
  * Seven days is short. A bad migration noticed three weeks later is not
    recoverable from a week of snapshots.
  * Restoring a disk snapshot rolls the whole disk back and loses everything
    after it. A file you can download is a copy you can inspect and pick from.

Kept beside the database on the persistent disk. That is deliberately not
off-site — for that, download one and keep it somewhere else, which is what
/admin/backups is for.
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.database import DB_NAME

KEEP_DAYS = 30
BACKUP_INTERVAL_SECONDS = 24 * 60 * 60
# The disk is 1GB and the database is small, but a runaway loop shouldn't be
# able to fill it and take the app down with it.
MAX_TOTAL_BYTES = 300 * 1024 * 1024


def backup_dir() -> Path:
    directory = Path(DB_NAME).resolve().parent / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def list_backups() -> list[dict]:
    """Newest first, with sizes, for the admin page."""
    entries = []
    for path in sorted(backup_dir().glob("zodi-*.db"), reverse=True):
        stat = path.stat()
        entries.append({
            "name": path.name,
            "bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        })
    return entries


def create_backup() -> dict:
    """Write one consistent copy of the database, then prune old ones."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target = backup_dir() / f"zodi-{stamp}.db"

    # VACUUM INTO takes a read lock and writes a complete, defragmented copy,
    # so the result is never a half-written page. Rewriting today's file is
    # intentional: one backup per day, the latest wins.
    if target.exists():
        target.unlink()

    source = sqlite3.connect(DB_NAME)
    try:
        source.execute("VACUUM INTO ?", (str(target),))
    finally:
        source.close()

    pruned = _prune()
    return {
        "name": target.name,
        "bytes": target.stat().st_size,
        "pruned": pruned,
        "kept": len(list_backups()),
    }


def _prune() -> int:
    """Drop anything past the retention window, and anything over the size cap."""
    backups = sorted(backup_dir().glob("zodi-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0

    for path in backups[KEEP_DAYS:]:
        path.unlink(missing_ok=True)
        removed += 1

    total = 0
    for path in sorted(backup_dir().glob("zodi-*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        total += path.stat().st_size
        if total > MAX_TOTAL_BYTES:
            path.unlink(missing_ok=True)
            removed += 1

    return removed


async def run_backup_loop() -> None:
    """Take one on boot, then once a day.

    Deploys restart the service, so the boot backup also means every deploy is
    preceded by a clean copy — which is exactly when a migration is most likely
    to go wrong.
    """
    while True:
        try:
            result = await asyncio.to_thread(create_backup)
            print(f"[backup] wrote {result['name']} ({result['bytes']} bytes), keeping {result['kept']}")
        except Exception as exc:  # noqa: BLE001 — a failed backup must never stop the app
            print("[backup] failed:", repr(exc))
        await asyncio.sleep(BACKUP_INTERVAL_SECONDS)
