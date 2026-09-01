"""Work out what an attached picture actually is, before answering about it.

The point of this pass is the birth chart case. Vision models read a chart
wheel badly — the glyphs are small, the degree numbers smaller — and will
state a confident wrong placement rather than admit the pixels were ambiguous.
But most astrology apps print the birth data on the chart in plain text, and
text is something a vision model reads reliably.

So: read the date, time and place, then cast the chart here with the real
ephemeris. The answer is then based on arithmetic instead of eyesight, and the
expensive model never has to look at the picture at all.

When the birth data isn't legible, the image is passed through to be described
with an explicit warning attached — accurate about its own uncertainty, which
is the next best thing to being right.
"""
from __future__ import annotations

import json
import re

from app.ai_service import inspect_images

INSPECTION_PROMPT = """
You are examining one or more images a user attached to a question for an astrologer.

Reply with JSON only — no prose, no code fences. Use exactly this shape:

{
  "kind": "birth_chart" | "conversation" | "other",
  "birth_data": {"date": "YYYY-MM-DD", "time": "HH:MM" or null, "place": "City, Country"} or null,
  "transcript": string or null,
  "description": string
}

How to decide "kind":
- "birth_chart" — an astrological chart wheel, a placements table, or a screenshot from an astrology app.
- "conversation" — a screenshot of messages: texts, DMs, a dating app, email, any back-and-forth.
- "other" — anything else.

"birth_data" — only for a birth chart, and only when the values are printed as readable text
somewhere in the image. Most astrology apps print them near the title. Rules:
- Never infer the date from the planet positions drawn in the wheel. Read printed text or return null.
- Use a 24-hour "HH:MM" time. If the chart says the time is unknown, or no time is printed, use null.
- "place" must be a real, geocodable place name — "Plovdiv, Bulgaria", not "PDV" or coordinates.
- If the date or the place is missing or unreadable, return null for the whole "birth_data" object.

"transcript" — only for a conversation. Write out the exchange in order, marking who sent
what, like:
  THEM: hey, are we still on for friday?
  ME: think so! what time were you thinking
Messages on the right side of a screenshot are almost always the user ("ME"); the left side is
the other person ("THEM"). Include timestamps only where they are visible and meaningful. Do not
paraphrase, soften or summarise — the exact wording is the whole point.

"description" — one or two plain sentences on what is actually visible. For a chart, mention
whether the birth data was printed. For anything else, describe it enough to answer about.
""".strip()


def _parse_json(text: str) -> dict | None:
    """Pull the JSON object out of a reply, tolerating fences and stray prose."""
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except ValueError:
            pass

    braces = re.search(r"\{.*\}", text, re.DOTALL)
    if braces:
        try:
            return json.loads(braces.group(0))
        except ValueError:
            pass
    return None


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME = re.compile(r"^\d{2}:\d{2}$")


def _clean_birth_data(raw) -> dict | None:
    """Keep birth data only when it is complete and well-formed enough to cast.

    A half-read date is worse than none: it would produce a confident chart for
    the wrong person.
    """
    if not isinstance(raw, dict):
        return None

    date = str(raw.get("date") or "").strip()
    place = str(raw.get("place") or "").strip()
    if not _DATE.match(date) or len(place) < 2:
        return None

    time = str(raw.get("time") or "").strip()
    known = bool(_TIME.match(time))

    return {
        "birth_date": date,
        "birth_time": time if known else "",
        "birth_place": place,
        "birth_time_known": known,
    }


def read_images(images: list[dict]) -> dict:
    """Inspect attachments and return what was found.

    Never raises for a bad reply — a failed inspection just means the picture
    is passed through to be looked at directly, which still answers the user.
    """
    if not images:
        return {"kind": "none", "tokens": 0}

    try:
        text, tokens = inspect_images(INSPECTION_PROMPT, images)
    except Exception as exc:  # noqa: BLE001 - degrade, don't fail the question
        print("Image inspection failed:", repr(exc))
        return {"kind": "unknown", "tokens": 0}

    parsed = _parse_json(text) or {}
    kind = parsed.get("kind")
    if kind not in ("birth_chart", "conversation", "other"):
        kind = "other"

    return {
        "kind": kind,
        "birth_data": _clean_birth_data(parsed.get("birth_data")),
        "transcript": (parsed.get("transcript") or None),
        "description": (parsed.get("description") or None),
        "tokens": tokens,
    }
