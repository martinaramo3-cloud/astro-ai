"""Per-user, per-model spend tracking.

The provider dashboards show one number: the whole bill. They can't show which
of your users cost what, because they don't know your users exist. So the app
writes down every AI call itself — who asked, which model answered, tokens each
way, and the dollar cost — and this module reads that back into a summary.

Cost is computed here from the published token prices, in the same place the
event is written, so a price change is a one-line edit and history stays as it
was recorded.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.database import get_db_connection

# Published input/output price per 1,000,000 tokens, in US dollars. Anthropic
# first-party and OpenAI rates. Update here if a price changes; past rows keep
# the cost they were written with.
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "gpt-4.1-mini":    (0.40, 1.60),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5":   (5.00, 25.00),
    "claude-fable-5":  (10.00, 50.00),
}

# Which friendly key a raw model id belongs to, so the summary can group by
# Fast / Smart / Deep rather than by cryptic model string.
MODEL_KEY_BY_ID: dict[str, str] = {
    "gpt-4.1-mini": "fast",
    "claude-sonnet-5": "smart",
    "claude-opus-5": "deep",
    "claude-fable-5": "deep",
}


def cost_for(model_id: str, tokens_in: int, tokens_out: int) -> float:
    """Dollar cost of one call. Unknown models cost 0 rather than guess."""
    in_rate, out_rate = MODEL_PRICES.get(model_id, (0.0, 0.0))
    return (tokens_in * in_rate + tokens_out * out_rate) / 1_000_000


def log_usage(user_id: int | None, model_id: str, tokens_in: int, tokens_out: int) -> None:
    """Record one AI call. Never raises — a failure to log must not fail a reply."""
    try:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO usage_events
                (user_id, model_key, model_id, tokens_in, tokens_out, cost_usd, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                MODEL_KEY_BY_ID.get(model_id, "other"),
                model_id,
                tokens_in,
                tokens_out,
                cost_for(model_id, tokens_in, tokens_out),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as exc:  # noqa: BLE001 - logging must never break a reply
        print("usage log failed:", repr(exc))


def month_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


# Kept for internal callers that used the private name.
_month_start_iso = month_start_iso


def sum_user_model_tokens(user_id: int, model_key: str, since_iso: str | None = None) -> int:
    """Total tokens this user has spent on this model — this month, or ever.

    Input and output added together, since the free-tier budget is a plain
    token count. `since_iso` None means all time (a lifetime allowance, like the
    Deep welcome); a month-start means the current calendar month.
    """
    conn = get_db_connection()
    base = "SELECT COALESCE(SUM(tokens_in + tokens_out), 0) FROM usage_events " \
           "WHERE user_id = ? AND model_key = ?"
    if since_iso is None:
        row = conn.execute(base, (user_id, model_key)).fetchone()
    else:
        row = conn.execute(base + " AND created_at >= ?", (user_id, model_key, since_iso)).fetchone()
    conn.close()
    return int(row[0] if row else 0)


def usage_summary() -> dict:
    """What everything has cost — this month and all time, by model and by user.

    Built for the founder's own eyes: the totals to watch, the split across the
    three models, and the handful of users who cost the most.
    """
    conn = get_db_connection()
    month_start = _month_start_iso()

    def scalar(sql: str, params: tuple = ()) -> float:
        row = conn.execute(sql, params).fetchone()
        return (row[0] or 0) if row else 0

    total_all = scalar("SELECT SUM(cost_usd) FROM usage_events")
    total_month = scalar(
        "SELECT SUM(cost_usd) FROM usage_events WHERE created_at >= ?", (month_start,)
    )
    calls_month = scalar(
        "SELECT COUNT(*) FROM usage_events WHERE created_at >= ?", (month_start,)
    )

    by_model = [
        {
            "model_key": row["model_key"],
            "calls": row["calls"],
            "tokens_in": row["tin"] or 0,
            "tokens_out": row["tout"] or 0,
            "cost_usd": round(row["cost"] or 0, 4),
        }
        for row in conn.execute(
            """
            SELECT model_key,
                   COUNT(*) AS calls,
                   SUM(tokens_in) AS tin,
                   SUM(tokens_out) AS tout,
                   SUM(cost_usd) AS cost
            FROM usage_events
            WHERE created_at >= ?
            GROUP BY model_key
            ORDER BY cost DESC
            """,
            (month_start,),
        ).fetchall()
    ]

    top_users = [
        {
            "user_id": row["user_id"],
            "email": row["email"],
            "tier": row["subscription_tier"],
            "calls": row["calls"],
            "cost_usd": round(row["cost"] or 0, 4),
        }
        for row in conn.execute(
            """
            SELECT e.user_id,
                   u.email,
                   u.subscription_tier,
                   COUNT(*) AS calls,
                   SUM(e.cost_usd) AS cost
            FROM usage_events e
            LEFT JOIN users u ON u.id = e.user_id
            WHERE e.created_at >= ?
            GROUP BY e.user_id
            ORDER BY cost DESC
            LIMIT 20
            """,
            (month_start,),
        ).fetchall()
    ]

    conn.close()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "month_to_date_usd": round(total_month, 4),
        "all_time_usd": round(total_all, 4),
        "calls_this_month": int(calls_month),
        "by_model": by_model,
        "top_users": top_users,
    }
