"""The things that must refuse.

Every one of these has a cost when it stops working: a free account that saves
unlimited people costs real money, an invite link that can be reused is a way
into someone's account list, a reset link that works twice is a way into their
account, and an admin endpoint without its secret is everything at once.
"""
from tests.conftest import MILAN, SOFIA

import app.invite_service as invites


# ── Saved people ───────────────────────────────────────────────────────────

def test_free_tier_saves_one_person_then_refuses(client, account):
    user, headers = account()
    first = client.post("/profiles", json={
        "owner_user_id": user["id"], "label": "Him", "person_name": "Luca", **MILAN,
    }, headers=headers)
    assert first.status_code == 200

    second = client.post("/profiles", json={
        "owner_user_id": user["id"], "label": "Her", "person_name": "Ana", **MILAN,
    }, headers=headers)
    assert second.status_code == 402
    assert "upgrade" in second.json()["detail"].lower()


# ── Invitations ────────────────────────────────────────────────────────────

def test_an_invite_can_be_filled_in_once(client, account):
    user, headers = account()
    token = client.post("/invites", json={"label": "Him"}, headers=headers).json()["token"]

    assert client.get(f"/invite/{token}").json()["from_name"] == "Martina"

    filled = client.post(f"/invite/{token}", json={"person_name": "Luca", **MILAN})
    assert filled.status_code == 200

    # Spent: neither readable nor fillable again.
    assert client.get(f"/invite/{token}").status_code == 404
    assert client.post(f"/invite/{token}", json={"person_name": "Someone", **MILAN}).status_code == 404


def test_a_filled_invite_becomes_a_saved_person(client, account):
    user, headers = account()
    token = client.post("/invites", json={"label": "Him"}, headers=headers).json()["token"]
    client.post(f"/invite/{token}", json={"person_name": "Luca", **MILAN})

    people = client.get(f"/profiles/{user['id']}", headers=headers).json()
    assert [(p["label"], p["person_name"]) for p in people] == [("Him", "Luca")]


def test_an_unknown_invite_is_refused(client):
    assert client.get("/invite/not-a-real-token").status_code == 404


def test_an_expired_invite_is_refused(client, account, monkeypatch):
    user, headers = account()
    monkeypatch.setattr(invites, "TTL_DAYS", -1)    # issued already expired
    token = invites.create_invite(user["id"], "Him")
    assert client.get(f"/invite/{token}").status_code == 404


def test_an_invite_only_shows_a_first_name(client, account):
    """The person opening it is a stranger; they get no more than they need."""
    user, headers = account(email="private@example.com")
    token = client.post("/invites", json={"label": "Him"}, headers=headers).json()["token"]
    body = client.get(f"/invite/{token}").json()
    assert body["from_name"] == "Martina"
    assert "private@example.com" not in str(body)


def test_the_invite_respects_the_people_limit(client, account):
    """Better to refuse the link than to refuse someone after they've typed."""
    user, headers = account()
    client.post("/profiles", json={
        "owner_user_id": user["id"], "label": "Him", "person_name": "Luca", **MILAN,
    }, headers=headers)
    assert client.post("/invites", json={"label": "Another"}, headers=headers).status_code == 402


# ── Admin ──────────────────────────────────────────────────────────────────

def test_admin_endpoints_need_the_secret(client, admin):
    for path in ("/admin/usage", "/admin/errors", "/admin/backups"):
        assert client.get(path).status_code == 401, path
        assert client.get(path, headers=admin).status_code == 200, path


def test_a_backup_cannot_be_used_to_read_other_files(client, admin):
    assert client.get("/admin/backups/../../etc/passwd", headers=admin).status_code in (404, 400)


# ── Someone else's things ──────────────────────────────────────────────────

def test_one_account_cannot_read_another_persons_people(client, account):
    her, her_headers = account(email="her@example.com")
    client.post("/profiles", json={
        "owner_user_id": her["id"], "label": "Him", "person_name": "Luca", **MILAN,
    }, headers=her_headers)

    them, them_headers = account(email="them@example.com")
    seen = client.get(f"/profiles/{her['id']}", headers=them_headers)
    assert seen.status_code in (401, 403) or seen.json() == []
