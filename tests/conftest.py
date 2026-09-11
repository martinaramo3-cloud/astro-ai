"""Shared setup for the test suite.

Two rules make these worth having: they must be fast, and they must never touch
the network. Geocoding and every AI call are stubbed, so a run is deterministic
and works on a plane — which also means nothing here spends money.

The database path is set before anything from `app` is imported, because the
modules read it once at import time.
"""
import os
import tempfile

# Must come before any app import.
_TMP = tempfile.mkdtemp(prefix="zodi-tests-")
os.environ["DATABASE_PATH"] = os.path.join(_TMP, "test.db")
os.environ.setdefault("ADMIN_SECRET", "test-admin-secret")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402
from app.database import get_db_connection, init_db  # noqa: E402

TABLES = (
    "chat_sessions", "attachments", "usage_events", "error_events",
    "invites", "auth_tokens", "sessions", "profiles", "users",
)

# Real coordinates, so the charts these produce are genuine — just fetched
# without asking anyone's server.
PLACES = {
    "sofia, bulgaria": {"latitude": 42.6977, "longitude": 23.3219,
                        "timezone": "Europe/Sofia", "display_name": "Sofia, Bulgaria"},
    "milan, italy": {"latitude": 45.4642, "longitude": 9.1900,
                     "timezone": "Europe/Rome", "display_name": "Milan, Italy"},
}

SOFIA = {"birth_date": "1999-03-02", "birth_time": "07:15", "birth_place": "Sofia, Bulgaria"}
MILAN = {"birth_date": "1997-11-08", "birth_time": "14:30", "birth_place": "Milan, Italy"}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No network, no spend, no surprises."""
    def fake_place(name):
        return PLACES.get((name or "").strip().lower())

    for module in ("app.main", "app.location_service"):
        monkeypatch.setattr(f"{module}.get_location_data", fake_place, raising=False)

    # Any model call returns something harmless and free.
    monkeypatch.setattr(main, "generate_astrologer_answer",
                        lambda prompt, **kw: ("A test answer.", 100), raising=False)
    monkeypatch.setattr(main, "classify_answer_tier", lambda q, recent="": 4, raising=False)
    monkeypatch.setattr(main, "extract_asked_date", lambda q: None, raising=False)
    monkeypatch.setattr(main, "send_password_reset", lambda *a, **k: True, raising=False)
    monkeypatch.setattr(main, "send_verification", lambda *a, **k: True, raising=False)


@pytest.fixture(autouse=True)
def clean_db():
    """A fresh database for every test, so order can never matter."""
    init_db()
    conn = get_db_connection()
    for table in TABLES:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
    yield


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def account(client):
    """A signed-up user, with the headers to act as them."""
    def make(email="her@example.com", **overrides):
        payload = {"name": "Martina", "email": email, "password": "Moonlight9!", **SOFIA}
        payload.update(overrides)
        user = client.post("/signup", json=payload).json()
        return user, {"Authorization": f"Bearer {user['token']}"}
    return make


@pytest.fixture
def admin():
    return {"x-admin-secret": os.environ["ADMIN_SECRET"]}
