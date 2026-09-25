#!/usr/bin/env bash
# Trägt den täglichen Scan als Cronjob ein (Mo-Fr, 08:15 Uhr Berlin-Zeit,
# 45 Min. vor Xetra-Handelsbeginn um 09:00 Uhr).
#
# Server läuft auf Europe/Berlin - Xetra/Euronext-Handelszeiten sind ebenfalls
# in dieser Zeitzone, daher ist hier (anders als beim früheren US-Setup) keine
# Zeitzonen-Umrechnung nötig.
#
# Nutzung: bash deploy/install_cron.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_SCRIPT="$PROJECT_DIR/deploy/run_scan.sh"
CRON_LINE="15 8 * * 1-5 $RUN_SCRIPT >> $PROJECT_DIR/watchlist/cron.log 2>&1"

chmod +x "$RUN_SCRIPT"

( crontab -l 2>/dev/null | grep -vF "$RUN_SCRIPT" ; echo "$CRON_LINE" ) | crontab -

echo "==> Cronjob eingetragen:"
echo "    $CRON_LINE"
echo ""
echo "    Prüfen mit:   crontab -l"
echo "    Logs unter:   $PROJECT_DIR/watchlist/cron.log"
