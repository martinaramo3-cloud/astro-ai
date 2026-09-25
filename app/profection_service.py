"""Annual profections: which house this year of someone's life belongs to.

The career data audit found this scaffolded and never built. The prediction
engine already raises the weight of a transit that lands on the profected
house, and already knows what to do with a time lord — and both were dead,
because nothing anywhere worked the profected house out from a birth date. The
boost had never once applied to a real person.

The rule, from the co-founder: count from age at the LAST birthday. Age 0 is
the 1st house, age 1 the 2nd, and it repeats every twelve years. The ruler of
the sign on that house is the year's time lord.

Her caution, kept in the output so it cannot be dropped: a profection is
context for a transit, not an event. A 10th-house year says where the year's
attention sits. It does not say that anything will happen.
"""
from __future__ import annotations

from datetime import date

from app.content_repository import get_sign_rulers


def age_at_last_birthday(birth_date: str, on: date | None = None) -> int | None:
    """Whole years lived. The number profections are counted from."""
    on = on or date.today()
    try:
        year, month, day = (int(part) for part in str(birth_date)[:10].split("-"))
        born = date(year, month, day)
    except (TypeError, ValueError):
        return None
    if born > on:
        return None
    had_birthday = (on.month, on.day) >= (born.month, born.day)
    return on.year - born.year - (0 if had_birthday else 1)


def profected_house(age: int) -> int:
    """Age 0 is the 1st house, age 1 the 2nd, repeating every twelve years."""
    return (age % 12) + 1


def annual_profection(birth_date: str, houses: list | None,
                      on: date | None = None) -> dict:
    """The active house for this year of life, and the planet that rules it.

    Needs houses, so it needs a birth time. Without one this returns
    unavailable rather than a guess — the same rule as everything else that
    rests on the Ascendant.
    """
    age = age_at_last_birthday(birth_date, on)
    if age is None:
        return {"available": False, "reason": "no usable birth date"}
    if not houses or len(houses) != 12:
        return {"available": False, "age": age,
                "reason": "profections are counted from the Ascendant, so they "
                          "need a birth time"}

    house = profected_house(age)
    cusp = next((h for h in houses if h.get("house") == house), None)
    sign = cusp.get("sign") if cusp else None
    rulers = get_sign_rulers().get(sign or "", [])
    time_lord = rulers[0] if rulers else None

    return {
        "available": True,
        "age_at_last_birthday": age,
        "profected_house": house,
        "sign_on_that_house": sign,
        "time_lord": time_lord,
        "counted_from": "age at the last birthday; age 0 is the 1st house",
        # Hers, and it travels with the number so it cannot be left behind.
        "how_to_use_it": (
            "Context for a transit, not an event. A profected house says where "
            "this year of life has its attention; it does not establish that "
            "anything will happen. A transit that lands on this house or "
            "involves this year's ruler matters more than one that does not."
        ),
    }
