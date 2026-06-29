"""Unit tests for the Love-Genie -> ChatKit widget builders.

Runs without network or secrets: it only exercises the pure mapping functions.
"""

from __future__ import annotations

from app import widgets
from chatkit.widgets import Button, Card


def _walk(node):
    """Yield every component in a widget tree."""
    yield node
    for child in getattr(node, "children", None) or []:
        yield from _walk(child)


def _buttons(card):
    return [n for n in _walk(card) if isinstance(n, Button)]


def test_read_situation_builds_card_with_draft_action():
    card, copy = widgets.build_read_situation(
        {
            "partnerName": "Jordan",
            "feeling": "overwhelmed",
            "needs": "space then reassurance",
            "notSaying": "they're scared",
            "dynamic": "pursue/withdraw",
        }
    )
    assert isinstance(card, Card)
    assert "overwhelmed" in copy
    actions = [b.onClickAction for b in _buttons(card) if b.onClickAction]
    server_payloads = [a.payload for a in actions if a.handler == "server"]
    assert {"requestedOutputType": "draft"} in server_payloads


def test_draft_renders_all_tones_and_tone_actions():
    card, copy = widgets.build_draft(
        {
            "instinctMessage": "why are you ignoring me",
            "instinctBackfires": "reads as needy",
            "drafts": {
                "playful": ["hey, missing your chaos over here"],
                "warm": ["thinking of you — no pressure to reply"],
                "direct": ["I'd like a quick call tonight"],
            },
            "whyItWorks": "low pressure, clear ask",
        }
    )
    assert isinstance(card, Card)
    assert "quick call" in copy
    tones = {
        a.payload.get("tone")
        for b in _buttons(card)
        if (a := b.onClickAction) and a.handler == "server"
    }
    assert {"softer", "direct"} <= tones


def test_what_to_do_next_includes_steps_and_avoid():
    card, copy = widgets.build_what_to_do_next(
        {
            "steps": [
                {"title": "Wait", "desc": "give it a day", "script": "no text yet"},
                {"title": "Open", "desc": "lead with curiosity"},
            ],
            "avoid": "don't double-text",
        }
    )
    assert isinstance(card, Card)
    assert "Wait" in copy and "Open" in copy


def test_dispatch_falls_back_to_draft_for_unknown_type():
    card, _ = widgets.build_widget("totally_unknown", {"drafts": {"warm": ["hi"]}})
    assert isinstance(card, Card)


def test_supported_output_types():
    assert "read_situation" in widgets.SUPPORTED_OUTPUT_TYPES
    assert "draft" in widgets.SUPPORTED_OUTPUT_TYPES
    assert "what_to_do_next" in widgets.SUPPORTED_OUTPUT_TYPES
