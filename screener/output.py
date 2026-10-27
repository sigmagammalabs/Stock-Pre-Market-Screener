"""Console rendering and file export for scan results."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime

import pandas as pd
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

DISPLAY_COLUMNS = ["Ticker", "Name", "ISIN", "WKN", "Price", "Gap%", "RVOL", "ATR", "RSI", "Trend", "Setup", "Score"]
LEFT_ALIGNED = {"Ticker", "Name", "ISIN", "WKN", "Trend"}
OPTIONAL_COLUMNS = {"ISIN", "WKN"}

LOG_WIDTH = 150


def render_console_table(df: pd.DataFrame, top_n: int | None = None) -> None:
    # Ohne TTY (Cron/docker exec/Log-Dateien) meldet Rich 80 Spalten; mit der
    # Name-Spalte würden dann alle Spalten auf "Ti…"/"Pr…" schrumpfen.
    console = Console(width=None if sys.stdout.isatty() else LOG_WIDTH)
    if df.empty:
        console.print("[yellow]Keine Treffer für die aktuellen Filterkriterien.[/yellow]")
        return

    for setup_name, style in (("Long Watch", "bold green"), ("Short Watch", "bold red")):
        subset = df[df["Setup"] == setup_name]
        if top_n:
            subset = subset.head(top_n)
        if subset.empty:
            continue

        # ISIN/WKN gibt es nur für DAX 40 und EURO STOXX 50; ohne Treffer weglassen.
        columns = [c for c in DISPLAY_COLUMNS if not (c in OPTIONAL_COLUMNS and subset[c].eq("").all())]

        table = Table(title=f"{setup_name} ({len(subset)})", header_style=style, title_style=style)
        for col in columns:
            justify = "left" if col in LEFT_ALIGNED else "right"
            if col == "Name":
                table.add_column(col, justify=justify, max_width=24, no_wrap=True, overflow="ellipsis")
            else:
                table.add_column(col, justify=justify)
        for _, row in subset.iterrows():
            table.add_row(*(str(row[c]) for c in columns))
        console.print(table)


def _timestamped_path(output_dir: str, extension: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(output_dir, f"watchlist_{stamp}.{extension}")


def export_csv(df: pd.DataFrame, output_dir: str) -> str:
    path = _timestamped_path(output_dir, "csv")
    df.to_csv(path, index=False)
    logger.info("CSV export written to %s", path)
    return path


def export_json(df: pd.DataFrame, output_dir: str) -> str:
    path = _timestamped_path(output_dir, "json")
    payload = {
        "generated_at": datetime.now().isoformat(),
        "count": len(df),
        "results": json.loads(df.to_json(orient="records")),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    logger.info("JSON export written to %s", path)
    return path
