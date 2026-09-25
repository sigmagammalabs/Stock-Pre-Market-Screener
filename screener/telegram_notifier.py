"""Telegram Bot API dispatcher: message formatting and sending."""

from __future__ import annotations

import logging
from datetime import datetime
from html import escape

import pandas as pd
import requests

from .config import Secrets

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LENGTH = 4096


def send_telegram_message(text: str, secrets: Secrets, chat_id: str | None = None) -> bool:
    if not secrets.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN fehlt in der Umgebung (.env). Versand übersprungen.")
        return False

    target_chat_id = chat_id or secrets.telegram_chat_id
    if not target_chat_id:
        logger.error("TELEGRAM_CHAT_ID fehlt (.env oder Parameter). Versand übersprungen.")
        return False

    url = TELEGRAM_API_URL.format(token=secrets.telegram_bot_token)
    payload = {
        "chat_id": target_chat_id,
        "text": text[:MAX_MESSAGE_LENGTH],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info("Telegram-Nachricht erfolgreich gesendet an chat_id=%s", target_chat_id)
            return True
        logger.error("Telegram API Fehler (%s): %s", resp.status_code, resp.text)
        return False
    except requests.exceptions.Timeout:
        logger.error("Telegram-Versand: Timeout beim Verbindungsaufbau.")
        return False
    except requests.exceptions.RequestException as exc:
        logger.error("Telegram-Versand: Netzwerkfehler: %s", exc)
        return False


def _format_row(row: pd.Series) -> str:
    ticker = escape(str(row["Ticker"]))
    price = row["Price"]
    gap = row["Gap%"]
    rvol = row["RVOL"]
    atr = row["ATR"]
    rsi = row["RSI"]
    trend = escape(str(row["Trend"]))
    gap_sign = "+" if gap >= 0 else ""
    return (
        f"<b>{ticker}</b>  ${price}\n"
        f"   Gap: {gap_sign}{gap}%  |  RVOL: {rvol}x  |  ATR: {atr}\n"
        f"   RSI: {rsi}  |  {trend}"
    )


def format_watchlist_message(df: pd.DataFrame, top_n: int = 8, ai_summary: str | None = None) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    lines = [f"🌅 <b>Pre-Market Watchlist</b> — {now}", ""]

    long_df = df[df["Setup"] == "Long Watch"].head(top_n)
    short_df = df[df["Setup"] == "Short Watch"].head(top_n)

    if long_df.empty and short_df.empty:
        lines.append("Keine Treffer für die aktuellen Filterkriterien.")
        return "\n".join(lines)

    if not long_df.empty:
        lines.append(f"🟢 <b>Long Watch</b> ({len(long_df)})")
        for _, row in long_df.iterrows():
            lines.append(_format_row(row))
        lines.append("")

    if not short_df.empty:
        lines.append(f"🔴 <b>Short Watch</b> ({len(short_df)})")
        for _, row in short_df.iterrows():
            lines.append(_format_row(row))
        lines.append("")

    if ai_summary:
        lines.append("🤖 <b>KI-Briefing</b>")
        lines.append(escape(ai_summary))

    message = "\n".join(lines)
    if len(message) > MAX_MESSAGE_LENGTH:
        logger.warning("Nachricht überschreitet %d Zeichen (%d) - wird gekürzt.", MAX_MESSAGE_LENGTH, len(message))
        message = message[: MAX_MESSAGE_LENGTH - 20].rstrip() + "\n…"
    return message
