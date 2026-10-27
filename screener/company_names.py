"""Company-name lookup with a persistent JSON cache.

Names rarely change, so each ticker is looked up once and then served from
./watchlist/company_names.json. A failed lookup is not cached and is retried
on the next run. Nothing in here may break a scan: all errors degrade to an
empty name.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

from .data_fetcher import DataProvider

logger = logging.getLogger(__name__)

CACHE_FILENAME = "company_names.json"


def _load(path: str) -> dict[str, str]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path: str, new_names: dict[str, str]) -> None:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # Re-read right before writing: the listener and the scheduled scan
        # share this file and must not overwrite each other's new entries.
        merged = _load(path)
        merged.update(new_names)
        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    except OSError as exc:
        logger.warning("Namens-Cache konnte nicht geschrieben werden (%s): %s", path, exc)


def resolve_names(provider: DataProvider, tickers: list[str], cache_dir: str, max_workers: int = 10) -> dict[str, str]:
    path = os.path.join(cache_dir, CACHE_FILENAME)
    cache = _load(path)
    missing = [t for t in dict.fromkeys(tickers) if not cache.get(t)]

    if missing:
        fetched: dict[str, str] = {}
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                for ticker, name in zip(missing, pool.map(provider.fetch_company_name, missing)):
                    if name:
                        fetched[ticker] = name
        except Exception as exc:
            logger.warning("Namensabfrage fehlgeschlagen: %s", exc)

        unresolved = [t for t in missing if t not in fetched]
        if unresolved:
            logger.info("Kein Firmenname gefunden für: %s", ", ".join(unresolved))
        if fetched:
            cache.update(fetched)
            _save(path, fetched)

    return {t: cache.get(t, "") for t in tickers}
