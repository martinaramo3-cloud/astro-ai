"""Subscription tier + daily token limits.

Tiers:
  free     - basic model, 30 000 tokens/day
  standard - mid model, 300 000 tokens/day
  premium  - top reasoning model, unlimited

The per-tier model and limit settings live in TIERS below so they are easy to
tweak without touching call sites.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TypedDict

from fastapi import HTTPException

from app.database import get_db_connection


class TierConfig(TypedDict):
    label: str
    model: str
    daily_token_limit: int | None  # None = unlimited


TIERS: dict[str, TierConfig] = {
    "free": {
        "label": "Free",
        "model": "gpt-4.1-mini",
        "daily_token_limit": 30_000,
    },
    "standard": {
        "label": "Standard",
        "model": "gpt-4.1",
        "daily_token_limit": 300_000,
    },
    "premium": {
        "label": "Premium",
        "model": "o1",
        "daily_token_limit": None,
    },
}

VALID_TIERS = set(TIERS.keys())
DEFAULT_TIER = "free"


def get_tier_config(tier: str | None) -> TierConfig:
    return TIERS.get(tier or DEFAULT_TIER, TIERS[DEFAULT_TIER])


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def get_user_tier(user_id: int | None) -> str:
    """Return the user's tier, or DEFAULT_TIER if user_id is None or not found."""
    if user_id is None:
        return DEFAULT_TIER

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT subscription_tier FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return DEFAULT_TIER

    tier = row["subscription_tier"] or DEFAULT_TIER
    return tier if tier in VALID_TIERS else DEFAULT_TIER


def get_usage_status(user_id: int | None) -> dict:
    """Return current tier, today's token usage, and the daily token limit."""
    if user_id is None:
        config = TIERS[DEFAULT_TIER]
        return {
            "tier": DEFAULT_TIER,
            "tier_label": config["label"],
            "model": config["model"],
            "daily_token_limit": config["daily_token_limit"],
            "tokens_used_today": 0,
            "tokens_remaining_today": config["daily_token_limit"],
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT subscription_tier, daily_usage_count, daily_usage_date FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        config = TIERS[DEFAULT_TIER]
        return {
            "tier": DEFAULT_TIER,
            "tier_label": config["label"],
            "model": config["model"],
            "daily_token_limit": config["daily_token_limit"],
            "tokens_used_today": 0,
            "tokens_remaining_today": config["daily_token_limit"],
        }

    tier = row["subscription_tier"] if row["subscription_tier"] in VALID_TIERS else DEFAULT_TIER
    config = TIERS[tier]
    tokens_used = row["daily_usage_count"] if row["daily_usage_date"] == _today_iso() else 0
    limit = config["daily_token_limit"]
    remaining = None if limit is None else max(0, limit - tokens_used)

    return {
        "tier": tier,
        "tier_label": config["label"],
        "model": config["model"],
        "daily_token_limit": limit,
        "tokens_used_today": tokens_used,
        "tokens_remaining_today": remaining,
    }


def check_usage(user_id: int | None) -> TierConfig:
    """Check whether the user can make another AI call.

    Raises:
        HTTPException 429 if the user has exceeded their daily token limit.

    Returns:
        TierConfig that the AI service should use (model, label, etc.)
    """
    if user_id is None:
        return TIERS[DEFAULT_TIER]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT subscription_tier, daily_usage_count, daily_usage_date FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return TIERS[DEFAULT_TIER]

    tier = row["subscription_tier"] if row["subscription_tier"] in VALID_TIERS else DEFAULT_TIER
    config = TIERS[tier]
    today = _today_iso()
    tokens_used = row["daily_usage_count"] if row["daily_usage_date"] == today else 0

    limit = config["daily_token_limit"]
    if limit is not None and tokens_used >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've used your {config['label']} plan's daily limit of {limit:,} tokens. "
                "Upgrade your plan to keep going, or come back tomorrow."
            ),
        )

    return config


def record_usage(user_id: int | None, tokens_used: int) -> None:
    """Add tokens_used to the user's daily token counter."""
    if user_id is None or tokens_used <= 0:
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT daily_usage_count, daily_usage_date FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return

    today = _today_iso()
    current = row["daily_usage_count"] if row["daily_usage_date"] == today else 0
    cursor.execute(
        "UPDATE users SET daily_usage_count = ?, daily_usage_date = ? WHERE id = ?",
        (current + tokens_used, today, user_id),
    )
    conn.commit()
    conn.close()


def set_user_tier(user_id: int, new_tier: str) -> dict | None:
    """Update a user's subscription tier. Returns the updated user dict or None if not found."""
    if new_tier not in VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier '{new_tier}'. Must be one of: {sorted(VALID_TIERS)}.",
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        conn.close()
        return None

    cursor.execute(
        "UPDATE users SET subscription_tier = ? WHERE id = ?",
        (new_tier, user_id),
    )
    conn.commit()

    cursor.execute(
        """
        SELECT id, name, email, birth_date, birth_time, birth_place, subscription_tier
        FROM users WHERE id = ?
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None
