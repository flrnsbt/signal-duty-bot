import os


def _split_numbers(raw: str) -> set[str]:
    return {n.strip() for n in raw.split(",") if n.strip()}


SIGNAL_NUMBER = os.environ["SIGNAL_NUMBER"]
SIGNAL_API_URL = os.environ.get("SIGNAL_API_URL", "http://signal-api:8080")

ADMIN_NUMBERS = _split_numbers(os.environ.get("ADMIN_NUMBERS", ""))

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

DB_PATH = os.environ.get("DB_PATH", "/data/duty_bot.db")
TMP_AUDIO_DIR = "/data/tmp_audio"

KOKORO_VOICE = os.environ.get("KOKORO_VOICE", "f_remy")
KOKORO_SPEED = float(os.environ.get("KOKORO_SPEED", 1.0))