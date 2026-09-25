#!/usr/bin/env bash
# Trägt den täglichen Pre-Market-Scan als Cronjob ein (Mo-Fr, 08:45 Uhr US-Ostküstenzeit).
#
# Die Cron-Uhrzeit unten ist auf Europe/Berlin-Serverzeit kalibriert: Berlin liegt
# die meiste Zeit des Jahres 6 Stunden vor US-Ostküstenzeit (beide Zonen wechseln
# zu leicht unterschiedlichen Terminen in die Sommerzeit, wodurch die Differenz für
# ca. 1-3 Wochen im Frühjahr/Herbst auf 5 Stunden abweicht - für einen taeglichen
# Scan i.d.R. vernachlässigbar). 08:45 Uhr ET => 14:45 Uhr Berlin.
# Läuft der Server in einer anderen Zeitzone, hier oder direkt per
# `sudo timedatectl set-timezone America/New_York` (DST-automatisch, exakt) anpassen.
#
# Nutzung: bash deploy/install_cron.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_SCRIPT="$PROJECT_DIR/deploy/run_scan.sh"
CRON_LINE="45 14 * * 1-5 $RUN_SCRIPT >> $PROJECT_DIR/watchlist/cron.log 2>&1"

chmod +x "$RUN_SCRIPT"

( crontab -l 2>/dev/null | grep -vF "$RUN_SCRIPT" ; echo "$CRON_LINE" ) | crontab -

echo "==> Cronjob eingetragen:"
echo "    $CRON_LINE"
echo ""
echo "    Prüfen mit:   crontab -l"
echo "    Logs unter:   $PROJECT_DIR/watchlist/cron.log"
