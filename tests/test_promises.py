"""What the app promises never to invent.

Most people don't know what time they were born. Without it the Ascendant, the
houses and the angles are not approximate — they are unknowable, because they
rotate a full circle every day. Guessing one is the single fastest way to lose
someone's trust, since they will recognise a rising sign that isn't theirs.

These are the promises, written down so they can't be broken by accident.
"""
from tests.conftest import SOFIA

import app.main as main


class NoTime:
    birth_date = "1999-03-02"
    birth_time = "12:00"
    birth_place = "Sofia, Bulgaria"
    birth_time_known = False


class WithTime(NoTime):
    birth_time = "07:15"
    birth_time_known = True


def test_no_birth_time_means_no_ascendant_or_houses():
    chart = main.build_natal_chart_data(NoTime())
    assert chart["ascendant"] is None
    assert chart["houses"] == []


def test_no_birth_time_means_no_angles_to_transit():
    """An angle without a birth time would be a transit to a guess."""
    assert main.build_natal_chart_data(NoTime())["angles"] == []
    assert main.build_natal_chart_data(NoTime())["midheaven"] is None


def test_no_birth_time_leaves_every_planet_without_a_house():
    chart = main.build_natal_chart_data(NoTime())
    assert all(p["house"] is None for p in chart["planet_positions"])


def test_the_planets_still_work_without_a_time():
    """Signs, aspects and transits need no birth time — only the houses do.
    Withholding them too would be over-caution, and it is most of the reading."""
    chart = main.build_natal_chart_data(NoTime())
    assert len(chart["planet_positions"]) >= 11
    assert chart["aspects"], "aspects between planets do not depend on the time"


def test_with_a_time_everything_is_present():
    chart = main.build_natal_chart_data(WithTime())
    assert chart["ascendant"]["sign"] == "Pisces"
    assert chart["midheaven"]["sign"] == "Sagittarius"
    assert len(chart["houses"]) == 12
    assert all(p["house"] is not None for p in chart["planet_positions"])


def test_a_stale_client_cannot_reintroduce_a_fake_rising_sign(client, account):
    """The saved account is the authority when the request doesn't say."""
    user, headers = account(email="unknown-time@example.com", birth_time_known=False)
    assert user["birth_time_known"] is False

    response = client.post(
        "/ask-astrologer",
        json={**SOFIA, "question": "what is my rising sign", "history": [],
              "user_id": user["id"]},          # deliberately omits birth_time_known
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["context"]["birth_time_known"] is False
