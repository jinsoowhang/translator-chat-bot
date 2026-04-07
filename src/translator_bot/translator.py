"""Claude-powered translator using claude-agent-sdk.

Authentication uses your local Claude Code login (Anthropic Max subscription)
rather than an API key, so translations bill against Max instead of API credit.

We ask Claude to detect the source language AND produce a natural translation
in one call, returning a compact JSON object — keeps latency low and gives
us tone-aware translations.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    query,
)

from .config import BotConfig


SYSTEM_PROMPT = """You are a translator for a family group chat. Your job is to:

1. Detect the source language of the user's message (return an ISO 639-1 code like "en", "es", "ko").
2. Translate it into the requested target language with a NATURAL, CONVERSATIONAL tone — the way a family member would actually speak, not a literal word-for-word translation.
3. Preserve emotional nuance, jokes, endearments, and informal register. When translating to Korean, use appropriate polite/informal register based on the original tone.
4. Do NOT add explanations, notes, or alternatives. Output the translation only.

Respond with ONLY a JSON object in this exact shape, no code fences, no prose:
{"source_lang": "<iso-code>", "translation": "<translated text>"}"""


# Block all default Claude Code tools — translation is pure text-in/text-out,
# we never want it spawning Read/Bash/etc.
_DISALLOWED_TOOLS = [
    "Bash", "Read", "Write", "Edit", "Glob", "Grep",
    "WebFetch", "WebSearch", "Task", "TodoWrite", "NotebookEdit",
]


@dataclass
class TranslationResult:
    source_lang: str
    translation: str


class Translator:
    def __init__(self, model: str) -> None:
        self._options = ClaudeAgentOptions(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            max_turns=1,
            disallowed_tools=_DISALLOWED_TOOLS,
        )

    async def translate(self, text: str, target_lang: str) -> TranslationResult:
        prompt = (
            f"Target language: {target_lang}\n"
            f"Message to translate:\n{text}"
        )
        chunks: list[str] = []
        async for message in query(prompt=prompt, options=self._options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
        raw = "".join(chunks).strip()
        if not raw:
            raise RuntimeError("Empty response from Claude Agent SDK")
        data = _parse_json(raw)
        return TranslationResult(
            source_lang=str(data.get("source_lang", "")).lower(),
            translation=str(data.get("translation", "")).strip(),
        )


def _parse_json(raw: str) -> dict:
    """Best-effort JSON parse — strips code fences if Claude adds them."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


class SmartTranslator:
    """Wraps Translator with BotConfig-driven target language routing.

    If the source language doesn't match any configured pair, we fall back to
    the first pair's target (best guess for family use).
    """

    def __init__(self, translator: Translator, config: BotConfig) -> None:
        self._translator = translator
        self._config = config

    async def translate_with_routing(self, text: str) -> TranslationResult:
        # First pass: guess a target using the first pair, then re-route if
        # the detected source suggests a different pair.
        default_target = self._config.language_pairs[0].target
        first = await self._translator.translate(text, default_target)
        routed_target = self._config.target_for(first.source_lang)
        if routed_target and routed_target != default_target:
            return await self._translator.translate(text, routed_target)
        return first
