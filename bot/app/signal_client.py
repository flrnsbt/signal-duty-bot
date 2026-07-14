import base64
import json
import logging

import httpx
import websockets

from . import config

log = logging.getLogger("signal_client")


def _ws_url() -> str:
    base = config.SIGNAL_API_URL.replace("http://", "ws://").replace("https://", "wss://")
    return f"{base}/v1/receive/{config.SIGNAL_NUMBER}"


async def listen():
    """Yields parsed Signal envelopes as they arrive, reconnecting on drop."""
    url = _ws_url()
    while True:
        try:
            async with websockets.connect(url, ping_interval=30, ping_timeout=30) as ws:
                log.info("Connected to signal-cli-rest-api websocket")
                async for raw in ws:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    envelope = payload.get("envelope")
                    if envelope:
                        yield envelope
        except Exception as exc:  # noqa: BLE001 - reconnect on any transient failure
            log.warning("Websocket connection lost (%s); reconnecting in 5s", exc)
            import asyncio

            await asyncio.sleep(5)


def send_message(recipient: str, text: str, attachments_b64: list[str] | None = None):
    url = f"{config.SIGNAL_API_URL}/v2/send"
    body = {
        "message": text,
        "number": config.SIGNAL_NUMBER,
        "recipients": [recipient],
    }
    if attachments_b64:
        body["base64_attachments"] = attachments_b64
    resp = httpx.post(url, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()


def download_attachment(attachment_id: str) -> bytes:
    url = f"{config.SIGNAL_API_URL}/v1/attachments/{attachment_id}"
    resp = httpx.get(url, timeout=120)
    resp.raise_for_status()
    return resp.content


def attachment_to_base64_note(file_bytes: bytes, content_type: str) -> str:
    """Formats bytes the way /v2/send expects: 'data:<mime>;filename=<name>;base64,<data>'."""
    encoded = base64.b64encode(file_bytes).decode()
    return f"data:{content_type};base64,{encoded}"
