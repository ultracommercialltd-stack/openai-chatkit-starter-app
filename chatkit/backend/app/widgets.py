"""Map Love-Genie `{outputType, data}` payloads to ChatKit widgets.

LoveGenie's React cards can't be reproduced inside ChatKit's transcript (no
shadow-DOM CSS), so each card becomes a declarative widget. Text/Box accept raw
hex colors, so we still inject the brand palette into widget *content* even
though the surrounding bubble chrome is themed only via `theme.accent`.

MVP covers three structured cards + casual text:
  read_situation -> ReadTheSituationCard
  draft          -> DraftCard (Exact words)
  what_to_do_next-> WhatToDoNextCard
"""

from __future__ import annotations

from typing import Any

from chatkit.widgets import (
    ActionConfig,
    Badge,
    Box,
    Button,
    Card,
    Divider,
    Markdown,
    Row,
    Text,
    Title,
    WidgetRoot,
)

# Brand palette (from LoveGenieApp/src/lib/lovegenie-tokens.js).
INK = "#1E1E2E"
MUTED = "#7A7280"
EYEBROW = "#9B98A8"
ACCENT = "#C9607A"
SECTION_BG = "#F6F3F5"
ACCENT_BG = "#FAF4F7"

# Action identifiers (kept in sync with the frontend onClientTool handler).
ACTION_REQUEST = "lovegenie.request"  # server: re-generate a different card
ACTION_COPY = "copy_draft"  # client: copy text to clipboard
ACTION_SAVE = "save_read"  # client: persist a thread via threadStorage.js


def _s(value: Any) -> str:
    return value if isinstance(value, str) else ("" if value is None else str(value))


def _eyebrow(label: str) -> Text:
    return Text(value=label.upper(), size="xs", weight="semibold", color=EYEBROW)


def _section(label: str, value: Any, *, accent: bool = False) -> Box:
    return Box(
        background=ACCENT_BG if accent else SECTION_BG,
        radius="lg",
        padding="md",
        gap=6,
        children=[
            Text(value=label, size="sm", weight="semibold", color=ACCENT if accent else MUTED),
            Text(value=_s(value), size="sm", color=INK),
        ],
    )


def _request_button(label: str, payload: dict[str, Any], *, primary: bool = True) -> Button:
    return Button(
        label=label,
        style="primary" if primary else "secondary",
        variant="solid" if primary else "soft",
        color="primary",
        onClickAction=ActionConfig(type=ACTION_REQUEST, payload=payload, handler="server"),
    )


def _client_button(label: str, action_type: str, payload: dict[str, Any]) -> Button:
    return Button(
        label=label,
        style="secondary",
        variant="ghost",
        onClickAction=ActionConfig(type=action_type, payload=payload, handler="client"),
    )


# --------------------------------------------------------------------------- #
# read_situation
# --------------------------------------------------------------------------- #
def build_read_situation(data: dict[str, Any]) -> tuple[WidgetRoot, str]:
    pn = _s(data.get("partnerName")) or "them"
    confidence = _s(data.get("confidence"))
    header_children: list[Any] = [_eyebrow("Read the situation")]
    if confidence:
        header_children.append(Badge(label=confidence, color="info", variant="soft", pill=True))

    card = Card(
        background="#FFFFFF",
        padding="lg",
        size="full",
        children=[
            Row(justify="between", align="center", children=header_children),
            Title(value=f"What's probably going on for {pn}", size="lg", color=INK),
            _section(f"What {pn} is feeling", data.get("feeling")),
            _section(f"What {pn} needs right now", data.get("needs"), accent=True),
            _section(f"What {pn} isn't saying", data.get("notSaying")),
            Text(value=_s(data.get("dynamic")), size="sm", italic=True, color=MUTED),
            Divider(spacing="sm"),
            Row(
                gap=8,
                wrap="wrap",
                children=[
                    _request_button("Tell me what to say", {"requestedOutputType": "draft"}),
                    _client_button("Save read", ACTION_SAVE, {"source": "read_situation"}),
                ],
            ),
        ],
    )
    copy = "\n\n".join(
        x for x in [_s(data.get("feeling")), _s(data.get("needs")), _s(data.get("notSaying"))] if x
    )
    return card, copy


# --------------------------------------------------------------------------- #
# draft  (Exact words)
# --------------------------------------------------------------------------- #
def _tone_block(label: str, lines: Any) -> list[Any]:
    items = lines if isinstance(lines, list) else ([lines] if lines else [])
    text = "\n".join(f"- {_s(x)}" for x in items if _s(x))
    if not text:
        return []
    return [Text(value=label, size="sm", weight="semibold", color=ACCENT), Markdown(value=text)]


def build_draft(data: dict[str, Any]) -> tuple[WidgetRoot, str]:
    drafts = data.get("drafts") if isinstance(data.get("drafts"), dict) else {}
    instinct = _s(data.get("instinctMessage"))
    backfires = _s(data.get("instinctBackfires"))

    children: list[Any] = [
        _eyebrow("Exact words"),
        Title(value="Here's what to send", size="lg", color=INK),
    ]
    if instinct:
        children.append(
            Box(
                background=SECTION_BG,
                radius="lg",
                padding="md",
                gap=6,
                children=[
                    Text(value="Your instinct", size="sm", weight="semibold", color=MUTED),
                    Text(value=instinct, size="sm", color=INK),
                    *(
                        [Text(value=f"Why it backfires: {backfires}", size="xs", color=MUTED)]
                        if backfires
                        else []
                    ),
                ],
            )
        )
    for label, key in (("Softer", "playful"), ("Warm", "warm"), ("Direct", "direct")):
        children.extend(_tone_block(label, drafts.get(key)))
    why = _s(data.get("whyItWorks"))
    if why:
        children.append(Text(value=why, size="sm", italic=True, color=MUTED))
    children.append(Divider(spacing="sm"))
    children.append(
        Row(
            gap=8,
            wrap="wrap",
            children=[
                _request_button("Make it softer", {"requestedOutputType": "draft", "tone": "softer"}, primary=False),
                _request_button("Make it more direct", {"requestedOutputType": "draft", "tone": "direct"}, primary=False),
                _client_button("Copy", ACTION_COPY, {}),
                _client_button("Save read", ACTION_SAVE, {"source": "draft"}),
            ],
        )
    )

    card = Card(background="#FFFFFF", padding="lg", size="full", children=children)
    all_lines: list[str] = []
    for key in ("playful", "warm", "direct"):
        v = drafts.get(key)
        if isinstance(v, list):
            all_lines.extend(_s(x) for x in v if _s(x))
    copy = "\n\n".join(all_lines) or instinct
    return card, copy


# --------------------------------------------------------------------------- #
# what_to_do_next
# --------------------------------------------------------------------------- #
def build_what_to_do_next(data: dict[str, Any]) -> tuple[WidgetRoot, str]:
    steps = data.get("steps") if isinstance(data.get("steps"), list) else []
    step_rows: list[Any] = []
    for i, step in enumerate(steps, start=1):
        step = step if isinstance(step, dict) else {}
        col_children = [
            Text(value=f"{i}. {_s(step.get('title'))}", size="sm", weight="semibold", color=INK),
            Text(value=_s(step.get("desc")), size="sm", color=INK),
        ]
        if _s(step.get("script")):
            col_children.append(Text(value=_s(step.get("script")), size="sm", italic=True, color=ACCENT))
        step_rows.append(Box(gap=4, padding="sm", children=col_children))

    avoid = _s(data.get("avoid"))
    children: list[Any] = [
        _eyebrow("What to do next"),
        Title(value="Your move, in order", size="lg", color=INK),
        *step_rows,
    ]
    if avoid:
        children.append(
            Box(
                background="#FDFAF5",
                radius="lg",
                padding="md",
                gap=6,
                children=[
                    Text(value="Avoid", size="sm", weight="semibold", color="#A08050"),
                    Text(value=avoid, size="sm", color=INK),
                ],
            )
        )
    children.append(Divider(spacing="sm"))
    children.append(
        Row(
            gap=8,
            wrap="wrap",
            children=[_request_button("Help me say it", {"requestedOutputType": "draft"})],
        )
    )
    card = Card(background="#FFFFFF", padding="lg", size="full", children=children)
    copy = "\n".join(
        f"{i}. {_s(s.get('title'))}: {_s(s.get('desc'))}"
        for i, s in enumerate(steps, 1)
        if isinstance(s, dict)
    )
    return card, copy


# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
_BUILDERS = {
    "read_situation": build_read_situation,
    "decode": build_read_situation,  # legacy alias
    "draft": build_draft,
    "what_to_do_next": build_what_to_do_next,
    "strategy": build_what_to_do_next,  # legacy alias
}

SUPPORTED_OUTPUT_TYPES = frozenset(_BUILDERS)


def build_widget(output_type: str, data: dict[str, Any]) -> tuple[WidgetRoot, str]:
    """Return (widget, copy_text). Falls back to a draft card for unknown types."""
    builder = _BUILDERS.get((output_type or "").strip().lower(), build_draft)
    return builder(data if isinstance(data, dict) else {})
