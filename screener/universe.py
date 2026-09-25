"""Ticker universe resolution (S&P 500 / NASDAQ 100 / custom)."""

from __future__ import annotations

import io
import logging

import requests

from .config import UniverseName

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PreMarketScreener/1.0)"}

_SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_NASDAQ100_WIKI_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"

# Small static fallback lists used only when live retrieval fails (e.g. no
# network access). Not exhaustive - just enough to keep the tool usable offline.
_SP500_FALLBACK = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "BRK-B", "JPM", "V", "UNH",
    "XOM", "JNJ", "PG", "MA", "HD", "MRK", "AVGO", "COST", "ABBV", "PEP",
    "KO", "WMT", "BAC", "CRM", "TMO", "MCD", "CSCO", "ACN", "ABT", "ADBE",
    "LIN", "DHR", "NFLX", "TXN", "WFC", "PM", "NEE", "ORCL", "DIS", "VZ",
]

_NASDAQ100_FALLBACK = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "NVDA", "AVGO", "COST", "PEP",
    "ADBE", "CSCO", "NFLX", "AMD", "TMUS", "INTC", "QCOM", "TXN", "AMGN", "INTU",
    "HON", "SBUX", "GILD", "ADP", "BKNG", "MDLZ", "ADI", "VRTX", "REGN", "PANW",
    "LRCX", "MU", "ISRG", "PYPL", "SNPS", "CDNS", "KLAC", "MAR", "ORLY", "CSX",
]


def _tickers_from_wikipedia(url: str, symbol_column_candidates: list[str]) -> list[str]:
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    # Wrapped in StringIO: passing the raw HTML string directly can make
    # pandas misdetect it as a file path on some pandas/lxml combinations.
    tables = __import__("pandas").read_html(io.StringIO(resp.text))
    for table in tables:
        for col in symbol_column_candidates:
            if col in table.columns:
                symbols = table[col].astype(str).str.strip().tolist()
                return [s.replace(".", "-") for s in symbols if s and s.lower() != "nan"]
    raise ValueError(f"No matching symbol column found at {url}")


def get_tickers(universe: UniverseName, custom_tickers: list[str] | None = None) -> list[str]:
    if universe == UniverseName.CUSTOM:
        if not custom_tickers:
            raise ValueError("universe=custom requires a non-empty custom_tickers list")
        return [t.strip().upper() for t in custom_tickers if t.strip()]

    if universe == UniverseName.SP500:
        try:
            return sorted(set(_tickers_from_wikipedia(_SP500_WIKI_URL, ["Symbol"])))
        except Exception as exc:
            logger.warning(
                "Could not fetch S&P 500 list from Wikipedia (%s: %s); using static fallback.",
                type(exc).__name__, str(exc)[:200],
            )
            return list(_SP500_FALLBACK)

    if universe == UniverseName.NASDAQ100:
        try:
            return sorted(set(_tickers_from_wikipedia(_NASDAQ100_WIKI_URL, ["Ticker", "Symbol"])))
        except Exception as exc:
            logger.warning(
                "Could not fetch NASDAQ-100 list from Wikipedia (%s: %s); using static fallback.",
                type(exc).__name__, str(exc)[:200],
            )
            return list(_NASDAQ100_FALLBACK)

    raise ValueError(f"Unknown universe: {universe}")
