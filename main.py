#!/usr/bin/env python3
"""Pre-Market Screener CLI.

Examples:
    python main.py scan
    python main.py scan --universe sp500 --export csv --notify-telegram
    python main.py scan --universe custom --tickers AAPL,NVDA,TSLA --ai-briefing
    python main.py listen
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from screener import ai_groq, output, screener_engine, telegram_bot
from screener.config import DataProviderName, ScreenerConfig, Secrets, UniverseName
from screener.telegram_notifier import format_watchlist_message, send_telegram_message


def setup_logging(output_dir: str, verbose: bool) -> None:
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "screener.log")
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


def build_config(args: argparse.Namespace) -> ScreenerConfig:
    custom_tickers = []
    universe = UniverseName(args.universe)
    if universe == UniverseName.CUSTOM:
        if not args.tickers:
            raise SystemExit("--tickers ist erforderlich bei --universe custom")
        custom_tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    return ScreenerConfig(
        universe=universe,
        custom_tickers=custom_tickers,
        provider=DataProviderName(args.provider),
        min_price=args.min_price,
        min_avg_volume=args.min_avg_volume,
        min_gap_pct=args.min_gap_pct,
        min_rvol=args.min_rvol,
        top_n=args.top_n,
        output_dir=args.output_dir,
    )


def cmd_scan(args: argparse.Namespace) -> int:
    config = build_config(args)
    setup_logging(config.output_dir, args.verbose)
    logger = logging.getLogger("scan")
    secrets = Secrets.from_env()

    try:
        df = screener_engine.screen_market(config, secrets)
    except Exception:
        logger.exception("Scan fehlgeschlagen")
        return 1

    output.render_console_table(df, top_n=config.top_n)

    if args.export in ("csv", "both"):
        output.export_csv(df, config.output_dir)
    if args.export in ("json", "both"):
        output.export_json(df, config.output_dir)

    if args.notify_telegram or args.ai_briefing:
        ai_summary = None
        if args.ai_briefing and not df.empty:
            top_rows = df.head(3).to_dict(orient="records")
            ai_summary = ai_groq.generate_briefing(top_rows, secrets)
            if ai_summary is None:
                logger.info("Kein KI-Briefing verfügbar (Key fehlt oder API-Fehler) - reine Tabellenausgabe.")

        if args.notify_telegram:
            message = format_watchlist_message(df, top_n=config.top_n, ai_summary=ai_summary)
            sent = send_telegram_message(message, secrets)
            if not sent:
                logger.warning("Telegram-Benachrichtigung konnte nicht zugestellt werden.")

    return 0


def cmd_listen(args: argparse.Namespace) -> int:
    config = build_config(args)
    setup_logging(config.output_dir, args.verbose)
    secrets = Secrets.from_env()

    try:
        telegram_bot.run_listener(config, secrets, poll_interval=args.poll_interval)
    except ValueError as exc:
        logging.getLogger("listen").error(str(exc))
        return 1
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pre-Market Screener für US-Aktien")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--universe", choices=[u.value for u in UniverseName], default="nasdaq100")
    common.add_argument("--tickers", help="Kommagetrennte Ticker-Liste (nur bei --universe custom)")
    common.add_argument("--provider", choices=[p.value for p in DataProviderName], default="yfinance")
    common.add_argument("--min-price", type=float, default=10.0)
    common.add_argument("--min-avg-volume", type=int, default=1_000_000)
    common.add_argument("--min-gap-pct", type=float, default=2.0)
    common.add_argument("--min-rvol", type=float, default=0.0)
    common.add_argument("--top-n", type=int, default=10)
    common.add_argument("--output-dir", default="./watchlist")
    common.add_argument("--verbose", action="store_true")

    scan_parser = subparsers.add_parser("scan", parents=[common], help="Einmaligen Scan ausführen")
    scan_parser.add_argument("--export", choices=["none", "csv", "json", "both"], default="none")
    scan_parser.add_argument("--notify-telegram", action="store_true")
    scan_parser.add_argument("--ai-briefing", action="store_true", help="KI-Kompakt-Briefing via Groq anhängen")
    scan_parser.set_defaults(func=cmd_scan)

    listen_parser = subparsers.add_parser("listen", parents=[common], help="Telegram-Bot im Listening-Modus starten")
    listen_parser.add_argument("--poll-interval", type=float, default=3.0)
    listen_parser.set_defaults(func=cmd_listen)

    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    load_dotenv()
    parser = build_arg_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
