"""How close an aspect has to be to count, and how much closer counts for more.

Written to the co-founder's instruction: "Set and document an orb policy; do
not quietly treat an 8° conjunction as equivalent to a 1° conjunction."

IN USE on career and money questions since 25 September 2026. The astrologer
has seen these numbers at the top of the blind table but has not signed them
off in writing, so they stay in one named file: changing them is one edit
rather than a search through the codebase.

------------------------------------------------------------------------------
The policy, in words
------------------------------------------------------------------------------
Three things decide the allowance: which aspect it is, what is being aspected,
and whether a luminary is involved.

  By aspect. A conjunction or opposition is the loudest and gets the widest
  allowance; a square or trine slightly less; a sextile least, because a wide
  sextile is the aspect most likely to be noise.

  By what is aspected. The angles are directions rather than bodies, so they
  take a tighter allowance than two planets do. A house cusp that is not an
  angle — the 2nd, which the weight table needs — is tighter still.

  By luminary. The Sun and the Moon carry more light than the rest, so an
  aspect involving one gets two extra degrees. This is the conventional
  moiety idea, kept simple: the widest party sets the allowance.

Exactness then becomes a weight, not a threshold. A contact at a tenth of its
allowance counts nearly double one at four fifths of it. The weight never
reaches zero inside the allowance — an aspect that qualifies is real — and it
never exceeds 1, so the co-founder's point values stay the ceiling they were
written to be.

------------------------------------------------------------------------------
What this does NOT change
------------------------------------------------------------------------------
The existing six-degree rule in `aspect_services.get_aspects` still governs
which aspects the rest of the app sees. This policy governs the career and
money engines only, so approving it cannot quietly alter every other reading
in the product.
"""
from __future__ import annotations

LUMINARIES = {"Sun", "Moon"}
ANGLES = {"Ascendant", "Midheaven", "Descendant", "Imum Coeli"}

# Maximum orb, in degrees, between two planets.
BY_ASPECT = {
    "conjunction": 8.0,
    "opposition": 8.0,
    "square": 7.0,
    "trine": 7.0,
    "sextile": 5.0,
}
# The same aspects to an angle, which is a direction and not a body.
TO_ANGLE = {
    "conjunction": 6.0,
    "opposition": 6.0,
    "square": 5.0,
    "trine": 5.0,
    "sextile": 3.0,
}
# A house cusp that is not an angle. Only conjunctions are read here.
TO_CUSP = 3.0
# A luminary widens whichever allowance applies.
LUMINARY_BONUS = 2.0
# An aspect inside its allowance is real, so its weight never falls to nothing.
FLOOR = 0.2

POLICY_NOTE = (
    "Orbs: 8° for a conjunction or opposition between planets, 7° for a square "
    "or trine, 5° for a sextile; 6/5/3° to an angle; 3° to the 2nd cusp. Two "
    "degrees wider when the Sun or Moon is involved. Exactness is then a "
    "weight from 0.2 to 1.0, so a 1° contact counts for roughly four times a "
    "contact at the edge of its allowance. In use on career questions; not yet "
    "signed off in writing."
)


def max_orb(aspect: str, point_a: str, point_b: str) -> float:
    """The widest this aspect may be and still count, for these two points."""
    if point_a in ANGLES or point_b in ANGLES:
        allowance = TO_ANGLE.get(aspect, 0.0)
    else:
        allowance = BY_ASPECT.get(aspect, 0.0)
    if allowance and (point_a in LUMINARIES or point_b in LUMINARIES):
        allowance += LUMINARY_BONUS
    return allowance


def within_orb(aspect: str, orb: float, point_a: str, point_b: str) -> bool:
    allowance = max_orb(aspect, point_a, point_b)
    return bool(allowance) and orb <= allowance


def exactness(aspect: str, orb: float, point_a: str, point_b: str) -> float:
    """How much this contact counts, from FLOOR to 1.0.

    Linear rather than curved, on purpose: it has to be explainable to the
    person whose chart it is, and "half the allowance, a bit over half the
    weight" is explainable.
    """
    allowance = max_orb(aspect, point_a, point_b)
    if not allowance:
        return 0.0
    if orb >= allowance:
        return FLOOR
    return round(FLOOR + (1.0 - FLOOR) * (1.0 - orb / allowance), 3)


def describe() -> dict:
    """The policy as data, so an audit can record which one was in force."""
    return {
        "between_planets": dict(BY_ASPECT),
        "to_an_angle": dict(TO_ANGLE),
        "to_the_second_cusp": TO_CUSP,
        "luminary_bonus": LUMINARY_BONUS,
        "exactness_floor": FLOOR,
        "status": "in use; seen by the astrologer, not yet signed off in writing",
        "note": POLICY_NOTE,
    }
