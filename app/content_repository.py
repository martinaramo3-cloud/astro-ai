from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"


def _read_json(relative_path: str) -> Any:
    path = CONTENT_DIR / relative_path
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def get_planets() -> dict[str, Any]:
    return _read_json("astrology-basics/planets.json")


@lru_cache(maxsize=None)
def get_signs() -> dict[str, Any]:
    return _read_json("astrology-basics/signs.json")


@lru_cache(maxsize=None)
def get_houses() -> dict[int, Any]:
    raw = _read_json("astrology-basics/houses.json")
    return {int(key): value for key, value in raw.items()}


@lru_cache(maxsize=None)
def get_aspects() -> dict[str, Any]:
    return _read_json("astrology-basics/aspects.json")


@lru_cache(maxsize=None)
def get_sign_rulers() -> dict[str, list[str]]:
    return _read_json("astrology-basics/sign_rulers.json")


@lru_cache(maxsize=None)
def get_elements() -> dict[str, str]:
    return _read_json("astrology-basics/elements.json")


@lru_cache(maxsize=None)
def get_modalities() -> dict[str, str]:
    return _read_json("astrology-basics/modalities.json")


@lru_cache(maxsize=None)
def get_interpretation_order() -> list[str]:
    return _read_json("engine/interpretation_order.json")


@lru_cache(maxsize=None)
def get_output_templates() -> dict[str, str]:
    return _read_json("engine/output_templates.json")


@lru_cache(maxsize=None)
def get_relationship_rules() -> dict[str, list[str]]:
    return _read_json("engine/relationship_rules.json")


@lru_cache(maxsize=None)
def get_career_rules() -> list[str]:
    return _read_json("engine/career_rules.json")


@lru_cache(maxsize=None)
def get_emotional_rules() -> list[str]:
    return _read_json("engine/emotional_rules.json")


@lru_cache(maxsize=None)
def get_synastry_rules() -> dict[str, Any]:
    return _read_json("engine/synastry_rules.json")
