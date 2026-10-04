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

# "|| true" ist hier notwendig: grep gibt Exit-Code 1 zurück, sobald nichts zu
# filtern übrig bleibt (z. B. keine bestehende Crontab, oder die Crontab enthält
# nur unsere eine Zeile - der Normalfall bei einem Solo-VPS). Mit "set -e" +
# "pipefail" würde das Skript sonst an dieser Stelle lautlos abbrechen, bevor
# die neue Cron-Zeile je eingetragen wird - ohne jede Fehlermeldung.
( crontab -l 2>/dev/null | grep -vF "$RUN_SCRIPT" || true; echo "$CRON_LINE" ) | crontab -

INSTALLED="$(crontab -l 2>/dev/null | grep -F "$RUN_SCRIPT" || true)"
if [ -z "$INSTALLED" ]; then
    echo "FEHLER: Cronjob wurde NICHT gefunden nach der Installation. Bitte 'crontab -l' manuell prüfen." >&2
    exit 1
fi

echo "==> Cronjob eingetragen und verifiziert:"
echo "    $INSTALLED"
echo ""
echo "    Prüfen mit:   crontab -l"
echo "    Logs unter:   $PROJECT_DIR/watchlist/cron.log"
