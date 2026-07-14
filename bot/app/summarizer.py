import logging

import httpx

from . import config

log = logging.getLogger("summarizer")

SYSTEM_PROMPT = (
    "You summarize short voice-message transcripts sent to an on-call duty bot in French. "
    "Produce a concise summary (minimum sentences possible) capturing the key point, any "
    "requested action, and urgency if apparent. Plain text, no markdown, no preamble or commentary."
)


def summarize(transcript: str) -> str:
    if not transcript.strip():
        return "(Aucun contenu detecte dans ce message vocal.)"

    url = f"{config.OLLAMA_URL}/api/generate"
    body = {
        "model": config.OLLAMA_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": transcript,
        "stream": False,
    }
    try:
        resp = httpx.post(url, json=body, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception:
        log.exception("Local LLM summarization failed")
        return "(Resume par IA locale indisponible. Veuillez contacter l'administrateur.)"
