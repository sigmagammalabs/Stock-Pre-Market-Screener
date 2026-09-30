# syntax=docker/dockerfile:1
#
# Image fuer den headless Betrieb auf dem VPS (Docker/Portainer).
#
#   docker build -t premarket-screener .
#   docker run --rm --env-file .env -v "$PWD/watchlist:/app/watchlist" \
#              premarket-screener scan --universe custom --tickers SAP.DE,SIE.DE --min-gap-pct 0.1
#
# Auf dem VPS laeuft "main.py listen" als Dauerprozess; der taegliche Scan wird
# per "docker exec" im selben Container gestartet. Secrets kommen zur Laufzeit
# als Umgebungsvariablen, nie ins Image.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Europe/Berlin

# python:*-slim bringt keine Zeitzonen-Datenbank mit - ohne tzdata wird
# TZ=Europe/Berlin still ignoriert und alles laeuft in UTC.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Abhaengigkeiten zuerst -- bleibt bei Codeaenderungen im Build-Cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY screener/ ./screener/

# Unprivilegierter Nutzer; das Ausgabeverzeichnis gehoert ihm.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/watchlist \
    && chown -R app:app /app
USER app

# Frueher Fehlschlag beim Build, falls ein Modul oder eine Abhaengigkeit fehlt.
RUN python -c "import main"

ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
