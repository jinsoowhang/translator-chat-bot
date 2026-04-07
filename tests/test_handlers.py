"""Unit tests for mention detection and message handler routing."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from translator_bot.config import BotConfig, LanguagePair
from translator_bot.handlers import MessageHandler, extract_mention_text
from translator_bot.models import MessageText, WhapiMessage
from translator_bot.translator import TranslationResult


def make_config() -> BotConfig:
    return BotConfig(
        language_pairs=[
            LanguagePair(source=["en", "es"], target="ko"),
            LanguagePair(source=["ko"], target="en"),
        ],
        bot_name="TranslatorBot",
        claude_model="claude-sonnet-4-5-20250929",
        language_labels={"en": "EN", "es": "ES", "ko": "KO"},
    )


def test_extract_mention_present():
    assert extract_mention_text("@TranslatorBot hello", "TranslatorBot") == "hello"


def test_extract_mention_case_insensitive():
    assert extract_mention_text("@translatorbot hola", "TranslatorBot") == "hola"


def test_extract_mention_absent():
    assert extract_mention_text("no mention here", "TranslatorBot") is None


def test_extract_mention_only():
    assert extract_mention_text("@TranslatorBot", "TranslatorBot") == ""


@pytest.mark.asyncio
async def test_handler_processes_own_messages_when_mentioned():
    """The bot runs on the user's own number, so from_me messages with a
    mention should still be translated. Loop safety comes from the mention
    gate, not from filtering from_me."""
    config = make_config()
    whatsapp = AsyncMock()
    translator = AsyncMock()
    translator.translate_with_routing.return_value = TranslationResult(
        source_lang="en", translation="안녕하세요"
    )
    handler = MessageHandler(config, whatsapp, translator)

    msg = WhapiMessage(
        id="own-1",
        chat_id="family@g.us",
        from_me=True,
        type="text",
        text=MessageText(body="@TranslatorBot Hello"),
    )
    await handler.handle(msg)
    translator.translate_with_routing.assert_awaited_once_with("Hello")
    whatsapp.send_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handler_ignores_no_mention():
    config = make_config()
    whatsapp = AsyncMock()
    translator = AsyncMock()
    handler = MessageHandler(config, whatsapp, translator)

    msg = WhapiMessage(
        id="1",
        chat_id="123@g.us",
        from_me=False,
        type="text",
        text=MessageText(body="just a normal message"),
    )
    await handler.handle(msg)
    whatsapp.send_text.assert_not_awaited()
    translator.translate_with_routing.assert_not_awaited()


@pytest.mark.asyncio
async def test_handler_translates_korean_to_english():
    config = make_config()
    whatsapp = AsyncMock()
    translator = AsyncMock()
    translator.translate_with_routing.return_value = TranslationResult(
        source_lang="ko", translation="What should we eat for dinner?"
    )
    handler = MessageHandler(config, whatsapp, translator)

    msg = WhapiMessage(
        id="msg-1",
        chat_id="family@g.us",
        from_me=False,
        type="text",
        text=MessageText(body="@TranslatorBot 오늘 저녁에 뭐 먹을까?"),
    )
    await handler.handle(msg)

    translator.translate_with_routing.assert_awaited_once_with("오늘 저녁에 뭐 먹을까?")
    whatsapp.send_text.assert_awaited_once()
    kwargs = whatsapp.send_text.await_args.kwargs
    assert kwargs["to"] == "family@g.us"
    assert kwargs["quoted_message_id"] == "msg-1"
    assert kwargs["body"] == "[EN] What should we eat for dinner?"


@pytest.mark.asyncio
async def test_handler_sends_fallback_on_error():
    config = make_config()
    whatsapp = AsyncMock()
    translator = AsyncMock()
    translator.translate_with_routing.side_effect = RuntimeError("boom")
    handler = MessageHandler(config, whatsapp, translator)

    msg = WhapiMessage(
        id="msg-2",
        chat_id="family@g.us",
        from_me=False,
        type="text",
        text=MessageText(body="@TranslatorBot hello"),
    )
    await handler.handle(msg)
    whatsapp.send_text.assert_awaited_once()
    body = whatsapp.send_text.await_args.kwargs["body"]
    assert "unavailable" in body.lower()
