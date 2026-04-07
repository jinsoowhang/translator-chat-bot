# Translator Chat Bot

A WhatsApp chatbot that translates messages between languages on demand, designed for multilingual family group chats. Summon it with `@TranslatorBot` in any chat, write in your strongest language, and the bot quote-replies with a natural translation.

> **Status:** Experimental MVP. Currently hardcoded to [Whapi.Cloud](https://whapi.cloud) as the WhatsApp gateway and [Anthropic Claude](https://www.anthropic.com) as the translation engine. Multi-provider support is on the roadmap (see [Roadmap](#roadmap)).

## Why this exists

In multilingual families, communication suffers when members have different language strengths. People simplify their messages, keep responses short, and lose nuance. This bot lets each person write freely in their strongest language and have it translated only when needed — without cluttering the chat the rest of the time.

**Example:** A family with English/Spanish-speaking children and Korean-speaking parents:
- Child writes: `@TranslatorBot Hey mom, what are you up to this weekend?`
- Bot quote-replies: `[KO] 엄마, 이번 주말에 뭐 하세요?`
- Mom writes back: `@TranslatorBot 김치찌개 만들 거야. 너도 와서 같이 먹자`
- Bot quote-replies: `[EN] I'm going to make kimchi stew. Come over and eat together!`

## How it works

```
WhatsApp Group  ←→  Whapi.Cloud  ←→  Cloudflare Tunnel  ←→  FastAPI Server  ←→  Claude
```

1. A user sends a message containing `@TranslatorBot` in a chat the bot's WhatsApp account is in
2. Whapi.Cloud delivers the message to the bot via webhook
3. The bot strips the mention, asks Claude to detect the source language and translate it to the configured target language, in one call
4. The bot quote-replies in the same chat with `[XX] <translation>`

The bot stays silent on any message that doesn't contain its mention, so it never clutters the chat.

## Tech stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.12+ |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Web framework | FastAPI + uvicorn |
| WhatsApp gateway | [Whapi.Cloud](https://whapi.cloud) (linked-device protocol) |
| LLM | Anthropic Claude (via [`claude-agent-sdk`](https://github.com/anthropics/claude-agent-sdk-python) — uses your Claude Code subscription) |
| HTTP client | httpx (async) |
| Config | pydantic-settings (`.env`) + PyYAML (`config.yaml`) |
| Tunnel | Cloudflare Tunnel |

## Quickstart

> Full step-by-step guide in [`docs/SETUP.md`](docs/SETUP.md), including how to get a Whapi.Cloud token, link your WhatsApp number, and configure the webhook tunnel.

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/translator-chat-bot.git
cd translator-chat-bot
uv sync
```

### 2. Configure secrets

```bash
cp .env.example .env
# Open .env and fill in WHAPI_TOKEN
```

You'll need:
- A **Whapi.Cloud** account with a Sandbox channel linked to your WhatsApp number ([guide](docs/SETUP.md#whapi-cloud-setup))
- A **Claude Code** login on this machine (run `claude` once and complete `/login`) — translations will use your Anthropic Max subscription. If you'd rather use the Anthropic API directly, see [Using an API key instead](docs/SETUP.md#using-an-api-key-instead).

### 3. Configure language pairs

Edit `config.yaml`:

```yaml
language_pairs:
  - source: ["en", "es"]
    target: "ko"
  - source: ["ko"]
    target: "en"

bot_name: "TranslatorBot"
claude_model: "claude-sonnet-4-5-20250929"
```

`bot_name` is the magic word users will type after `@`. It does **not** have to match your WhatsApp display name — just pick something memorable.

### 4. Run the server

```bash
uv run uvicorn translator_bot.main:app --host 0.0.0.0 --port 8000
```

You should see:

```
INFO     translator_bot: Bot ready — responds to @TranslatorBot
INFO     Uvicorn running on http://0.0.0.0:8000
```

### 5. Expose it with a tunnel

In another terminal:

```bash
cloudflared tunnel --url http://localhost:8000
```

Copy the `https://<random>.trycloudflare.com` URL it prints and configure it as your webhook URL in the Whapi.Cloud dashboard, with `/webhook` appended:

```
https://<random>.trycloudflare.com/webhook
```

### 6. Test it

From any chat your linked WhatsApp account is in, send:

```
@TranslatorBot 안녕하세요
```

You should see the bot quote-reply within a few seconds.

## Smoke test the translator alone

If you want to test the Claude integration without going through WhatsApp:

```bash
uv run python -m translator_bot.smoketest "오늘 저녁에 뭐 먹을까?"
```

## Project structure

```
translator-chat-bot/
├── src/translator_bot/
│   ├── main.py         # FastAPI app + webhook endpoint
│   ├── config.py       # Settings + language pair config loader
│   ├── whatsapp.py     # Whapi.Cloud REST client
│   ├── translator.py   # Claude-powered translation engine
│   ├── handlers.py     # Message processing and routing
│   ├── models.py       # Pydantic webhook payload models
│   └── smoketest.py    # Standalone translator smoke test
├── tests/              # pytest suite
├── config.yaml         # Language pair definitions
├── .env.example        # Template for secrets
├── docs/SETUP.md       # Detailed setup walkthrough
└── pyproject.toml
```

## Running the tests

```bash
uv run pytest
```

The handler tests mock the translator, so they don't make any real API calls and run in seconds.

## Configuration reference

### `.env`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WHAPI_TOKEN` | ✅ | — | API token from your Whapi.Cloud channel dashboard |
| `WHAPI_BASE_URL` | | `https://gate.whapi.cloud` | Whapi API base URL — change only if you have a custom region endpoint |
| `WEBHOOK_SECRET` | | _empty_ | Optional shared secret. If set, incoming webhooks must include `X-Webhook-Secret` matching this value |
| `HOST` | | `0.0.0.0` | Address uvicorn binds to |
| `PORT` | | `8000` | Port uvicorn binds to |

### `config.yaml`

| Field | Required | Description |
|-------|----------|-------------|
| `language_pairs` | ✅ | List of `{source: [iso codes], target: iso code}` rules. The first pair's target is used as the default if the detected source language doesn't match any rule. |
| `bot_name` | ✅ | The magic word the bot scans for after `@`. Case-insensitive. |
| `claude_model` | ✅ | Model identifier passed to Claude. |
| `language_labels` | | Map of ISO code → display label used in the `[XX]` reply prefix. Defaults to uppercased ISO code. |

## Scope

This project is intentionally minimal: it's a small, self-contained app you can clone and run locally on your own machine for personal/family use. There is no hosted version, no managed deployment, and no production infrastructure to maintain. If you want to keep it running 24/7, that's up to you — `uvicorn` + a tunnel of your choice is all you need.

## Roadmap

This MVP is hardcoded to one gateway and one LLM provider. Planned next steps:

- [ ] **Multi-provider gateway abstraction** — pluggable backends for Whapi.Cloud, GREEN-API, and others
- [ ] **Multi-provider LLM abstraction** — pluggable backends for Claude, OpenAI, Gemini, and Ollama
- [ ] **Onboarding wizard** — interactive `python -m translator_bot.setup` that prompts for credentials and writes `.env`
- [ ] **Docker support** — `docker compose up` for one-command local startup

Contributions and issues welcome.

## Security notes

- **Never commit your `.env` file.** It's gitignored by default — keep it that way.
- **Never paste your `WHAPI_TOKEN` or `ANTHROPIC_API_KEY` in chat, screenshots, or issues.** If you accidentally leak one, regenerate it immediately from the provider dashboard.
- The webhook endpoint is publicly reachable through the tunnel. Set `WEBHOOK_SECRET` and configure it in the Whapi dashboard to reject unauthenticated POSTs.
- The Whapi sandbox plan uses a linked-device session against your personal WhatsApp account. WhatsApp's terms of service prohibit automated use of personal accounts at scale; this project is intended for personal/family use, not commercial automation.

## License

[MIT](LICENSE)
