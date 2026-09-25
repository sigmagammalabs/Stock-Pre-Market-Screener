"""Market data providers.

Only the yfinance provider is fully implemented. Alpaca and FMP are stubbed
out behind the same interface (`DataProvider`) so they can be dropped in via
the `--provider` CLI flag / config.provider once API credentials and a
concrete HTTP client are wired up.
"""

from __future__ import annotations

import abc
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import pandas as pd

from .config import Secrets

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    ticker: str
    price: float | None
    previous_close: float | None
    volume: float | None


class DataProvider(abc.ABC):
    @abc.abstractmethod
    def fetch_daily_history(self, ticker: str, period: str) -> pd.DataFrame | None:
        """Return a DataFrame with columns Open/High/Low/Close/Volume, indexed by date."""

    @abc.abstractmethod
    def fetch_quote(self, ticker: str) -> Quote | None:
        """Return the latest available (pre-market aware) quote for a ticker."""

    def fetch_daily_history_batch(self, tickers: list[str], period: str, max_workers: int = 10) -> dict[str, pd.DataFrame]:
        results: dict[str, pd.DataFrame] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(self.fetch_daily_history, t, period): t for t in tickers}
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        results[ticker] = df
                    else:
                        logger.warning("No history data for %s", ticker)
                except Exception as exc:
                    logger.warning("Failed to fetch history for %s: %s", ticker, exc)
        return results

    def fetch_quote_batch(self, tickers: list[str], max_workers: int = 10) -> dict[str, Quote]:
        results: dict[str, Quote] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(self.fetch_quote, t): t for t in tickers}
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    quote = future.result()
                    if quote is not None:
                        results[ticker] = quote
                    else:
                        logger.warning("No quote data for %s", ticker)
                except Exception as exc:
                    logger.warning("Failed to fetch quote for %s: %s", ticker, exc)
        return results


class YFinanceProvider(DataProvider):
    def __init__(self) -> None:
        import yfinance as yf

        self._yf = yf

    def fetch_daily_history(self, ticker: str, period: str = "1y") -> pd.DataFrame | None:
        try:
            df = self._yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
            if df is None or df.empty:
                return None
            return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        except Exception as exc:
            logger.debug("history fetch failed for %s: %s", ticker, exc)
            return None

    def fetch_quote(self, ticker: str) -> Quote | None:
        try:
            tk = self._yf.Ticker(ticker)
            fi = tk.fast_info
            price = _safe_get(fi, "last_price", "lastPrice")
            prev_close = _safe_get(fi, "previous_close", "previousClose", "regular_market_previous_close")
            volume = _safe_get(fi, "last_volume", "lastVolume", "regular_market_volume")

            if price is None or prev_close is None:
                # Fallback: intraday/pre-post history for the most recent trade.
                intraday = tk.history(period="1d", interval="1m", prepost=True)
                if not intraday.empty:
                    price = price if price is not None else float(intraday["Close"].dropna().iloc[-1])
                    volume = volume if volume is not None else float(intraday["Volume"].fillna(0).sum())
                daily = tk.history(period="5d", interval="1d", prepost=False)
                if prev_close is None and not daily.empty:
                    prev_close = float(daily["Close"].iloc[-1])

            if price is None or prev_close is None:
                return None

            return Quote(ticker=ticker, price=float(price), previous_close=float(prev_close),
                         volume=float(volume) if volume is not None else None)
        except Exception as exc:
            logger.debug("quote fetch failed for %s: %s", ticker, exc)
            return None


def _safe_get(obj, *keys):
    for key in keys:
        try:
            value = obj[key] if hasattr(obj, "__getitem__") else getattr(obj, key)
            if value is not None:
                return value
        except (KeyError, AttributeError, TypeError):
            continue
    return None


class AlpacaProvider(DataProvider):
    """Placeholder for the Alpaca Market Data API. Requires alpaca-py and API keys."""

    def __init__(self, secrets: Secrets) -> None:
        if not secrets.alpaca_api_key or not secrets.alpaca_api_secret:
            raise ValueError("ALPACA_API_KEY / ALPACA_API_SECRET missing in environment (.env)")
        self._secrets = secrets

    def fetch_daily_history(self, ticker: str, period: str) -> pd.DataFrame | None:
        raise NotImplementedError(
            "Alpaca provider is a stub. Implement via alpaca-py's StockHistoricalDataClient "
            "and map bars to Open/High/Low/Close/Volume columns."
        )

    def fetch_quote(self, ticker: str) -> Quote | None:
        raise NotImplementedError(
            "Alpaca provider is a stub. Implement via alpaca-py's latest-quote/latest-trade endpoints."
        )


class FMPProvider(DataProvider):
    """Placeholder for the FinancialModelingPrep REST API. Requires an API key."""

    def __init__(self, secrets: Secrets) -> None:
        if not secrets.fmp_api_key:
            raise ValueError("FMP_API_KEY missing in environment (.env)")
        self._secrets = secrets

    def fetch_daily_history(self, ticker: str, period: str) -> pd.DataFrame | None:
        raise NotImplementedError(
            "FMP provider is a stub. Implement via the /historical-price-full endpoint."
        )

    def fetch_quote(self, ticker: str) -> Quote | None:
        raise NotImplementedError(
            "FMP provider is a stub. Implement via the /quote endpoint."
        )


def get_provider(name: str, secrets: Secrets) -> DataProvider:
    if name == "yfinance":
        return YFinanceProvider()
    if name == "alpaca":
        return AlpacaProvider(secrets)
    if name == "fmp":
        return FMPProvider(secrets)
    raise ValueError(f"Unknown data provider: {name}")
