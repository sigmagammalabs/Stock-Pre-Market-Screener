#!/usr/bin/env bash
# Wrapper für den Cronjob: aktiviert die venv, führt den Scan aus, loggt sauber.
# Wird nicht direkt aufgerufen, sondern von deploy/install_cron.sh eingetragen.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

exec .venv/bin/python main.py scan \
    --universe sp500 \
    --export csv \
    --notify-telegram \
    --ai-briefing
