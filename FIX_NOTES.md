# Applied fixes

## Frontend
- Replaced hardcoded backend access with a configurable API base in the home and chat pages.
- Kept `/api/:path*` rewrites in Next so the frontend can proxy backend requests during local development.
- Switched package scripts to `next dev`, `next build`, `next start`, and `eslint .` so the app does not depend on a bundled `node_modules` layout.

## Backend
- Made CORS configurable through `FRONTEND_ORIGINS`.
- Added a regex to allow deployed Vercel preview or production frontend URLs.

## What to do next
1. Rotate the exposed OpenAI API key from the uploaded `.env`.
2. Remove `node_modules`, `.next`, and any bundled virtual environment folders before redeploying.
3. Reinstall dependencies fresh:

### Frontend
```bash
cd astro-frontend
rm -rf node_modules package-lock.json .next
npm install
npm run dev
```

### Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
