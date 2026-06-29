"""Identity + per-request context extraction.

The `<ChatKit>` web component is configured (frontend) with an `api.fetch`
override that attaches the same auth LoveGenieApp already uses today:

  - `Authorization: Bearer <supabase_access_token>`  (paid users), OR
  - `x-lead-token: <lead_uuid>`                        (free leads)

plus three context headers the composer can't carry in the message body:

  - `x-lg-result-id`   -> Love-Genie lg_results.id (for memory write-back)
  - `x-lg-me-type`     -> user MBTI type
  - `x-lg-partner-type`-> partner MBTI type

We forward auth to Love-Genie verbatim so entitlement/paywall/free-reads behave
exactly as they do for the current chat. JWT verification here is best-effort
(used only to surface a user id); Love-Genie remains the gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import config

try:  # optional; only used for best-effort decode
    import jwt  # type: ignore
except Exception:  # pragma: no cover - jwt is a declared dep, guard anyway
    jwt = None  # type: ignore


@dataclass
class RequestContext:
    """Per-request identity + LoveGenie context, threaded through respond/action."""

    authorization: str | None = None
    lead_token: str | None = None
    user_id: str | None = None
    result_id: str | None = None
    me_type: str = ""
    partner_type: str = ""
    me_archetype_label: str = ""
    partner_archetype_label: str = ""
    user_name: str | None = None
    partner_name: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_authenticated(self) -> bool:
        return bool(self.authorization or self.lead_token)

    def auth_headers(self) -> dict[str, str]:
        """Headers to forward to Love-Genie so it can enforce auth/entitlement."""
        headers: dict[str, str] = {}
        if self.authorization:
            headers["Authorization"] = self.authorization
        if self.lead_token:
            headers["x-lead-token"] = self.lead_token
        return headers


def _decode_user_id(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token or jwt is None:
        return None
    try:
        if config.SUPABASE_JWT_SECRET:
            claims = jwt.decode(
                token,
                config.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": False},
            )
        else:
            # No secret configured: decode without verification just to read sub.
            claims = jwt.decode(token, options={"verify_signature": False})
        sub = claims.get("sub")
        return str(sub) if sub else None
    except Exception:
        return None


def build_context(headers) -> RequestContext:
    """Build a RequestContext from request headers (case-insensitive mapping)."""

    def get(name: str) -> str | None:
        try:
            value = headers.get(name)
        except Exception:
            value = None
        return value.strip() if isinstance(value, str) and value.strip() else None

    authorization = get("authorization")
    return RequestContext(
        authorization=authorization,
        lead_token=get("x-lead-token"),
        user_id=_decode_user_id(authorization),
        result_id=get("x-lg-result-id"),
        me_type=get("x-lg-me-type") or "",
        partner_type=get("x-lg-partner-type") or "",
        me_archetype_label=get("x-lg-me-archetype") or "",
        partner_archetype_label=get("x-lg-partner-archetype") or "",
        user_name=get("x-lg-user-name"),
        partner_name=get("x-lg-partner-name"),
    )
