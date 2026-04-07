"""FastAPI app — webhook endpoint + health check."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from .config import get_bot_config, get_settings
from .handlers import MessageHandler
from .models import WhapiWebhookPayload
from .translator import SmartTranslator, Translator
from .whatsapp import WhapiClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("translator_bot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    bot_config = get_bot_config()

    whatsapp = WhapiClient(token=settings.whapi_token, base_url=settings.whapi_base_url)
    translator = Translator(model=bot_config.claude_model)
    smart = SmartTranslator(translator=translator, config=bot_config)
    handler = MessageHandler(config=bot_config, whatsapp=whatsapp, translator=smart)

    app.state.whatsapp = whatsapp
    app.state.handler = handler
    app.state.bot_config = bot_config
    log.info("Bot ready — responds to @%s", bot_config.bot_name)
    try:
        yield
    finally:
        await whatsapp.aclose()


app = FastAPI(title="Translator Chat Bot", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> dict:
    settings = get_settings()
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    raw = await request.json()
    try:
        payload = WhapiWebhookPayload.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not parse webhook payload: %s", exc)
        return {"status": "ignored"}

    handler: MessageHandler = request.app.state.handler
    for message in payload.messages:
        # Process in background so we ACK the webhook quickly.
        background_tasks.add_task(handler.handle, message)

    return {"status": "accepted", "count": len(payload.messages)}
