Astraea Studio upgrade notes

What changed
- Frontend/backend connection is now safer by default. Browser calls use /api unless you explicitly set a public API URL.
- Next.js rewrites now use BACKEND_URL instead of relying on NEXT_PUBLIC_API_URL, which avoids rewrite loops and bad client-side config.
- Server-side content fetches now use the backend base consistently.
- Chat sends full history correctly.
- Method page presents your astrology system as a real website page.
- Backend content-library includes more engine data.
- Prompting uses interpretation order and rule priorities from your uploaded documents.
- Location lookup prefers the free/open Nominatim lookup and only uses Geoapify as a fallback.

Local run
1. Create a .env file in the project root from .env.example.
2. Backend: uvicorn app.main:app --reload --port 8000
3. Frontend: cd astro-frontend && npm install && npm run dev
4. Open http://localhost:3000

Recommended local env
- Keep BACKEND_URL=http://127.0.0.1:8000
- Do not set NEXT_PUBLIC_API_URL for local development unless you intentionally want the browser to skip the Next.js proxy
