"""Central configuration for the pre-market screener."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class DataProviderName(str, Enum):
    YFINANCE = "yfinance"
    ALPACA = "alpaca"
    FMP = "fmp"


class UniverseName(str, Enum):
    SP500 = "sp500"
    NASDAQ100 = "nasdaq100"
    CUSTOM = "custom"


@dataclass
class ScreenerConfig:
    universe: UniverseName = UniverseName.NASDAQ100
    custom_tickers: list[str] = field(default_factory=list)
    provider: DataProviderName = DataProviderName.YFINANCE

    # Base filters
    min_price: float = 10.0
    min_avg_volume: int = 1_000_000
    min_gap_pct: float = 2.0
    min_rvol: float = 0.0

    # Indicator settings
    history_period: str = "1y"
    atr_period: int = 14
    rsi_period: int = 14
    sma_periods: tuple[int, int, int] = (20, 50, 200)
    avg_volume_period: int = 20

    # Ranking / output
    top_n: int = 10
    max_workers: int = 10
    scoring_weights: dict[str, float] = field(
        default_factory=lambda: {
            "rvol": 0.35,
            "gap": 0.30,
            "trend": 0.20,
            "atr_pct": 0.15,
        }
    )

    output_dir: str = "./watchlist"


@dataclass
class Secrets:
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    groq_api_key: str | None = None
    alpaca_api_key: str | None = None
    alpaca_api_secret: str | None = None
    fmp_api_key: str | None = None

    @classmethod
    def from_env(cls) -> "Secrets":
        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            alpaca_api_key=os.getenv("ALPACA_API_KEY"),
            alpaca_api_secret=os.getenv("ALPACA_API_SECRET"),
            fmp_api_key=os.getenv("FMP_API_KEY"),
        )


# llama-3.3-70b-versatile wurde von Groq entfernt (Stand 09/2026); gpt-oss-120b
# unterstützt json_mode + structured_outputs und läuft auf Groqs Hardware
# ähnlich schnell trotz der größeren Parameterzahl.
GROQ_MODEL = "openai/gpt-oss-120b"
