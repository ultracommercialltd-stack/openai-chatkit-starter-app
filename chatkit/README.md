# ChatKit Starter — LoveGenie adapter

This backend has been adapted into the **LoveGenie ChatKit adapter**: a FastAPI
server that speaks the ChatKit protocol to the `<ChatKit>` web component and
proxies every turn to the locked Love-Genie backend (the LLM stays in
Love-Genie). See `backend/app/server.py`, `widgets.py`, `lovegenie_client.py`.
It needs `LOVEGENIE_API_BASE` (not `OPENAI_API_KEY`).

## Deploy the adapter (persistent host — Render / Railway / Fly)

The adapter keeps ChatKit thread state **in memory**, so it must run as **one
always-on instance**, not a serverless function. A `Dockerfile` lives in
`backend/`, and a Render Blueprint (`render.yaml`) sits at the repo root.

**Render (one-click from repo):** New → Blueprint → connect this repo + the
`claude/lovegenie-chatkit-comparison-y1ojhn` branch. Set these env vars:

- `LOVEGENIE_API_BASE` — URL of the Love-Genie backend that serves `/api/*`.
- `CHATKIT_ALLOWED_ORIGIN` — the LoveGenieApp domain (comma-separated).
- `SUPABASE_JWT_SECRET` — optional (best-effort user-id decode only).

**Railway / Fly:** point them at `backend/Dockerfile` (build context `backend/`)
and set the same env vars. The container starts `uvicorn app.main:app` on `$PORT`.

After deploy, copy the service URL and set LoveGenieApp's `/chatkit` rewrite
(`vercel.json`) destination to `https://<service>/chatkit`, then flip
`VITE_USE_CHATKIT=1`.

---

## (Upstream) Quick start

Minimal Vite + React UI paired with a FastAPI backend that forwards chat
requests to OpenAI through the ChatKit server library.

## Quick start

```bash
npm install
npm run dev
```

What happens:

- `npm run dev` starts the FastAPI backend on `127.0.0.1:8000` and the Vite
  frontend on `127.0.0.1:3000` with a proxy at `/chatkit`.

## Required environment

- `OPENAI_API_KEY` (backend)
- `VITE_CHATKIT_API_URL` (optional, defaults to `/chatkit`)
- `VITE_CHATKIT_API_DOMAIN_KEY` (optional, defaults to `domain_pk_localhost_dev`)

Set `OPENAI_API_KEY` in your shell or in `.env.local` at the repo root before
running the backend. Register a production domain key in the OpenAI dashboard
and set `VITE_CHATKIT_API_DOMAIN_KEY` when deploying.

## Customize

- Update UI and connection settings in `frontend/src/lib/config.ts`.
- Adjust layout in `frontend/src/components/ChatKitPanel.tsx`.
- Swap the in-memory store in `backend/app/server.py` for persistence.
