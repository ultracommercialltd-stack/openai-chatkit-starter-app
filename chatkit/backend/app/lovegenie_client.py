"""Thin async HTTP client for the locked Love-Genie Node/Vercel backend.

Mirrors what LoveGenieApp's `src/services/chatGuidanceClient.js` does today:
same endpoints, same request bodies, same auth headers. The ChatKit adapter
never talks to an LLM directly — Love-Genie owns routing, prompts, cards,
memory and entitlement.
"""

from __future__ import annotations

from typing import Any

import httpx

from . import config
from .auth import RequestContext


class LoveGenieError(Exception):
    """Raised when Love-Genie returns a non-OK response we must surface."""

    def __init__(self, status: int, kind: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.kind = kind  # "paywall" | "auth" | "error"
        self.message = message


def _headers(ctx: RequestContext) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    headers.update(ctx.auth_headers())
    return headers


async def chat_guidance(
    ctx: RequestContext,
    *,
    context_text: str | None,
    prior_messages: list[dict[str, str]],
    category: str | None = None,
    sub_situation: str | None = None,
    requested_output_type: str | None = None,
    force_casual: bool = False,
    screenshot_context: list[str] | None = None,
) -> dict[str, Any]:
    """POST /api/chat-guidance. Returns {ok, outputType, intent, data, chips}.

    Raises LoveGenieError on paywall (402) / auth (401) / other failures so the
    server layer can render a friendly assistant message instead of crashing.
    """
    body: dict[str, Any] = {
        "category": category,
        "subSituation": sub_situation,
        "context": context_text,
        "meType": ctx.me_type,
        "partnerType": ctx.partner_type,
        "meArchetypeLabel": ctx.me_archetype_label,
        "partnerArchetypeLabel": ctx.partner_archetype_label,
        "userName": ctx.user_name,
        "partnerName": ctx.partner_name,
        "priorMessages": prior_messages,
        "requestedOutputType": requested_output_type,
        "forceCasual": force_casual,
        "screenshotContext": screenshot_context or [],
        "resultId": ctx.result_id,
    }

    async with httpx.AsyncClient(
        base_url=config.LOVEGENIE_API_BASE, timeout=config.LOVEGENIE_TIMEOUT
    ) as client:
        try:
            resp = await client.post(
                "/api/chat-guidance", headers=_headers(ctx), json=body
            )
        except httpx.RequestError as exc:
            raise LoveGenieError(502, "error", f"Could not reach Love-Genie: {exc}")

    payload: dict[str, Any]
    try:
        payload = resp.json()
    except Exception:
        payload = {}

    if resp.status_code == 402 or payload.get("error") == "paywall":
        raise LoveGenieError(402, "paywall", "free_reads_exhausted")
    if resp.status_code == 401 or payload.get("error") == "lead_session_lost":
        raise LoveGenieError(401, "auth", "lead_session_lost")
    if resp.status_code >= 400 or not payload.get("ok"):
        msg = payload.get("error") or payload.get("message") or "request_failed"
        raise LoveGenieError(resp.status_code or 500, "error", str(msg))

    return payload


async def post_transcript_snapshot(
    ctx: RequestContext, transcript: list[dict[str, str]]
) -> None:
    """Fire-and-forget /api/transcript-snapshot (paid users; needs Bearer)."""
    if not ctx.result_id or not ctx.authorization:
        return
    if len(transcript) < 2:
        return
    async with httpx.AsyncClient(
        base_url=config.LOVEGENIE_API_BASE, timeout=config.LOVEGENIE_TIMEOUT
    ) as client:
        try:
            await client.post(
                "/api/transcript-snapshot",
                headers=_headers(ctx),
                json={"resultId": ctx.result_id, "transcript": transcript},
            )
        except httpx.RequestError:
            pass  # best-effort


async def post_memory_update(
    ctx: RequestContext, prior_messages: list[dict[str, str]]
) -> None:
    """Fire-and-forget /api/memory-update (paid users; needs Bearer)."""
    if not ctx.result_id or not ctx.authorization:
        return
    if len(prior_messages) < 4:
        return
    async with httpx.AsyncClient(
        base_url=config.LOVEGENIE_API_BASE, timeout=config.LOVEGENIE_TIMEOUT
    ) as client:
        try:
            await client.post(
                "/api/memory-update",
                headers=_headers(ctx),
                json={"resultId": ctx.result_id, "priorMessages": prior_messages},
            )
        except httpx.RequestError:
            pass  # best-effort
