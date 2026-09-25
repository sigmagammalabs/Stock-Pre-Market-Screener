"""Technical indicator calculations built directly on pandas.

Implemented manually (Wilder's smoothing via an equivalent EWM) instead of
depending on pandas-ta, which has had repeated breakage against newer numpy
releases. Keeps the dependency surface small and the math auditable.
"""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    result = 100 - (100 / (1 + rs))
    return result.fillna(100.0)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def avg_volume(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def gap_pct(current_price: float, previous_close: float) -> float:
    if previous_close in (None, 0):
        return 0.0
    return (current_price / previous_close - 1) * 100


def rvol(current_volume: float | None, avg_volume_value: float | None) -> float:
    if not current_volume or not avg_volume_value:
        return 0.0
    return current_volume / avg_volume_value
