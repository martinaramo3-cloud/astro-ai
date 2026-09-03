"""Subscription tier + daily token limits.

Tiers:
  free     - basic model, 120 000 tokens/day
  standard - mid model, 600 000 tokens/day
  premium  - top model, unlimited

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
    # `daily_token_limit` is the old blunt cap and is now None everywhere —
    # limits are per model and counted in messages, in ALLOWANCES below, which
    # is both what people understand and what lets Fast stay unlimited while
    # Smart and Deep are metered. `model` is only the fallback when a request
    # names no model.
    "free": {
        "label": "Free",
        "model": "gpt-4.1-mini",
        "daily_token_limit": None,
    },
    "standard": {
        "label": "Standard",
        "model": "claude-sonnet-5",
        "daily_token_limit": None,
    },
    "premium": {
        "label": "Premium",
        # Opus 5, not Fable 5: half the token price ($5/$25 vs $10/$50) for
        # what is almost certainly indistinguishable quality on warm
        # interpretive writing. Flip both this and MODELS["deep"] back to
        # "claude-fable-5" to revert.
        "model": "claude-opus-5",
        "daily_token_limit": None,
    },
}

# How many TOKENS of each model a tier may spend, and over what window. Tokens,
# not messages, because a message is not a fixed size — a long synastry message
# costs several times a short solo one, so a token budget tracks real cost.
# Fast is unlimited for everyone, so it is never listed. A model absent from a
# tier's entry is unlimited for that tier. Only free is metered today; the paid
# tiers stay open until there is real usage data and a checkout to upgrade into.
#   window "month"    — resets on the 1st of each month
#   window "lifetime" — never resets (a one-time welcome, like free's Deep)
# Sizing, from real usage: a solo Smart message is ~4,000 tokens in+out, so
# 50,000 is about a dozen Smart messages; Deep messages run larger, so 20,000
# is a real first Deep conversation to feel it once.
ALLOWANCES: dict[str, dict[str, dict]] = {
    "free": {
        "smart": {"limit": 50_000, "window": "month"},
        "deep":  {"limit": 20_000, "window": "lifetime"},
    },
}

VALID_TIERS = set(TIERS.keys())
DEFAULT_TIER = "free"

# How many other people a tier may save for synastry. None = unlimited. Free
# gets exactly one — enough to taste compatibility on a single person (the
# crush, the ex) and want more. Costs nothing to store; this is pure upsell.
PEOPLE_LIMITS: dict[str, int | None] = {
    "free": 1,
    "standard": 3,
    "premium": None,
}


def check_people_limit(tier: str | None, current_count: int) -> None:
    """Refuse a new saved person once the tier's allowance is full."""
    limit = PEOPLE_LIMITS.get(tier or DEFAULT_TIER, 1)
    if limit is not None and current_count >= limit:
        one = limit == 1
        raise HTTPException(
            status_code=402,
            detail=(
                f"Your plan lets you save {limit} {'person' if one else 'people'} "
                "for compatibility. Upgrade to add more — subscriptions coming soon."
            ),
        )


# Friendly model catalog. `key` is the stable id the frontend sends and stores;
# `id` is the actual OpenAI model name.
MODELS: dict[str, dict] = {
    "fast":  {"key": "fast",  "id": "gpt-4.1-mini",   "label": "Fast",  "blurb": "Quick, everyday chats"},
    "smart": {"key": "smart", "id": "claude-sonnet-5", "label": "Smart", "blurb": "Deeper, more nuanced answers"},
    "deep":  {"key": "deep",  "id": "claude-opus-5", "label": "Deep",  "blurb": "The most thorough, insightful answers"},
}

# Which model keys each tier may pick (cheapest first). Everyone can now pick
# all three — free can taste Smart and Deep — and how much they may actually use
# is governed by ALLOWANCES above, not by hiding the model. Cheapest first, so
# a tier's fallback model is the cheapest one it can reach.
TIER_MODELS: dict[str, list[str]] = {
    "free":     ["fast", "smart", "deep"],
    "standard": ["fast", "smart", "deep"],
    "premium":  ["fast", "smart", "deep"],
}


def get_tier_config(tier: str | None) -> TierConfig:
    return TIERS.get(tier or DEFAULT_TIER, TIERS[DEFAULT_TIER])


def available_models_for_tier(tier: str | None) -> list[dict]:
    """Public-facing list of models a tier can choose from."""
    keys = TIER_MODELS.get(tier or DEFAULT_TIER, TIER_MODELS[DEFAULT_TIER])
    return [
        {"key": MODELS[k]["key"], "label": MODELS[k]["label"], "blurb": MODELS[k]["blurb"]}
        for k in keys
    ]


VALID_EFFORTS = {"low", "medium", "high"}


def resolve_effort(tier: str | None, requested: str | None) -> str | None:
    """Honour an effort choice only from tiers that pay for a thinking model.

    Effort drives how long the model reasons, and reasoning bills as output —
    so this is a spend control, not a preference.
    """
    if requested not in VALID_EFFORTS:
        return None
    # Effort is a paid lever now that free can *taste* the thinking models —
    # honouring high effort on a free message would let it cost several times a
    # normal one, and the free taste is meant to be predictable, not deep.
    if (tier or DEFAULT_TIER) == "free":
        return None
    return requested


def resolve_model(tier: str | None, requested_key: str | None) -> str:
    """Return the OpenAI model id for a tier, honoring a valid user choice.

    Never trust the client to gate this: if the requested model isn't available
    to the user's tier, fall back to the tier's default model.
    """
    allowed = TIER_MODELS.get(tier or DEFAULT_TIER, TIER_MODELS[DEFAULT_TIER])
    if requested_key in allowed:
        return MODELS[requested_key]["id"]
    return get_tier_config(tier)["model"]


def model_key_for_id(model_id: str) -> str:
    """Map a raw model id back to its friendly key (fast/smart/deep)."""
    for key, meta in MODELS.items():
        if meta["id"] == model_id:
            return key
    return "fast"


def _next_month_start() -> datetime:
    now = datetime.now(timezone.utc)
    year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    return datetime(year, month, 1, tzinfo=timezone.utc)


def _human_until(when: datetime) -> str:
    """A rough 'in 3 days' / 'in 5 hours', for the 'resets in…' message."""
    delta = when - datetime.now(timezone.utc)
    hours = max(0, int(delta.total_seconds() // 3600))
    if hours >= 48:
        return f"in {hours // 24} days"
    if hours >= 1:
        return f"in {hours} hours"
    return "soon"


def check_model_allowance(user_id: int | None, tier: str | None, model_key: str) -> None:
    """Stop a metered model once its allowance is spent. Fast is never metered.

    Counts how many of this model the user has already sent inside the window,
    from the usage log, and refuses the next one with a message that says when
    it comes back. The refusal is a 402, not a 429: this is 'you need to
    upgrade', not 'the server is busy'.
    """
    from app.usage_log_service import sum_user_model_tokens, month_start_iso

    if user_id is None:
        return
    allowance = ALLOWANCES.get(tier or DEFAULT_TIER, {}).get(model_key)
    if not allowance:
        return  # unlimited for this tier + model

    window = allowance["window"]
    since = month_start_iso() if window == "month" else None
    used = sum_user_model_tokens(user_id, model_key, since)
    # Only block a *new* message once already over — never a message already in
    # flight. Someone at 49k who sends one more finishes it; the next is blocked.
    if used < allowance["limit"]:
        return

    label = MODELS.get(model_key, {}).get("label", model_key)
    if window == "lifetime":
        detail = (
            f"You've used your welcome {label} messages. "
            f"{label} is part of a paid plan — subscriptions are coming soon. "
            "Fast is always free and unlimited."
        )
    else:
        detail = (
            f"You've used your free {label} for this month (resets "
            f"{_human_until(_next_month_start())}). Fast is always free and unlimited, "
            "or upgrade for more."
        )
    raise HTTPException(status_code=402, detail=detail)


def model_limits_for(user_id: int | None, tier: str | None) -> dict:
    """Per-model token budget and how much is left, for the app to show.

    The raw token numbers are here for the app to render however it likes —
    a bar, a percentage, or a quiet 'running low' — since a bare token count
    means nothing to a person.
    """
    from app.usage_log_service import sum_user_model_tokens, month_start_iso

    out: dict[str, dict] = {}
    for model_key, allowance in ALLOWANCES.get(tier or DEFAULT_TIER, {}).items():
        window = allowance["window"]
        since = month_start_iso() if window == "month" else None
        used = sum_user_model_tokens(user_id, model_key, since) if user_id else 0
        limit = allowance["limit"]
        entry = {
            "limit_tokens": limit,
            "used_tokens": used,
            "remaining_tokens": max(0, limit - used),
            "fraction_used": round(min(1.0, used / limit), 3) if limit else 1.0,
            "window": window,
        }
        if window == "month":
            entry["resets_at"] = _next_month_start().isoformat()
        out[model_key] = entry
    return out


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
            "available_models": available_models_for_tier(DEFAULT_TIER),
            "daily_token_limit": config["daily_token_limit"],
            "tokens_used_today": 0,
            "tokens_remaining_today": config["daily_token_limit"],
            "model_limits": model_limits_for(None, DEFAULT_TIER),
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
            "available_models": available_models_for_tier(DEFAULT_TIER),
            "daily_token_limit": config["daily_token_limit"],
            "tokens_used_today": 0,
            "tokens_remaining_today": config["daily_token_limit"],
            "model_limits": model_limits_for(None, DEFAULT_TIER),
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
        "available_models": available_models_for_tier(tier),
        "daily_token_limit": limit,
        "tokens_used_today": tokens_used,
        "tokens_remaining_today": remaining,
        # Per-model message allowances, so the picker can show "7 of 10 left"
        # and Deep can show its remaining welcome messages.
        "model_limits": model_limits_for(user_id, tier),
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


def find_user_id_by_email(email: str) -> int | None:
    """Look up an account by email, for admin tier changes.

    Until there's a checkout flow, upgrades are applied by hand, and email is
    what you actually know about a customer — not their database id.
    """
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id FROM users WHERE lower(email) = lower(?)", (email.strip(),)
    ).fetchone()
    conn.close()
    return row["id"] if row else None


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
