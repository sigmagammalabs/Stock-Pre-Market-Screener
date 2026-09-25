#!/usr/bin/env bash
# Einmaliges Setup auf einem frischen Ubuntu/Debian Hetzner VPS.
# Ausführen als der Nutzer, der den Screener später betreiben soll (nicht root),
# aber mit sudo-Rechten fürs Paketinstallieren.
#
# Nutzung:
#   git clone https://github.com/sigmagammalabs/Stock-Pre-Market-Screener.git
#   cd Stock-Pre-Market-Screener
#   bash deploy/setup_vps.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "==> System-Pakete aktualisieren und Python/venv installieren"
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git

echo "==> Virtuelle Umgebung anlegen (.venv)"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "==> Dependencies installieren"
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "==> .env aus .env.example erstellen (bitte danach befüllen!)"
    cp .env.example .env
    echo "    -> nano .env  (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GROQ_API_KEY eintragen)"
else
    echo "==> .env existiert bereits, wird nicht überschrieben"
fi

mkdir -p watchlist

echo ""
echo "==> Setup abgeschlossen. Nächste Schritte:"
echo "    1. .env befüllen: nano $PROJECT_DIR/.env"
echo "    2. Testlauf:      .venv/bin/python main.py scan --universe custom --tickers AAPL,NVDA --min-gap-pct 0.1"
echo "    3. systemd-Service für den Telegram-Listener einrichten: deploy/install_listener_service.sh"
echo "    4. Cronjob für den täglichen Scan einrichten: deploy/install_cron.sh"
