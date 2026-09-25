"""Optional Groq-powered intent parsing and watchlist briefings.

Fails soft everywhere: if GROQ_API_KEY is missing or any API call raises,
callers get None back and fall back to pure rule-based behavior.
"""

from __future__ import annotations

import json
import logging

from .config import GROQ_MODEL, Secrets

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """\
Du bist ein Intent-Parser für einen Aktien-Screener-Telegram-Bot.
Extrahiere aus der Nachricht des Nutzers ausschließlich ein JSON-Objekt mit exakt diesem Schema:
{
  "action": "scan" | "quote" | "help",
  "filters": {
    "min_rvol": float | null,
    "min_gap_pct": float | null,
    "tickers": [string] | null
  }
}
Regeln:
- "scan": Nutzer möchte den Markt/eine Untergruppe nach Setups durchsuchen.
- "quote": Nutzer fragt nach konkreten, in "tickers" genannten Symbolen.
- "help": Nutzer fragt nach Hilfe/Befehlen oder die Nachricht ist unklar.
- Wenn kein Filter erkennbar ist, setze den jeweiligen Wert auf null.
- Gib ausschließlich valides JSON zurück, keinen Fließtext.
"""

BRIEFING_SYSTEM_PROMPT = """\
Du bist ein erfahrener Trader. Analysiere die übergebenen Kennzahlen der Top-Setups \
und fasse jedes Setup in maximal 2 prägnanten Bulletpoints zusammen \
(Katalysator/Risiko/Level). Antworte kompakt auf Deutsch, ohne Einleitung.
"""


def _get_client(secrets: Secrets):
    if not secrets.groq_api_key:
        return None
    try:
        from groq import Groq

        return Groq(api_key=secrets.groq_api_key)
    except Exception as exc:
        logger.warning("Groq-Client konnte nicht initialisiert werden: %s", exc)
        return None


def parse_intent(user_text: str, secrets: Secrets) -> dict | None:
    client = _get_client(secrets)
    if client is None:
        return None

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=300,
        )
        raw = completion.choices[0].message.content
        parsed = json.loads(raw)
        return _validate_intent(parsed)
    except Exception as exc:
        logger.warning("Groq Intent-Parsing fehlgeschlagen, Fallback auf regelbasiertes Verhalten: %s", exc)
        return None


def _validate_intent(parsed: dict) -> dict | None:
    if not isinstance(parsed, dict):
        return None
    action = parsed.get("action")
    if action not in ("scan", "quote", "help"):
        return None
    filters = parsed.get("filters") or {}
    return {
        "action": action,
        "filters": {
            "min_rvol": filters.get("min_rvol"),
            "min_gap_pct": filters.get("min_gap_pct"),
            "tickers": filters.get("tickers"),
        },
    }


def generate_briefing(top_rows: list[dict], secrets: Secrets) -> str | None:
    client = _get_client(secrets)
    if client is None or not top_rows:
        return None

    try:
        payload = json.dumps(top_rows, ensure_ascii=False)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": BRIEFING_SYSTEM_PROMPT},
                {"role": "user", "content": payload},
            ],
            temperature=0.4,
            max_tokens=500,
        )
        return completion.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("Groq Briefing fehlgeschlagen, Nachricht wird ohne KI-Zusammenfassung versendet: %s", exc)
        return None
