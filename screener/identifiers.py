"""ISIN/WKN lookup from the curated table screener/identifiers.csv.

yfinance returns wrong ISINs for many European tickers and no WKN at all, so
the identifiers come from a fixed table for the DAX 40 and EURO STOXX 50 (all
entries verified by check digit and against OpenFIGI). Tickers outside the
table get empty values. The WKN is derived from German ISINs only
("DE000" + 6-character WKN + check digit); other countries have no such rule.
"""

from __future__ import annotations

import csv
import os
from functools import lru_cache

_CSV_PATH = os.path.join(os.path.dirname(__file__), "identifiers.csv")


@lru_cache(maxsize=1)
def _table() -> dict[str, str]:
    try:
        with open(_CSV_PATH, encoding="utf-8", newline="") as fh:
            return {row["ticker"].strip().upper(): row["isin"].strip().upper() for row in csv.DictReader(fh)}
    except (OSError, KeyError):
        return {}


def wkn_from_isin(isin: str) -> str:
    if len(isin) == 12 and isin.startswith("DE000"):
        return isin[5:11]
    return ""


def lookup(ticker: str) -> tuple[str, str]:
    isin = _table().get(ticker.strip().upper(), "")
    return isin, wkn_from_isin(isin)
