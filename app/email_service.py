"""Sending the two transactional emails Zodi needs: a password reset and an
email verification, through Resend.

Configured by two environment variables on the server:
  RESEND_API_KEY  — from resend.com; without it, sending is skipped (logged),
                    so the app runs fine before email is set up.
  RESEND_FROM     — the verified sender, e.g. "Zodi <hello@yourdomain>". Until a
                    domain is verified, Resend's onboarding address works but
                    only delivers to your own account email.

The link base comes from FRONTEND_URL (falling back to the first configured
frontend origin), so the emails point at the real site.
"""
from __future__ import annotations

import os

import requests

RESEND_ENDPOINT = "https://api.resend.com/emails"
DEFAULT_FROM = "Zodi <onboarding@resend.dev>"


def _from_address() -> str:
    return (os.getenv("RESEND_FROM") or DEFAULT_FROM).strip()


def frontend_base() -> str:
    """Where the links in emails point — the live site, without a trailing slash."""
    explicit = os.getenv("FRONTEND_URL")
    if explicit:
        return explicit.rstrip("/")
    origins = os.getenv("FRONTEND_ORIGINS", "")
    first = next((o.strip() for o in origins.split(",") if o.strip()), "")
    return (first or "https://astro-ai-duh2.vercel.app").rstrip("/")


def email_configured() -> bool:
    return bool((os.getenv("RESEND_API_KEY") or "").strip())


def _send(to: str, subject: str, html: str) -> bool:
    """Send one email. Returns False (and logs) rather than raising, so a mail
    failure never takes down the request that triggered it."""
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    if not api_key:
        print(f"[email] RESEND_API_KEY not set — skipping '{subject}' to {to}")
        return False
    try:
        r = requests.post(
            RESEND_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": _from_address(), "to": [to], "subject": subject, "html": html},
            timeout=15,
        )
        if r.status_code >= 300:
            print(f"[email] Resend error {r.status_code}: {r.text[:200]}")
            return False
        return True
    except Exception as exc:  # noqa: BLE001 - never fail the caller over email
        print("[email] send failed:", repr(exc))
        return False


# A quiet, on-brand shell so both emails look like they belong to Zodi without
# pulling in a templating dependency.
def _wrap(heading: str, body_html: str, button_label: str, url: str) -> str:
    return f"""
<div style="font-family:Georgia,'Times New Roman',serif;max-width:480px;margin:0 auto;
            padding:32px 28px;color:#241f19;background:#faf6ec;border-radius:16px">
  <p style="font-family:'Jost',system-ui,sans-serif;font-size:12px;letter-spacing:.24em;
            text-transform:uppercase;color:#9a7128;margin:0 0 18px">Zodi</p>
  <h1 style="font-size:26px;font-weight:400;margin:0 0 14px">{heading}</h1>
  <div style="font-size:16px;line-height:1.6;color:#5c5346">{body_html}</div>
  <p style="margin:26px 0">
    <a href="{url}" style="display:inline-block;background:#c99a45;color:#fffdf8;
       text-decoration:none;padding:13px 26px;border-radius:999px;
       font-family:'Jost',system-ui,sans-serif;font-size:13px;letter-spacing:.12em;
       text-transform:uppercase">{button_label}</a>
  </p>
  <p style="font-size:13px;line-height:1.6;color:#8e8474">
    If the button doesn't work, paste this link into your browser:<br>
    <span style="color:#9a7128;word-break:break-all">{url}</span>
  </p>
</div>
""".strip()


def send_password_reset(to: str, name: str, url: str) -> bool:
    body = (
        f"Hi {name or 'there'}, someone asked to reset your Zodi password. "
        "Tap below to choose a new one — the link works for the next hour. "
        "If it wasn't you, you can ignore this; nothing has changed."
    )
    return _send(to, "Reset your Zodi password", _wrap("Reset your password", body, "Set a new password", url))


def send_verification(to: str, name: str, url: str) -> bool:
    body = (
        f"Welcome, {name or 'there'}. Confirm this is your email so we can keep "
        "your account safe and reach you if you ever need a password reset."
    )
    return _send(to, "Confirm your email for Zodi", _wrap("One quick thing", body, "Confirm my email", url))
