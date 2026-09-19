"""Persistent abuse controls shared by workers; never trust client-supplied IDs."""
import hashlib
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
