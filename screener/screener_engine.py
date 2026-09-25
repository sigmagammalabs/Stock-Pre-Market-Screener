"""Orchestrates data fetching, indicator calculation, filtering and scoring."""

from __future__ import annotations

import logging

import pandas as pd

from . import indicators, scoring
from .config import ScreenerConfig, Secrets
from .data_fetcher import get_provider
from .universe import get_tickers

logger = logging.getLogger(__name__)

RESULT_COLUMNS = [
    "Ticker", "Price", "PrevClose", "Gap%", "RVOL", "ATR", "ATR%", "RSI",
    "SMA20", "SMA50", "SMA200", "Trend", "Setup", "Score",
]


def screen_market(
    config: ScreenerConfig,
    secrets: Secrets,
    override_tickers: list[str] | None = None,
    min_rvol_override: float | None = None,
    min_gap_pct_override: float | None = None,
) -> pd.DataFrame:
    tickers = override_tickers or get_tickers(config.universe, config.custom_tickers)
    logger.info("Screening %d tickers via provider=%s", len(tickers), config.provider)

    provider = get_provider(config.provider, secrets)
    histories = provider.fetch_daily_history_batch(tickers, config.history_period, config.max_workers)
    if not histories:
        logger.warning("No historical data retrieved for any ticker.")
        return pd.DataFrame(columns=RESULT_COLUMNS)

    quotes = provider.fetch_quote_batch(list(histories.keys()), config.max_workers)

    min_gap_pct = min_gap_pct_override if min_gap_pct_override is not None else config.min_gap_pct
    min_rvol = min_rvol_override if min_rvol_override is not None else config.min_rvol

    rows = []
    for ticker, history in histories.items():
        quote = quotes.get(ticker)
        if quote is None or quote.price is None or quote.previous_close is None:
            logger.debug("Skipping %s: no usable quote.", ticker)
            continue

        try:
            row = _build_row(ticker, history, quote, config, min_gap_pct, min_rvol)
        except Exception as exc:
            logger.warning("Skipping %s due to calculation error: %s", ticker, exc)
            continue

        if row is not None:
            rows.append(row)

    if not rows:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    df = pd.DataFrame(rows, columns=RESULT_COLUMNS)
    df = df.sort_values("Score", ascending=False).reset_index(drop=True)
    return df


def _build_row(ticker, history, quote, config: ScreenerConfig, min_gap_pct: float, min_rvol: float):
    close = history["Close"]
    volume = history["Volume"]

    avg_vol_20 = indicators.avg_volume(volume, config.avg_volume_period).iloc[-1]
    if pd.isna(avg_vol_20) or avg_vol_20 < config.min_avg_volume:
        return None
    if quote.price < config.min_price:
        return None

    sma20 = indicators.sma(close, 20).iloc[-1]
    sma50 = indicators.sma(close, 50).iloc[-1]
    sma200 = indicators.sma(close, 200).iloc[-1]
    rsi14 = indicators.rsi(close, config.rsi_period).iloc[-1]
    atr14 = indicators.atr(history, config.atr_period).iloc[-1]
    atr_pct = (atr14 / quote.price * 100) if quote.price else 0.0

    gap = indicators.gap_pct(quote.price, quote.previous_close)
    if abs(gap) < min_gap_pct:
        return None

    rvol_value = indicators.rvol(quote.volume, avg_vol_20)
    if rvol_value < min_rvol:
        return None

    alignment = scoring.trend_alignment(
        quote.price,
        None if pd.isna(sma20) else sma20,
        None if pd.isna(sma50) else sma50,
        None if pd.isna(sma200) else sma200,
    )
    setup = scoring.classify_setup(gap, alignment, min_gap_pct)
    if setup is None:
        return None

    score = scoring.compute_score(rvol_value, gap, alignment, atr_pct, config.scoring_weights)
    trend_label = _trend_label(quote.price, sma20, sma50, sma200)

    return {
        "Ticker": ticker,
        "Price": round(quote.price, 2),
        "PrevClose": round(quote.previous_close, 2),
        "Gap%": round(gap, 2),
        "RVOL": round(rvol_value, 2),
        "ATR": round(atr14, 2) if not pd.isna(atr14) else None,
        "ATR%": round(atr_pct, 2) if not pd.isna(atr_pct) else None,
        "RSI": round(rsi14, 1) if not pd.isna(rsi14) else None,
        "SMA20": round(sma20, 2) if not pd.isna(sma20) else None,
        "SMA50": round(sma50, 2) if not pd.isna(sma50) else None,
        "SMA200": round(sma200, 2) if not pd.isna(sma200) else None,
        "Trend": trend_label,
        "Setup": setup,
        "Score": score,
    }


def _trend_label(price: float, sma20: float, sma50: float, sma200: float) -> str:
    parts = []
    if not pd.isna(sma200):
        parts.append("über SMA200" if price > sma200 else "unter SMA200")
    if not pd.isna(sma50):
        parts.append("über SMA50" if price > sma50 else "unter SMA50")
    if not pd.isna(sma20):
        parts.append("über SMA20" if price > sma20 else "unter SMA20")
    return ", ".join(parts) if parts else "n/a"
