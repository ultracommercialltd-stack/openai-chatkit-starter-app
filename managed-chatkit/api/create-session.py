"""Vercel serverless function: exchange a workflow id for a ChatKit client secret.

Mirrors backend/app/main.py's /api/create-session endpoint, but as a
dependency-free (stdlib only) handler so it runs on Vercel's Python runtime
without a requirements install step.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler

DEFAULT_CHATKIT_BASE = "https://api.openai.com"


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 (Vercel expects this name)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._send(500, {"error": "Missing OPENAI_API_KEY environment variable"})

        body = self._read_json_body()
        workflow_id = self._resolve_workflow_id(body)
        if not workflow_id:
            return self._send(400, {"error": "Missing workflow id"})

        user_id = str(uuid.uuid4())
        api_base = os.getenv("CHATKIT_API_BASE") or DEFAULT_CHATKIT_BASE
        request_body = json.dumps(
            {"workflow": {"id": workflow_id}, "user": user_id}
        ).encode()

        request = urllib.request.Request(
            f"{api_base}/v1/chatkit/sessions",
            data=request_body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "chatkit_beta=v1",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as upstream:
                payload = self._parse_json(upstream.read())
        except urllib.error.HTTPError as error:
            payload = self._parse_json(error.read())
            message = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(message, dict):
                message = message.get("message")
            return self._send(
                error.code, {"error": message or error.reason or "Failed to create session"}
            )
        except urllib.error.URLError as error:
            return self._send(502, {"error": f"Failed to reach ChatKit API: {error.reason}"})

        client_secret = payload.get("client_secret") if isinstance(payload, dict) else None
        if not client_secret:
            return self._send(502, {"error": "Missing client secret in response"})

        return self._send(
            200,
            {
                "client_secret": client_secret,
                "expires_after": payload.get("expires_after"),
            },
        )

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        parsed = self._parse_json(raw)
        return parsed if isinstance(parsed, dict) else {}

    def _resolve_workflow_id(self, body: dict) -> str | None:
        workflow = body.get("workflow", {})
        workflow_id = workflow.get("id") if isinstance(workflow, dict) else None
        workflow_id = (
            workflow_id
            or body.get("workflowId")
            or os.getenv("CHATKIT_WORKFLOW_ID")
            or os.getenv("VITE_CHATKIT_WORKFLOW_ID")
        )
        if isinstance(workflow_id, str) and workflow_id.strip():
            return workflow_id.strip()
        return None

    @staticmethod
    def _parse_json(raw: bytes) -> dict:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
