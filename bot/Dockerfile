FROM python:3.11-slim

# ffmpeg is required by faster-whisper/ctranslate2 audio decoding pipeline
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \ 
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN mkdir -p /data

CMD ["python", "-m", "app.main"]