"""Async client for the Whapi.Cloud REST API.

Docs: https://whapi.readme.io/
We only need `POST /messages/text` with an optional `quoted` field for quote-replies.
"""
from __future__ import annotations

import httpx


class WhapiClient:
    def __init__(self, token: str, base_url: str = "https://gate.whapi.cloud") -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(15.0),
        )

    async def send_text(
        self,
        to: str,
        body: str,
        quoted_message_id: str | None = None,
    ) -> dict:
        """Send a text message. If `quoted_message_id` is set, send it as a quote-reply."""
        payload: dict = {"to": to, "body": body}
        if quoted_message_id:
            payload["quoted"] = quoted_message_id
        resp = await self._client.post("/messages/text", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()
