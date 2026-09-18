"""Persistent abuse controls shared by workers; never trust client-supplied IDs."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import os
import secrets
import time
from fastapi import HTTPException
from starlette.responses import JSONResponse
from app.database import get_db_connection


def rate_limit(scope: str, identity: str, limit: int, seconds: int) -> None:
    now = time.time()
    key = hashlib.sha256(f"{scope}:{identity}".encode()).hexdigest()
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM rate_limits WHERE expires <= ?", (now,))
        row = conn.execute("SELECT count, expires FROM rate_limits WHERE key = ?", (key,)).fetchone()
        if row and row['count'] >= limit:
            raise HTTPException(429, "Too many requests. Please try again later.",
                                headers={"Retry-After": str(max(1, int(row['expires'] - now) + 1))})
        conn.execute("""INSERT INTO rate_limits (key, count, expires) VALUES (?, 1, ?)
            ON CONFLICT(key) DO UPDATE SET count = count + 1""", (key, now + seconds))
        conn.commit()
    finally:
        conn.close()


class SecurityMiddleware:
    """Limit actual body bytes (including chunked uploads), not just Content-Length."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        path, method = scope['path'], scope['method']
        if method == 'OPTIONS':
            return await self.app(scope, receive, send)
        try:
            peer = (scope.get('client') or ('unknown',))[0]
            # ASGI client is supplied by the server's trusted proxy configuration.
            # Do not read arbitrary X-Forwarded-For / X-Real-IP headers here.
            if path not in ('/', '/health'):
                rate_limit('requests', peer, 240, 60)
            special = {'/login': (30, 900), '/signup': (10, 3600),
                       '/forgot-password': (10, 3600), '/reset-password': (20, 900),
                       '/bug-reports': (10, 3600)}
            if method == 'POST' and path in special:
                rate_limit(path, peer, *special[path])
            if method in ('POST', 'PATCH', 'PUT'):
                maximum = 9 * 1024 * 1024 if path == '/attachments' else 256 * 1024
                chunks, size = [], 0
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    body = message.get('body', b'')
                    size += len(body)
                    if size > maximum:
                        raise HTTPException(413, "That request is too large.")
                    chunks.append(body)
                    if not message.get('more_body'):
                        break
                sent = False
                async def bounded_receive():
                    nonlocal sent
                    if not sent:
                        sent = True
                        return {'type':'http.request', 'body':b''.join(chunks), 'more_body':False}
                    return await receive()
                request_receive = bounded_receive
            else:
                request_receive = receive
        except HTTPException as exc:
            return await JSONResponse({'detail':exc.detail}, status_code=exc.status_code,
                                      headers=exc.headers)(scope, receive, send)

        async def secure_send(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                headers += [(b'x-content-type-options', b'nosniff'),
                            (b'referrer-policy', b'no-referrer'),
                            (b'x-frame-options', b'DENY')]
                if path != '/health':
                    headers = [(k,v) for k,v in headers if k.lower() != b'cache-control']
                    headers.append((b'cache-control', b'no-store'))
                message = {**message, 'headers': headers}
            await send(message)
        await self.app(scope, request_receive, secure_send)


@contextmanager
def ai_budget(user_id, model, prompt, max_output_tokens, images=None):
    """Reserve worst-case tokens before spend; failed/abandoned calls retain a charge.

    Dollar controls are conservative application estimates. Provider-side spending
    limits should remain enabled as the independent billing backstop.
    """
    from app.subscription_service import ALLOWANCES, model_key_for_id
    from app.usage_log_service import cost_for
    byte_count = len(prompt.encode('utf-8'))
    if byte_count > 128 * 1024:
        raise HTTPException(413, "This conversation is too long. Please start a new chat.")
    tokens = byte_count + 20000 * len(images or []) + max_output_tokens
    # Reserve for server-side fallback/cache billing too. Never assume unknown models are free.
    cost = max(cost_for(model, tokens - max_output_tokens, max_output_tokens) * 2, tokens * .000002)
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    month = now.replace(day=1).date().isoformat()
    key = model_key_for_id(model)
    reservation = secrets.token_urlsafe(24)
    conn = get_db_connection()
    try:
        conn.execute('BEGIN IMMEDIATE')
        user = conn.execute('SELECT subscription_tier, email_verified FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            raise HTTPException(401, 'Please log in again.')
        tier = user['subscription_tier']
        if tier == 'free' and key in ('smart', 'deep') and not user['email_verified']:
            raise HTTPException(403, 'Please confirm your email before using Smart or Deep.')
        active = conn.execute('SELECT COUNT(*) FROM ai_reservations WHERE active=1 AND expires>?', (time.time(),)).fetchone()[0]
        own = conn.execute('SELECT COUNT(*) FROM ai_reservations WHERE user_id=? AND active=1 AND expires>?', (user_id,time.time())).fetchone()[0]
        if own or active >= 8:
            raise HTTPException(429, 'An answer is already being prepared. Please try again shortly.', headers={'Retry-After':'10'})
        global_cost = conn.execute('SELECT COALESCE(SUM(cost),0) FROM ai_reservations WHERE created>=?', (today,)).fetchone()[0]
        user_cost = conn.execute('SELECT COALESCE(SUM(cost),0) FROM ai_reservations WHERE user_id=? AND created>=?', (user_id,today)).fetchone()[0]
        daily = float(os.getenv('AI_USER_DAILY_USD', str({'free':1,'standard':5,'premium':15}.get(tier,1))))
        if global_cost + cost > float(os.getenv('AI_GLOBAL_DAILY_USD','100')) or user_cost + cost > daily:
            raise HTTPException(429, 'The daily AI allowance has been reached. Please try again tomorrow.')
        allowance = ALLOWANCES.get(tier,{}).get(key)
        if allowance:
            since = month if allowance['window'] == 'month' else ''
            used = conn.execute('SELECT COALESCE(SUM(tokens_in+tokens_out),0) FROM usage_events WHERE user_id=? AND model_key=? AND created_at>=?', (user_id,key,since)).fetchone()[0]
            pending = conn.execute('SELECT COALESCE(SUM(tokens),0) FROM ai_reservations WHERE user_id=? AND model_key=? AND uncertain=1 AND created>=?', (user_id,key,since)).fetchone()[0]
            if used + pending >= allowance['limit']:
                raise HTTPException(402, 'This model allowance has been used. Please choose Fast or try after it resets.')
        rate_count = conn.execute('SELECT COUNT(*) FROM ai_reservations WHERE user_id=? AND created>=?', (user_id,today)).fetchone()[0]
        if rate_count >= 200:
            raise HTTPException(429, 'The daily AI request limit has been reached.')
        conn.execute('INSERT INTO ai_reservations (id,user_id,model_key,tokens,cost,created,expires) VALUES (?,?,?,?,?,?,?)',
                     (reservation,user_id,key,tokens,cost,now.isoformat(),time.time()+300))
        conn.commit()
    finally:
        conn.close()
    usage = {}
    try:
        yield usage
    finally:
        conn = get_db_connection()
        try:
            if usage:
                actual = cost_for(model,usage.get('tokens_in',0),usage.get('tokens_out',0))
                conn.execute('UPDATE ai_reservations SET active=0, uncertain=0, cost=? WHERE id=?', (actual,reservation))
            else:
                conn.execute('UPDATE ai_reservations SET active=0 WHERE id=?', (reservation,))
            conn.commit()
        finally:
            conn.close()
