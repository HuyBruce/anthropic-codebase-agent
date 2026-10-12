from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class AnthropicClient:
    """Minimal Messages API client.

    Keeping this small makes the project easy to inspect and avoids hiding the
    agent loop behind an SDK.
    """

    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str, max_tokens: int = 1600) -> None:
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def create_message(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError(
                "Missing ANTHROPIC_API_KEY. Create .env from .env.example or set the variable."
            )

        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
            "tools": tools,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error {exc.code}: {error_body}") from exc
