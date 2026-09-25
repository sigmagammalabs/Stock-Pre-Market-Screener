#!/usr/bin/env bash
# Trägt den täglichen Pre-Market-Scan als Cronjob ein (Mo-Fr, 08:45 Uhr Serverzeit).
# Server-Zeitzone beachten! US-Pre-Market startet ca. 09:00-14:30 Uhr MEZ/MESZ,
# je nach Sommer-/Winterzeit-Differenz zu den USA. Zeit ggf. in der Crontab-Zeile
# unten anpassen, oder Serverzeitzone mit `sudo timedatectl set-timezone Europe/Berlin` setzen.
#
# Nutzung: bash deploy/install_cron.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_SCRIPT="$PROJECT_DIR/deploy/run_scan.sh"
CRON_LINE="45 8 * * 1-5 $RUN_SCRIPT >> $PROJECT_DIR/watchlist/cron.log 2>&1"

chmod +x "$RUN_SCRIPT"

( crontab -l 2>/dev/null | grep -vF "$RUN_SCRIPT" ; echo "$CRON_LINE" ) | crontab -

echo "==> Cronjob eingetragen:"
echo "    $CRON_LINE"
echo ""
echo "    Prüfen mit:   crontab -l"
echo "    Logs unter:   $PROJECT_DIR/watchlist/cron.log"
