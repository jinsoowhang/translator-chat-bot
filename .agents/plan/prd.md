# Translator Chat Bot — Product Requirements Document

## Problem Statement

In multilingual family group chats, communication suffers when members have different language strengths. Messages get simplified, responses stay short, and full expression is lost. There is no lightweight tool that lets each person write freely in their strongest language and have it automatically translated for others — only when needed.

## Solution

A WhatsApp chatbot that lives in a family group chat and translates messages on demand. The bot is summoned by @mentioning it, detects the source language, and replies with a translation in the configured target language. It stays silent unless called upon.

## User Stories

- **As a bilingual speaker (EN/ES)**, I want to write a message in English or Spanish, @mention the bot, and have it translated to Korean so my parents can read it naturally.
- **As a Korean speaker**, I want to write freely in Korean, @mention the bot, and have it translated to English so my children can read it.
- **As a group member**, I want the bot to stay silent unless I specifically @mention it, so it doesn't clutter the chat.

## Architecture

```
WhatsApp Group Chat  ←→  Whapi.Cloud (gateway)  ←→  FastAPI Server  ←→  Claude API
                                                     (localhost:8000)    (translation)

Cloudflare Tunnel exposes localhost to the internet for webhook delivery.
```

### Message Flow

1. User writes `@TranslatorBot 오늘 저녁에 뭐 먹을까?` in the group
2. Whapi.Cloud receives the message and POSTs a webhook to the bot server
3. Bot server checks: is this a group message with a @mention? If not, ignore.
4. Strips the @mention, detects Korean as the source language
5. Looks up config: Korean → translate to English
6. Calls Claude API with translation prompt
7. Sends a quote-reply back to the group: `[EN] What should we eat for dinner tonight?`

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| WhatsApp Gateway | Whapi.Cloud | Official Meta API doesn't support group chats at small scale. Whapi.Cloud uses linked-device protocol, supports groups, has a free sandbox (150 msgs/day). |
| Bot Server | FastAPI + uvicorn | Async-native, lightweight, ideal for webhook handling. |
| Translation LLM | Claude Sonnet 4.6 | Top-tier translation quality, natural tone, ~$0.50-1.00/month at family chat volume. |
| HTTP Client | httpx | Async HTTP client for Whapi.Cloud API calls. |
| Config | pydantic-settings + YAML | Type-safe env vars (.env) + readable language pair config (config.yaml). |
| Tunnel | Cloudflare Tunnel | Free, persistent subdomain, more reliable than ngrok free tier. |
| Package Manager | uv | Fast, modern Python packaging. |

## Language Configuration

```yaml
language_pairs:
  - source: ["en", "es"]
    target: "ko"
  - source: ["ko"]
    target: "en"

bot_name: "TranslatorBot"
claude_model: "claude-sonnet-4-6-20250514"
```

Translation rules:
- English or Spanish input → Korean output
- Korean input → English output
- Mixed-language messages: translate the full message to the opposite language group
- Bot detects source language automatically (delegated to Claude)

## Reply Format

The bot quote-replies the original message with a language tag prefix:

```
┌─ Replying to Mom ─────────────┐
│ @TranslatorBot 오늘 저녁에     │
│ 뭐 먹을까?                     │
└───────────────────────────────┘

[EN] What should we eat for dinner tonight?
```

## Project Structure

```
translator-chat-bot/
├── .agents/plan/prd.md
├── .claude/CLAUDE.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── config.yaml
├── src/
│   └── translator_bot/
│       ├── __init__.py
│       ├── main.py          # FastAPI app + webhook endpoint
│       ├── config.py         # Settings loader (pydantic-settings + YAML)
│       ├── whatsapp.py       # Whapi.Cloud API client
│       ├── translator.py     # Claude API translation logic
│       ├── handlers.py       # Message processing (mention detection, routing)
│       └── models.py         # Pydantic models for webhook payloads
└── tests/
    ├── test_translator.py
    └── test_handlers.py
```

## Phase 1 — Get It Working

**Goal:** Bot works in the family WhatsApp group chat, translating messages on @mention.

### Implementation Steps

1. **Project scaffolding** — `uv init`, dependencies, directory structure, `.gitignore`, `.env.example`
2. **Configuration module** — Load API keys from `.env`, language pairs from `config.yaml`
3. **Webhook models** — Pydantic models for Whapi.Cloud webhook payloads
4. **WhatsApp client** — Async wrapper for Whapi.Cloud REST API (send messages, quote-reply)
5. **Translation engine** — Claude API integration with a prompt tuned for natural family-chat translation
6. **Message handler** — Core logic: detect @mention → strip it → determine target language → translate → format reply
7. **FastAPI app** — Webhook endpoint + health check, background task processing
8. **Tunnel setup** — Cloudflare Tunnel to expose local server
9. **End-to-end testing** — Test in actual family group chat, refine translation prompt

### Verification

- Health endpoint responds at `GET /health`
- Bot ignores messages without @mention
- Korean → English translation works with natural tone
- English → Korean translation works with appropriate family register
- Spanish → Korean translation works
- Quote-reply with language tag displays correctly in WhatsApp

## Phase 2 — Open Source

**Goal:** Anyone can download the project, provide their own credentials, and run the bot for their own language pairs.

### Key Features

- **Onboarding CLI** — Interactive setup wizard: enter API keys, choose languages, configure bot name
- **Multi-provider support** — Abstracted gateway layer (Whapi.Cloud, GREEN-API) and LLM layer (Claude, OpenAI, Gemini, Ollama)
- **Docker deployment** — `docker compose up` for one-command setup
- **Web dashboard** — Simple config UI as an alternative to YAML editing
- **Documentation** — Setup guide, supported gateways, supported LLMs, troubleshooting

### Phase 1 Design Decisions That Enable Phase 2

- API keys in `.env` (not hardcoded) → easy to swap credentials
- Language pairs in YAML config → easy to customize
- Gateway client as a separate module → easy to add alternative providers
- LLM call as a separate module → easy to add alternative models

## Cost Estimate (Phase 1, Monthly)

| Item | Cost |
|------|------|
| Whapi.Cloud Sandbox | Free (150 msgs/day) |
| Claude API (~1000 translations) | ~$0.50 - $1.00 |
| Cloudflare Tunnel | Free |
| **Total** | **~$0.50 - $1.00/month** |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| WhatsApp account restrictions | Low volume family use is low risk. If issues arise, get a secondary SIM. |
| Whapi.Cloud service changes | Gateway layer is abstracted; GREEN-API is the backup. |
| Claude API outages | Return a friendly "translation unavailable" fallback message. |
| Free tier message limits | 150 msgs/day is generous for family chat. Upgrade to paid ($35/mo) if needed. |
