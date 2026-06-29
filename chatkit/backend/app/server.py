"""LoveGenie ChatKit server.

Translates ChatKit turns to/from the locked Love-Genie backend. The LLM lives in
Love-Genie; this server only:
  - loads thread history from the Store,
  - calls /api/chat-guidance,
  - renders the JSON result as a widget (or casual text),
  - handles widget button actions (re-generate as a different card / tone),
  - fires memory + transcript write-back.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator

from chatkit.actions import Action
from chatkit.agents import stream_widget
from chatkit.server import ChatKitServer, default_generate_id
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ThreadItemDoneEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
    WidgetItem,
)

from . import lovegenie_client as lg
from . import widgets
from .auth import RequestContext
from .lovegenie_client import LoveGenieError
from .memory_store import MemoryStore

MAX_RECENT_ITEMS = 30
# Chips-first gating: the first few turns stay conversational unless the user
# explicitly asks for a card (mirrors LoveGenieChat.jsx forceCasual behaviour).
CASUAL_TURN_THRESHOLD = 3

PAYWALL_TEXT = (
    "You've used your free reads. Unlock full access to keep going — "
    "tap the upgrade option in the app."
)
AUTH_TEXT = "Your session expired. Re-enter your email in the app to continue."
ERROR_TEXT = "Something went wrong reading that. Try sending it again."


def _item_text(item: Any) -> str:
    """Best-effort extract plain text from a stored thread item."""
    content = getattr(item, "content", None)
    if isinstance(content, list):
        parts = [getattr(p, "text", "") for p in content]
        text = " ".join(p for p in parts if p).strip()
        if text:
            return text
    # Widget items carry their copy_text as a useful assistant summary.
    return getattr(item, "copy_text", "") or ""


class LoveGenieChatServer(ChatKitServer[RequestContext]):
    def __init__(self) -> None:
        self.store = MemoryStore()
        super().__init__(self.store)

    # ------------------------------------------------------------------ #
    async def _prior_messages(
        self, thread: ThreadMetadata, context: RequestContext, exclude_id: str | None
    ) -> list[dict[str, str]]:
        page = await self.store.load_thread_items(
            thread.id, after=None, limit=MAX_RECENT_ITEMS, order="desc", context=context
        )
        items = list(reversed(page.data))
        messages: list[dict[str, str]] = []
        for item in items:
            if exclude_id and item.id == exclude_id:
                continue
            role = "user" if isinstance(item, UserMessageItem) else "assistant"
            text = _item_text(item)
            if text:
                messages.append({"role": role, "content": text})
        return messages

    def _hydrate_context(self, thread: ThreadMetadata, context: RequestContext) -> None:
        """Persist context on the thread on turn 1; restore it on later turns
        when the client didn't resend the x-lg-* headers."""
        meta = thread.metadata if isinstance(thread.metadata, dict) else {}
        for attr in ("result_id", "me_type", "partner_type", "user_name", "partner_name"):
            current = getattr(context, attr, None)
            if current:
                meta[attr] = current
            elif meta.get(attr):
                setattr(context, attr, meta[attr])
        thread.metadata = meta

    def _emit_text(self, thread: ThreadMetadata, text: str) -> ThreadItemDoneEvent:
        return ThreadItemDoneEvent(
            item=AssistantMessageItem(
                id=default_generate_id("message"),
                thread_id=thread.id,
                created_at=datetime.now(),
                content=[AssistantMessageContent(text=text)],
            )
        )

    async def _generate(
        self,
        thread: ThreadMetadata,
        context: RequestContext,
        *,
        context_text: str | None,
        prior_messages: list[dict[str, str]],
        requested_output_type: str | None,
        force_casual: bool,
    ) -> AsyncIterator[ThreadStreamEvent]:
        try:
            result = await lg.chat_guidance(
                context,
                context_text=context_text,
                prior_messages=prior_messages,
                requested_output_type=requested_output_type,
                force_casual=force_casual,
            )
        except LoveGenieError as err:
            text = {"paywall": PAYWALL_TEXT, "auth": AUTH_TEXT}.get(err.kind, ERROR_TEXT)
            yield self._emit_text(thread, text)
            return

        output_type = result.get("outputType") or "casual"
        data = result.get("data") or {}

        if output_type == "casual":
            message = ""
            if isinstance(data, dict):
                message = data.get("message") or ""
            yield self._emit_text(thread, message or "Got it.")
        else:
            widget, copy_text = widgets.build_widget(output_type, data)
            async for event in stream_widget(thread, widget, copy_text=copy_text):
                yield event

        # Memory + transcript write-back (best-effort, paid users only).
        transcript = prior_messages + (
            [{"role": "user", "content": context_text}] if context_text else []
        )
        await lg.post_transcript_snapshot(context, transcript)
        await lg.post_memory_update(context, transcript)

    # ------------------------------------------------------------------ #
    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        self._hydrate_context(thread, context)
        await self.store.save_thread(thread, context)

        context_text = _item_text(input_user_message) if input_user_message else None
        prior = await self._prior_messages(
            thread, context, exclude_id=getattr(input_user_message, "id", None)
        )
        user_turns = sum(1 for m in prior if m["role"] == "user") + (1 if context_text else 0)
        force_casual = user_turns <= CASUAL_TURN_THRESHOLD

        async for event in self._generate(
            thread,
            context,
            context_text=context_text,
            prior_messages=prior,
            requested_output_type=None,
            force_casual=force_casual,
        ):
            yield event

    # ------------------------------------------------------------------ #
    async def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle server-side widget button clicks (re-generate a card)."""
        self._hydrate_context(thread, context)

        payload = action.payload if isinstance(action.payload, dict) else {}
        requested = payload.get("requestedOutputType")
        tone = payload.get("tone")

        prior = await self._prior_messages(thread, context, exclude_id=None)
        # Re-use the most recent user message as the situation context.
        context_text = next(
            (m["content"] for m in reversed(prior) if m["role"] == "user"), None
        )
        if tone:
            note = "Make it softer and warmer." if tone == "softer" else "Make it more direct."
            context_text = f"{context_text}\n\n({note})" if context_text else note

        async for event in self._generate(
            thread,
            context,
            context_text=context_text,
            prior_messages=prior,
            requested_output_type=requested or "draft",
            force_casual=False,
        ):
            yield event
