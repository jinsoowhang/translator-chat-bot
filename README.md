# Translator Chat Bot

A WhatsApp bot for group chats where people speak different languages. Mention `@TranslatorBot`, write in whatever language you're comfortable with, and it quote-replies with the translation.

> **Status:** Experimental MVP. Currently hardcoded to [Whapi.Cloud](https://whapi.cloud) as the WhatsApp gateway and [Anthropic Claude](https://www.anthropic.com) as the translation engine. Multi-provider support is on the roadmap (see [Roadmap](#roadmap)).

## Why this exists

When a group chat has members with different language strengths, communication flattens out. People shorten their messages, skip the nuance, or just stop replying. This bot lets everyone write in the language they actually think in, and only translates when someone asks, so it stays out of the way the rest of the time.

Families are the most common case, but it works for any group — friend chats, work channels, expat communities, gaming clans.

**Example:** A family with English/Spanish-speaking children and Korean-speaking parents:
- Child writes: `@TranslatorBot Hey mom, what are you up to this weekend?`
- Bot quote-replies: `[KO] 엄마, 이번 주말에 뭐 하세요?`
- Mom writes back: `@TranslatorBot 김치찌개 만들 거야. 너도 와서 같이 먹자`
- Bot quote-replies: `[EN] I'm going to make kimchi stew. Come over and eat together!`

## How it works

```
Inbound:  WhatsApp Group  →  Whapi.Cloud  →  Cloudflare Tunnel  →  FastAPI  →  Claude
Outbound: FastAPI         →  Whapi.Cloud REST  →  WhatsApp Group
```

1. A user sends a message containing `@TranslatorBot` in a chat the bot's WhatsApp account is in
2. Whapi.Cloud delivers the message to the bot via webhook
3. The bot strips the mention and sends it to Claude, which detects the source language and translates it in a single call
4. The bot quote-replies in the same chat via Whapi's REST API with `[XX] <translation>`

Without the mention, the bot says nothing.

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

**Prerequisites:** Python 3.12+ (uv will install it for you), [`uv`](https://github.com/astral-sh/uv), and [`cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) (no Cloudflare account needed for quick tunnels — `brew install cloudflared` or your distro equivalent).

### 1. Clone and install

```bash
git clone https://github.com/jinsoowhang/translator-chat-bot.git
cd translator-chat-bot
uv sync
```

### 2. Configure secrets

```bash
cp .env.example .env
```

A minimal `.env` only needs your Whapi token:

```bash
WHAPI_TOKEN=your_whapi_token_here
# Optional:
# WEBHOOK_SECRET=some-shared-secret
# WHAPI_BASE_URL=https://gate.whapi.cloud
# HOST=0.0.0.0
# PORT=8000
```

You'll need:
- A **Whapi.Cloud** account with a Sandbox channel linked to your WhatsApp number ([guide](docs/SETUP.md#whapi-cloud-setup))
- A **Claude Code** login on this machine (install [Claude Code](https://docs.claude.com/claude-code), then run `claude` once and complete `/login`). Translations use your Claude subscription. To use an Anthropic API key instead, see [Using an API key](docs/SETUP.md#using-an-api-key-instead).

### 3. Configure language pairs

Edit `config.yaml`:

```yaml
language_pairs:
  - source: ["en", "es"]
    target: "ko"
  - source: ["ko"]
    target: "en"

bot_name: "TranslatorBot"
claude_model: "claude-sonnet-4-5-20250929"  # alias "claude-sonnet-4-5" also works
```

`bot_name` is what users type after `@`. It doesn't have to match your WhatsApp display name — pick something memorable.

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

Copy the `https://<random>.trycloudflare.com` URL it prints and configure it as your webhook URL in the Whapi.Cloud dashboard (Settings → Webhooks), with `/webhook` appended:

```
https://<random>.trycloudflare.com/webhook
```

Subscribe to the **`messages`** event (POST). That's the only event the bot consumes.

### 6. Test it

From any chat your linked WhatsApp account is in, send:

```
@TranslatorBot 안녕하세요
```

You should see the bot quote-reply within a few seconds.

## Smoke test the translator alone

If you want to test the Claude integration without going through WhatsApp (only needs Claude auth, no `WHAPI_TOKEN` required):

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
| `bot_name` | ✅ | What the bot scans for after `@`. Case-insensitive. |
| `claude_model` | ✅ | Model identifier passed to Claude. |
| `language_labels` | | Map of ISO code → display label used in the `[XX]` reply prefix. Defaults to uppercased ISO code. |

## Scope

Intentionally small. Clone it, run it on your own machine, done. No hosted version, no managed deployment. If you want to keep it running 24/7, that's up to you — `uvicorn` + a tunnel of your choice is all you need.

## Roadmap

Currently hardcoded to one gateway and one LLM. Next up:

- [ ] **Multi-provider gateway abstraction** — pluggable backends for Whapi.Cloud, GREEN-API, and others
- [ ] **Multi-provider LLM abstraction** — pluggable backends for Claude, OpenAI, Gemini, and Ollama
- [ ] **Onboarding wizard** — interactive `python -m translator_bot.setup` that prompts for credentials and writes `.env`
- [ ] **Docker support** — `docker compose up` for one-command local startup

Contributions and issues welcome.

## Security notes

- **Never commit your `.env` file.** It's gitignored by default — keep it that way.
- **Never paste your `WHAPI_TOKEN` or `ANTHROPIC_API_KEY` in chat, screenshots, or issues.** If you accidentally leak one, regenerate it immediately from the provider dashboard.
- The webhook endpoint is publicly reachable through the tunnel. Set `WEBHOOK_SECRET` and configure it in the Whapi dashboard to reject unauthenticated POSTs.
- The Whapi sandbox plan uses a linked-device session against your personal WhatsApp account. WhatsApp's terms of service prohibit automated use of personal accounts at scale; this project is intended for personal and small-group use, not commercial automation.

## License

[MIT](LICENSE)
