"""Standalone smoke test for the translator.

Calls Translator + SmartTranslator directly — no FastAPI, no Whapi.Cloud.
Use this to confirm claude-agent-sdk subscription auth is working before
wiring up the webhook plumbing.

Usage:
    uv run python -m translator_bot.smoketest "오늘 저녁에 뭐 먹을까?"
    uv run python -m translator_bot.smoketest "Hola mamá, ¿cómo estás?"
"""
from __future__ import annotations

import asyncio
import sys

from .config import get_bot_config
from .translator import SmartTranslator, Translator


async def main(text: str) -> int:
    config = get_bot_config()
    translator = Translator(model=config.claude_model)
    smart = SmartTranslator(translator=translator, config=config)

    print(f"Input:        {text}")
    print(f"Bot config:   model={config.claude_model}, pairs={[(p.source, p.target) for p in config.language_pairs]}")
    print("Translating...")

    try:
        result = await smart.translate_with_routing(text)
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ Translation failed: {type(exc).__name__}: {exc}")
        return 1

    target = config.target_for(result.source_lang) or "?"
    print()
    print(f"Source lang:  {result.source_lang}")
    print(f"Target lang:  {target}")
    print(f"Translation:  {result.translation}")
    print(f"\nReply preview: [{config.label(target)}] {result.translation}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m translator_bot.smoketest \"<text to translate>\"")
        sys.exit(2)
    sys.exit(asyncio.run(main(" ".join(sys.argv[1:]))))
