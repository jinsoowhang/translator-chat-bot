"""Pydantic models for Whapi.Cloud webhook payloads.

Whapi sends a flexible JSON body with `messages: [...]` entries. We only
model the fields we actually use and ignore the rest.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MessageText(BaseModel):
    model_config = ConfigDict(extra="ignore")
    body: str = ""


class MessageContext(BaseModel):
    """Reply/quote context — present when a message is a reply to another."""

    model_config = ConfigDict(extra="ignore")
    quoted_id: str | None = None


class WhapiMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    chat_id: str = Field(..., alias="chat_id")
    from_: str | None = Field(default=None, alias="from")
    from_me: bool = Field(default=False, alias="from_me")
    type: str = "text"
    text: MessageText | None = None
    # Whapi sometimes nests the body differently; keep a raw fallback.
    body: str | None = None
    context: MessageContext | None = None
    timestamp: int | None = None

    @property
    def is_group(self) -> bool:
        return self.chat_id.endswith("@g.us")

    @property
    def content(self) -> str:
        if self.text and self.text.body:
            return self.text.body
        return self.body or ""


class WhapiWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    messages: list[WhapiMessage] = Field(default_factory=list)
    event: dict | None = None
