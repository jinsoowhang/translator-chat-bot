# Translator Chat Bot

## Overview

WhatsApp translator chatbot for multilingual family communication. Translates messages between English/Spanish and Korean on demand via @mention in a group chat.

## Tech Stack

- **Language:** Python 3.12+
- **Package Manager:** uv
- **Framework:** FastAPI + uvicorn
- **WhatsApp Gateway:** Whapi.Cloud (linked-device protocol)
- **Translation LLM:** Claude Sonnet 4.6 via Anthropic SDK
- **Config:** pydantic-settings (.env) + PyYAML (config.yaml)
- **HTTP Client:** httpx (async)
- **Tunnel:** Cloudflare Tunnel

## Development

```bash
# Install dependencies
uv sync

# Run dev server
uv run uvicorn src.translator_bot.main:app --reload --port 8000

# Run tests
uv run pytest
```

## Project Structure

- `src/translator_bot/main.py` — FastAPI app entry point, webhook endpoint
- `src/translator_bot/config.py` — Settings and language pair configuration
- `src/translator_bot/whatsapp.py` — Whapi.Cloud API client
- `src/translator_bot/translator.py` — Claude API translation logic
- `src/translator_bot/handlers.py` — Message processing and routing
- `src/translator_bot/models.py` — Pydantic webhook payload models
- `config.yaml` — Language pair definitions
- `.env` — API keys (never commit)

## Key Decisions

- Bot only responds when @mentioned — stays silent otherwise
- Reply format: quote-reply + language tag (e.g. `[EN]`, `[KO]`)
- Translation prompt prioritizes natural conversational tone over literal accuracy
- Gateway and LLM layers kept modular for Phase 2 open-source flexibility
