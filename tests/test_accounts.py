"""Getting in, getting back in, and not being let in.

The reset flow is the one place where a mistake hands someone else an account,
so most of this is about the link: that a weak password doesn't waste it, that
it works once, and that asking for one never reveals who has an account.
"""
import app.auth_token_service as tokens
from tests.conftest import SOFIA


def test_a_password_must_be_hard_enough(client):
    # The four rules the signup screen states: length, a capital, a number, a
    # symbol. Lowercase is deliberately not among them, so "NOLOWERCASE1!" is
    # a valid password and not a gap.
    for weak in ("short", "nocapitals1!", "NoNumbers!!", "NoSymbol123"):
        response = client.post("/signup", json={
            "name": "Test", "email": f"{weak}@example.com", "password": weak, **SOFIA,
        })
        assert response.status_code == 400, f"{weak!r} should have been refused"


def test_the_same_email_cannot_be_taken_twice(client, account):
    account(email="taken@example.com")
    again = client.post("/signup", json={
        "name": "Someone", "email": "taken@example.com", "password": "Moonlight9!", **SOFIA,
    })
    assert again.status_code == 400


def test_asking_for_a_reset_never_says_who_has_an_account(client, account):
    """Otherwise this is a way to find out who uses Zodi."""
    account(email="real@example.com")
    known = client.post("/forgot-password", json={"email": "real@example.com"})
    unknown = client.post("/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]


def test_a_weak_new_password_does_not_waste_the_link(client, account):
    """Fumbling the password should not strand someone with a spent link."""
    user, _ = account(email="reset@example.com")
    token = tokens.issue_token(user["id"], tokens.PURPOSE_RESET)

    assert client.post("/reset-password", json={"token": token, "password": "weak"}).status_code == 400
    assert client.post("/reset-password", json={"token": token, "password": "NewPass42!"}).status_code == 200


def test_a_reset_link_works_once(client, account):
    user, _ = account(email="once@example.com")
    token = tokens.issue_token(user["id"], tokens.PURPOSE_RESET)

    assert client.post("/reset-password", json={"token": token, "password": "NewPass42!"}).status_code == 200
    assert client.post("/reset-password", json={"token": token, "password": "Another99!"}).status_code == 400


def test_after_a_reset_the_old_password_is_dead(client, account):
    user, _ = account(email="rotate@example.com")
    token = tokens.issue_token(user["id"], tokens.PURPOSE_RESET)
    client.post("/reset-password", json={"token": token, "password": "NewPass42!"})

    assert client.post("/login", json={"email": "rotate@example.com", "password": "Moonlight9!"}).status_code == 401
    assert client.post("/login", json={"email": "rotate@example.com", "password": "NewPass42!"}).status_code == 200


def test_a_reset_signs_every_other_device_out(client, account):
    """A reset may mean the account was taken; a stolen session must not outlive it."""
    user, headers = account(email="sessions@example.com")
    assert client.get("/me", headers=headers).status_code == 200

    token = tokens.issue_token(user["id"], tokens.PURPOSE_RESET)
    client.post("/reset-password", json={"token": token, "password": "NewPass42!"})

    assert client.get("/me", headers=headers).status_code == 401


def test_a_verification_link_cannot_be_replayed_as_a_reset(client, account):
    """Different purposes, so the cheaper link can't stand in for the dangerous one."""
    user, _ = account(email="purpose@example.com")
    verify = tokens.issue_token(user["id"], tokens.PURPOSE_VERIFY)
    assert client.post("/reset-password", json={"token": verify, "password": "NewPass42!"}).status_code == 400


def test_a_new_account_starts_unverified_and_can_confirm(client, account):
    user, headers = account(email="confirm@example.com")
    assert user["email_verified"] is False

    token = tokens.issue_token(user["id"], tokens.PURPOSE_VERIFY)
    assert client.post("/verify-email", json={"token": token}).status_code == 200
    assert client.get("/me", headers=headers).json()["email_verified"] is True


def test_deleting_an_account_takes_everything_with_it(client, account):
    user, headers = account(email="gone@example.com")
    assert client.delete("/me", headers=headers).status_code == 200
    assert client.post("/login", json={"email": "gone@example.com", "password": "Moonlight9!"}).status_code == 401
