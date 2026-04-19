Open in VS Code

1. Unzip the folder.
2. Open the folder root in VS Code.
3. Copy .env.example to .env.
4. Start backend:
   uvicorn app.main:app --reload --port 8000
5. Start frontend:
   cd astro-frontend
   npm install
   npm run dev
6. Visit http://localhost:3000

Important
- Leave NEXT_PUBLIC_API_URL unset for local development.
- The frontend now uses /api in the browser and Next.js proxies that to BACKEND_URL.
