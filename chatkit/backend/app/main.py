"""FastAPI entrypoint for the LoveGenie ChatKit adapter backend.

Receives ChatKit web-component payloads on POST /chatkit, builds a per-request
RequestContext from headers (auth + x-lg-* context), and hands off to
LoveGenieChatServer, which proxies to the locked Love-Genie backend.
"""

from __future__ import annotations

from chatkit.server import StreamingResult
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse

from . import config
from .auth import build_context
from .server import LoveGenieChatServer

app = FastAPI(title="LoveGenie ChatKit Adapter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CHATKIT_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chatkit_server = LoveGenieChatServer()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "lovegenie_api_base": config.LOVEGENIE_API_BASE}


@app.post("/chatkit")
async def chatkit_endpoint(request: Request) -> Response:
    """Process a ChatKit payload with per-request LoveGenie context."""
    payload = await request.body()
    context = build_context(request.headers)
    result = await chatkit_server.process(payload, context)

    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)
