"""Message processing: mention detection, translation, and reply formatting."""
from __future__ import annotations

import logging
import re

from .config import BotConfig
from .models import WhapiMessage
from .translator import SmartTranslator
from .whatsapp import WhapiClient

log = logging.getLogger(__name__)


def _mention_pattern(bot_name: str) -> re.Pattern[str]:
    # Matches "@BotName" (case-insensitive), as a standalone token.
    return re.compile(rf"@{re.escape(bot_name)}\b", re.IGNORECASE)


def extract_mention_text(body: str, bot_name: str) -> str | None:
    """If the message @mentions the bot, return the remaining text (without the mention).
    Returns None if no mention was found."""
    pattern = _mention_pattern(bot_name)
    if not pattern.search(body):
        return None
    stripped = pattern.sub("", body).strip()
    return stripped


class MessageHandler:
    def __init__(
        self,
        config: BotConfig,
        whatsapp: WhapiClient,
        translator: SmartTranslator,
    ) -> None:
        self._config = config
        self._whatsapp = whatsapp
        self._translator = translator

    async def handle(self, message: WhapiMessage) -> None:
        # Ignore non-text events. We deliberately do NOT filter `from_me`:
        # since the bot runs on the user's personal WhatsApp number, the user's
        # own messages are `from_me: true` too, and they should be able to
        # @mention the bot from their own phone. Loop safety comes from the
        # @mention check below — the bot's own replies (e.g. "[EN] Hello")
        # don't contain @TranslatorBot, so they're naturally ignored.
        if message.type != "text":
            return
        body = message.content.strip()
        if not body:
            return

        # Only respond in group chats (per PRD), but allow DMs for dev convenience.
        to_translate = extract_mention_text(body, self._config.bot_name)
        if to_translate is None:
            return
        if not to_translate:
            log.info("Empty mention on message %s — ignoring", message.id)
            return

        log.info("Translating message %s from chat %s", message.id, message.chat_id)

        try:
            result = await self._translator.translate_with_routing(to_translate)
        except Exception as exc:  # noqa: BLE001 — we want a friendly fallback in chat
            log.exception("Translation failed: %s", exc)
            await self._whatsapp.send_text(
                to=message.chat_id,
                body="⚠️ Translation unavailable right now. Please try again in a moment.",
                quoted_message_id=message.id,
            )
            return

        label = self._config.label(result.source_lang)
        # The tag shows the TARGET language (what the reader sees).
        target_label = self._config.label(
            self._config.target_for(result.source_lang) or ""
        )
        tag = target_label or label
        reply = f"[{tag}] {result.translation}"

        await self._whatsapp.send_text(
            to=message.chat_id,
            body=reply,
            quoted_message_id=message.id,
        )
