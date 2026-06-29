"""Environment configuration for the LoveGenie ChatKit adapter.

This server is a *translation layer*: it speaks the ChatKit protocol to the
`<ChatKit>` web component and proxies every turn to the existing (locked)
Love-Genie Node/Vercel backend. It does not call an LLM itself, so no
OPENAI_API_KEY is required for the data plane.
"""

from __future__ import annotations

import os


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


# Base URL of the locked Love-Genie backend (e.g. http://127.0.0.1:4310 in dev,
# or the production deployment host). All /api/* calls are made against this.
LOVEGENIE_API_BASE: str = (
    _clean(os.getenv("LOVEGENIE_API_BASE")) or "http://127.0.0.1:4310"
)

# Supabase project URL + JWT secret. The secret is optional: when present we
# decode the Bearer token to surface a user id for logging/metadata. Love-Genie
# remains the source of truth for auth + entitlement, so verification here is a
# convenience, not a gate.
SUPABASE_URL: str | None = _clean(os.getenv("SUPABASE_URL"))
SUPABASE_JWT_SECRET: str | None = _clean(os.getenv("SUPABASE_JWT_SECRET"))

# CORS: the LoveGenieApp origin allowed to talk to /chatkit. Comma-separated.
# Defaults to the Vite dev origin used by the starter + LoveGenieApp.
_ALLOWED = _clean(os.getenv("CHATKIT_ALLOWED_ORIGIN"))
CHATKIT_ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _ALLOWED.split(",") if o.strip()]
    if _ALLOWED
    else ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"]
)

# Outbound request timeout to Love-Genie (seconds).
LOVEGENIE_TIMEOUT: float = float(_clean(os.getenv("LOVEGENIE_TIMEOUT")) or "30")
