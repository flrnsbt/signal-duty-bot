# Signal Duty Bot

A fully self-hosted, no-cost, no-third-party-API Signal bot for a small group
of people. Everything runs on your own machine. Anyone registered as a
member can:

- `!onduty` / `!offduty` — declare themselves on call
- Message the bot directly — the message gets forwarded to whoever is on duty
- Send a voice message — it's transcribed locally (faster-whisper) and
  summarized by a small local LLM (Ollama), then the transcript + summary +
  original audio are forwarded to the on-duty person

Three containers, wired together with Docker Compose:

- **signal-api** — [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api),
  open-source, self-hosted, handles the actual Signal protocol (this is the
  only way for any bot to talk to Signal — it's not a paid service, just
  software you run yourself)
- **ollama** — [Ollama](https://ollama.com), runs a small open-weight LLM
  locally for summarization, no API key, no cost, no data leaving your
  machine
- **bot** — the Python service in this repo containing all the logic
  (forwarding, faster-whisper transcription, calling Ollama)

Nothing here calls out to Anthropic, OpenAI, or any paid API. The only
network access the bot needs at runtime is to your own containers.

## 1. Get a Signal number for the bot

You need a phone number the bot can own on Signal — either:

**Option A: Register a new number** (needs a number that can receive an SMS/call for verification, not currently used on another Signal device)

```bash
docker compose up -d signal-api
curl -X POST 'http://localhost:8080/v1/register/+15551234567'
# you'll receive an SMS/call with a code
curl -X POST 'http://localhost:8080/v1/register/+15551234567/verify/123456'
```

**Option B: Link as a secondary device to an existing number** (like linking Signal Desktop)

```bash
docker compose up -d signal-api
curl 'http://localhost:8080/v1/qrcodelink?device_name=duty-bot' -o link.png
# open link.png, scan with Signal app -> Settings -> Linked Devices -> Link New Device
```

Full details: https://github.com/bbernhard/signal-cli-rest-api

## 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:
- `SIGNAL_NUMBER` — the number you registered/linked above
- `ADMIN_NUMBERS` — your number(s), comma-separated; admins can add/remove members and are auto-registered as members on first boot
- `OLLAMA_MODEL` — which local model to use (default `llama3.2:3b`, ~2GB, runs fine on CPU). Other good small options: `qwen2.5:3b`, `phi3:mini`
- `WHISPER_MODEL_SIZE` — `small` is a solid CPU default; bump to `medium`/`large-v3` if you have a GPU (set `WHISPER_DEVICE=cuda`)

## 3. Run

```bash
docker   bot:
    build: ./bot
    container_name: duty-bot
    env_file:
      - .env
    depends_on:
      - signal-api
      - ollama
    volumes:
      -  bot:
    build: ./bot
    container_name: duty-bot
    env_file:
      - .env
    depends_on:
      - signal-api
      - ollama
    volumes:
      -  bot:
    build: ./bot
    container_name: duty-bot
    env_file:
      - .env
    depends_on:
      - signal-api
      - ollama
    volumes:
      - bot-data:/data          # sqlite db + tmp audio files
      - whisper-cache:/root/.cache/huggingface   # persist downloaded whisper model
    restart: unless-stopped
    networks:
      - duty-net bot-data:/data          # sqlite db + tmp audio files
      - whisper-cache:/root/.cache/huggingface   # persist downloaded whisper model
    restart: unless-stopped
    networks:
      - duty-net bot-data:/data          # sqlite db + tmp audio files
      - whisper-cache:/root/.cache/huggingface   # persist downloaded whisper model
    restart: unless-stopped
    networks:
      - duty-netcompose up -d --build

# One-time: pull the local LLM into the ollama container
docker compose exec ollama ollama pull llama3.2:3b   # match OLLAMA_MODEL in .env

docker compose logs -f bot
```

## 4. Add your group

Message the bot's Signal number from an admin's phone:

```
!add Alice +15559990001
!add Bob +15559990002
```

Everyone in the group can now message the bot directly.

## Usage

| Command      | Effect                                      |
|--------------|----------------------------------------------|
| `!onduty`    | You become the on-duty person                |
| `!offduty`   | You stop being on-duty                       |
| `!status`    | Shows who's currently on duty                |
| `!members`   | Lists registered members                     |
| `!add`/`!remove` | Admin-only member management             |

Any plain-text message a member sends to the bot is forwarded to whoever is
on duty (with the sender's name prefixed). Any voice message triggers
transcription + AI summary, forwarded to the on-duty person along with the
original audio clip.

## Notes & things to adapt

- **Security**: only phone numbers in the `members` table are acted on;
  everyone else is silently ignored. Keep `ADMIN_NUMBERS` tight.
- **Persistence**: `signal-data`, `bot-data`, and `whisper-cache` are Docker
  volumes — your linked device, member list, on-duty state, and downloaded
  Whisper model all survive restarts/rebuilds.
- **Group chats**: this implementation forwards based on 1:1 DMs to the bot.
  If you'd rather have everyone talk in one Signal *group* and have the bot
  watch that group, the `envelope.dataMessage.groupInfo` field (present in
  signal-cli-rest-api envelopes) can be checked in `handle_envelope` to scope
  behavior to a specific group ID — ask if you'd like that variant.
- **Multiple people on duty at once**: currently one on-duty person at a
  time (last `!onduty` wins). Easy to extend `db.py`/`main.py` to a list if
  you want fan-out to several people simultaneously.
- **Costs**: $0. Whisper and the LLM both run locally on your CPU/RAM (or
  GPU if you enable it in `docker-compose.yml`). No API keys, no per-request
  charges, no data sent off your machine.
- **RAM**: budget roughly 2-4GB for a `small` Whisper model plus a `3b`
  Ollama model running together. If your host is tight on memory, drop to
  `WHISPER_MODEL_SIZE=base` and/or a smaller Ollama model.
