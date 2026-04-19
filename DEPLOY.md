# Deploy Guide

This project is easiest to deploy as:

- frontend: Vercel
- backend API: Render

## Before you start

- Do not upload `.env`
- Do not upload `venv/`, `node_modules/`, or `.next/`
- Keep your OpenAI key only in hosting environment variables

## 1. Push the project to GitHub

Create a GitHub repo and upload the folder contents from this project root.

## 2. Deploy the backend on Render

Use the `render.yaml` file in the repo root, or create the service manually with:

- runtime: Python
- root directory: repo root
- build command: `pip install -r requirements.txt`
- start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- health check path: `/health`

Set environment variables:

- `OPENAI_API_KEY`: your real key
- `DATABASE_PATH`: `astrology.db`

After deploy, copy the public backend URL, for example:

- `https://your-backend.onrender.com`

## 3. Deploy the frontend on Vercel

Import the same GitHub repo into Vercel and set:

- framework preset: Next.js
- root directory: `astro-frontend`

Set environment variables:

- `BACKEND_URL`: your Render backend URL

Optional:

- `NEXT_PUBLIC_API_URL`: leave unset unless you want the browser to call the backend directly

## 4. Redeploy the frontend

After `BACKEND_URL` is saved, trigger a new Vercel deploy.

## 5. Test the live site

Check:

- homepage loads
- signup/login works
- chart generation works
- compatibility questions return answers

## Important note about the current database

This app currently uses SQLite. That is fine for an early test deployment, but it is not ideal for a serious public app with user accounts.

For a stronger production setup, the next upgrade should be moving users and profiles to Postgres.
