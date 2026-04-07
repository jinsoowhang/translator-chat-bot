# Setup Guide

This guide walks you through getting the translator bot running end-to-end. It assumes you already cloned the repo and ran `uv sync`.

## Overview

You'll set up four pieces in order:

1. **Whapi.Cloud account** — the WhatsApp gateway
2. **Claude authentication** — translation engine
3. **Local server** — the bot itself
4. **Public tunnel** — so Whapi can reach the bot

Total time: ~20 minutes if everything goes smoothly.

---

## 1. Whapi.Cloud setup

[Whapi.Cloud](https://whapi.cloud) uses the WhatsApp linked-device protocol (the same one WhatsApp Web uses) to send and receive messages on behalf of a real WhatsApp account.

### 1.1 Create an account

1. Go to https://whapi.cloud and sign up
2. Verify your email if prompted

### 1.2 Create a sandbox channel

A "channel" represents one linked WhatsApp account.

1. From the dashboard, click **Add channel** (or **+ New channel**)
2. Pick the **Sandbox** plan — it's free (150 messages/day, no card required)
3. Give the channel a label like `family-translator`
4. Click **Launch channel**

### 1.3 Link your WhatsApp number

1. In the channel dashboard, click **Get QR** / **Authorize** / **Link device**
2. A QR code appears in your browser
3. On your phone, open WhatsApp:
   - **iOS**: Settings → Linked devices → Link a device
   - **Android**: ⋮ menu → Linked devices → Link a device
4. Scan the QR code
5. Wait a few seconds — the dashboard should flip to **Connected** with a green status

> **Note:** The QR code expires in ~30 seconds. If it greys out before you scan, click refresh.

### 1.4 Copy the API token

1. In the channel dashboard, find the **Token** field (usually under Settings or API)
2. Copy it to your clipboard

> ⚠️ **Treat this token like a password.** Anyone with it can send and read messages on your linked WhatsApp account.

### 1.5 Save the token to `.env`

```bash
cp .env.example .env
```

Open `.env` in your editor and set:

```
WHAPI_TOKEN=<paste-your-token-here>
```

Or, to avoid having the token visible in your shell history:

```bash
read -s -p "Paste Whapi token: " TOKEN && echo
sed -i "s|^WHAPI_TOKEN=.*|WHAPI_TOKEN=$TOKEN|" .env
unset TOKEN
```

---

## 2. Claude authentication

The bot uses [`claude-agent-sdk`](https://github.com/anthropics/claude-agent-sdk-python) for translations. By default, it authenticates using your local Claude Code login (your Anthropic Max subscription) — meaning translations bill against Max instead of an API account.

### Option A: Use your Claude Code subscription (recommended for personal use)

1. Install Claude Code if you haven't already: https://docs.claude.com/en/docs/claude-code
2. Run `claude` once and complete `/login` in the browser
3. Credentials persist in `~/.claude/` and the bot will pick them up automatically

No `ANTHROPIC_API_KEY` needs to be set in `.env`.

### Using an API key instead

If you'd rather use the Anthropic API directly (e.g., on a headless VPS where interactive OAuth is awkward), you can swap the SDK back to `anthropic` and set `ANTHROPIC_API_KEY` in `.env`. The current `translator.py` uses `claude-agent-sdk`; swapping is a small refactor — see `src/translator_bot/translator.py` for the integration point.

---

## 3. Run the bot locally

```bash
uv run uvicorn translator_bot.main:app --host 0.0.0.0 --port 8000
```

You should see:

```
INFO     Started server process [...]
INFO     translator_bot: Bot ready — responds to @TranslatorBot
INFO     Application startup complete.
INFO     Uvicorn running on http://0.0.0.0:8000
```

In a second terminal, verify health:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

Leave the uvicorn terminal running for the rest of the guide.

---

## 4. Public tunnel with Cloudflare

Whapi.Cloud needs a public HTTPS URL to deliver webhooks to. The simplest free option is a Cloudflare Quick Tunnel — no account required.

### 4.1 Install `cloudflared`

On Debian/Ubuntu (including WSL):

```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
rm cloudflared.deb
cloudflared --version
```

For other platforms, see the [official install docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/).

### 4.2 Start the tunnel

In a new terminal:

```bash
cloudflared tunnel --url http://localhost:8000
```

After a few seconds you'll see a banner with a URL like:

```
https://random-words-1234.trycloudflare.com
```

Copy that URL. Your full webhook URL is:

```
https://random-words-1234.trycloudflare.com/webhook
```

> **Quick tunnels are ephemeral.** Every time you restart `cloudflared` you get a new random URL and have to update Whapi. Fine for testing — for production, use a [named Cloudflare tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) with your own domain.

### 4.3 Verify it's reachable

In a third terminal:

```bash
curl https://random-words-1234.trycloudflare.com/health
# {"status":"ok"}
```

---

## 5. Configure Whapi to send webhooks

1. Go back to your Whapi.Cloud channel dashboard
2. Open **Settings** → **Webhooks**
3. Set the URL to your full webhook URL (with `/webhook` at the end)
4. Check **Persistent webhook** so Whapi retries on transient failures
5. Leave all **Auto Download** boxes unchecked (we only handle text)
6. Save / Apply

If the dashboard exposes an "Events" or "Mode" section, make sure incoming **messages** are enabled. The default settings work for most channels.

---

## 6. Test end-to-end

Send a WhatsApp message containing the bot's mention to any chat your linked account is in. With the default config:

```
@TranslatorBot 안녕하세요
```

Watch the uvicorn terminal for:

```
INFO     ...:... - "POST /webhook HTTP/1.1" 200 OK
INFO     translator_bot.handlers: Translating message ... from chat ...
```

The first translation has a noticeable cold-start (30–60s) because `claude-agent-sdk` spawns the Claude Code CLI as a subprocess. Subsequent translations are much faster.

You should then see the bot quote-reply in the chat with `[EN] Hello`.

---

## Troubleshooting

### `POST /webhook` never appears in the uvicorn terminal

- Verify the tunnel terminal still shows `Registered tunnel connection`
- Verify `curl https://<your-tunnel>/health` returns `200 OK`
- Verify the URL in Whapi's dashboard ends in `/webhook`
- Try sending a message **from a different account** — some Whapi configs don't deliver self-sent messages by default

### Bot acknowledges the webhook but never replies

- Check the uvicorn terminal for tracebacks
- Verify your `WHAPI_TOKEN` is correct (a 401/403 will show in the logs)
- If the translator hangs, your Claude Code subscription may not be authenticated — run `claude` interactively and complete `/login`

### Bot replies but the translation is wrong language

- Check `config.yaml`'s `language_pairs` — the first pair's target is used as the default fallback
- The translator detects the source language via Claude; if your message is very short or mixed-language, detection may guess wrong

### `from_me` messages aren't being processed

- Confirm Whapi is configured to deliver outgoing messages too
- Confirm you're running the latest version of `handlers.py` — older versions filtered `from_me` messages

---

## Next steps

- Explore `config.yaml` to customize language pairs and the bot name
- Set `WEBHOOK_SECRET` in `.env` and Whapi's dashboard for an extra layer of webhook auth
- See the [Roadmap in the README](../README.md#roadmap) for planned multi-provider support and Docker deployment
