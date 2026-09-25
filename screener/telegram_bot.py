"""Long-polling Telegram bot: parses free-text commands via Groq and runs scans."""

from __future__ import annotations

import logging
import time

import requests

from . import ai_groq, screener_engine
from .config import ScreenerConfig, Secrets
from .telegram_notifier import format_watchlist_message, send_telegram_message

logger = logging.getLogger(__name__)

GET_UPDATES_URL = "https://api.telegram.org/bot{token}/getUpdates"

HELP_TEXT = (
    "🤖 <b>Pre-Market Screener Bot</b>\n\n"
    "Sende mir z. B.:\n"
    "• \"Scanne nach hohem Volumen und Gap über 3%\"\n"
    "• \"Zeig mir AAPL und NVDA\"\n"
    "• \"Hilfe\"\n\n"
    "Ohne GROQ_API_KEY läuft der Bot im einfachen Kommandomodus:\n"
    "/scan – Standard-Scan\n"
    "/quote TICKER [TICKER ...] – Einzelwerte"
)


def _handle_message(text: str, config: ScreenerConfig, secrets: Secrets) -> str:
    intent = ai_groq.parse_intent(text, secrets)

    if intent is None:
        # Fallback: simple rule-based command parsing.
        stripped = text.strip()
        if stripped.lower().startswith("/quote"):
            tickers = stripped.split()[1:]
            intent = {"action": "quote", "filters": {"tickers": tickers, "min_rvol": None, "min_gap_pct": None}}
        elif stripped.lower().startswith("/scan"):
            intent = {"action": "scan", "filters": {"tickers": None, "min_rvol": None, "min_gap_pct": None}}
        else:
            intent = {"action": "help", "filters": {}}

    action = intent["action"]
    filters = intent.get("filters", {})

    if action == "help":
        return HELP_TEXT

    if action == "quote" and not filters.get("tickers"):
        return "⚠️ Für eine Kursabfrage bitte mindestens einen Ticker nennen, z. B. \"Zeig mir AAPL\"."

    if action in ("scan", "quote"):
        # "quote" ist eine explizite Ticker-Anfrage - Scan-Schwellenwerte (Gap%,
        # RVOL, Mindestpreis/-volumen) werden hier bewusst umgangen, da der
        # Nutzer den Ticker namentlich angefragt hat und ihn sehen möchte,
        # unabhängig davon, ob er die Scan-Kriterien erfüllt.
        override_tickers = filters.get("tickers") if action == "quote" else None
        try:
            df = screener_engine.screen_market(
                config,
                secrets,
                override_tickers=override_tickers,
                min_rvol_override=filters.get("min_rvol"),
                min_gap_pct_override=filters.get("min_gap_pct"),
                enforce_filters=(action == "scan"),
            )
        except Exception as exc:
            logger.exception("Scan im Bot-Modus fehlgeschlagen")
            return f"⚠️ Scan fehlgeschlagen: {exc}"

        ai_summary = None
        if not df.empty:
            top_rows = df.head(3).to_dict(orient="records")
            ai_summary = ai_groq.generate_briefing(top_rows, secrets)

        return format_watchlist_message(df, top_n=config.top_n, ai_summary=ai_summary)

    return HELP_TEXT


def run_listener(config: ScreenerConfig, secrets: Secrets, poll_interval: float = 3.0) -> None:
    if not secrets.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN fehlt - Listener kann nicht gestartet werden.")

    logger.info("Telegram-Bot-Listener gestartet (Poll-Intervall: %.1fs). Strg+C zum Beenden.", poll_interval)
    url = GET_UPDATES_URL.format(token=secrets.telegram_bot_token)
    offset = None

    while True:
        try:
            params = {"timeout": 20}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(url, params=params, timeout=25)
            resp.raise_for_status()
            data = resp.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message") or update.get("edited_message")
                if not message or "text" not in message:
                    continue

                chat_id = message["chat"]["id"]
                text = message["text"]
                logger.info("Nachricht von chat_id=%s: %s", chat_id, text)

                reply = _handle_message(text, config, secrets)
                send_telegram_message(reply, secrets, chat_id=str(chat_id))

        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.RequestException as exc:
            logger.error("Telegram getUpdates fehlgeschlagen: %s", exc)
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Listener durch Nutzer beendet.")
            break
        except Exception:
            logger.exception("Unerwarteter Fehler im Listener-Loop, wird fortgesetzt.")
            time.sleep(poll_interval)
