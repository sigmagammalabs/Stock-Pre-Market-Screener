#!/usr/bin/env bash
# Installiert den Telegram-Listener als systemd-Service (Dauerbetrieb).
# Passe VOR dem Ausführen bei Bedarf die --tickers/--universe Argumente in
# deploy/watchlist-listener.service.template an.
#
# Nutzung: bash deploy/install_listener_service.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="watchlist-listener"
VPS_USER="$(whoami)"

if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "FEHLER: $PROJECT_DIR/.env fehlt. Erst deploy/setup_vps.sh ausführen und .env befüllen." >&2
    exit 1
fi

echo "==> Erzeuge systemd-Unit für User=$VPS_USER, ProjectDir=$PROJECT_DIR"
sed -e "s#__VPS_USER__#${VPS_USER}#g" \
    -e "s#__PROJECT_DIR__#${PROJECT_DIR}#g" \
    "$PROJECT_DIR/deploy/watchlist-listener.service.template" \
    | sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null

echo "==> systemd neu laden und Service aktivieren"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.service"
sudo systemctl restart "${SERVICE_NAME}.service"

echo ""
echo "==> Fertig. Nützliche Befehle:"
echo "    sudo systemctl status ${SERVICE_NAME}"
echo "    sudo journalctl -u ${SERVICE_NAME} -f"
echo "    sudo systemctl restart ${SERVICE_NAME}   # nach Code-Update (git pull)"
