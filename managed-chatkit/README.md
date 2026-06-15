# Managed ChatKit starter

Vite + React UI that talks to a FastAPI session backend for creating ChatKit
workflow sessions.

## Quick start

```bash
npm install           # installs root deps (concurrently)
npm run dev           # runs FastAPI on :8000 and Vite on :3000
```

What happens:

- `npm run dev` runs the backend via `backend/scripts/run.sh` (FastAPI +
  uvicorn) and the frontend via `npm --prefix frontend run dev`.
- The backend exposes `/api/create-session`, exchanging your workflow id and
  `OPENAI_API_KEY` for a ChatKit client secret. The Vite dev server proxies
  `/api/*` to `127.0.0.1:8000`.

## Required environment

- `OPENAI_API_KEY`
- `VITE_CHATKIT_WORKFLOW_ID`
- (optional) `CHATKIT_API_BASE` or `VITE_CHATKIT_API_BASE` (defaults to `https://api.openai.com`)
- (optional) `VITE_API_URL` (override the dev proxy target for `/api`)

Set the env vars in your shell (or process manager) before running. Use a
workflow id from Agent Builder (starts with `wf_...`) and an API key from the
same project and organization.

## Customize

- UI: `frontend/src/components/ChatKitPanel.tsx`
- Session logic: `backend/app/main.py`

## Deploy to Vercel

This directory is Vercel-ready:

- `vercel.json` builds the Vite app to `frontend/dist` (static) and serves it.
- `api/create-session.py` is a stdlib-only Python serverless function that
  replaces the FastAPI backend for the hosted `/api/create-session` route.

Steps:

1. Create a Vercel project with **Root Directory** set to `managed-chatkit`.
2. Add Environment Variables (Production + Preview):
   - `OPENAI_API_KEY` — used at runtime by the serverless function.
   - `VITE_CHATKIT_WORKFLOW_ID` — baked into the frontend bundle at build time,
     so set it before deploying (or redeploy after adding it).
3. Deploy. The static UI calls `/api/create-session`, which the Python function
   handles.
