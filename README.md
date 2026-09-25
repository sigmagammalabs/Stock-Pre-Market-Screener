# Stock-Pre-Market-Screener

CLI-Tool zum täglichen Screening von US-Aktien (S&P 500 / NASDAQ 100 / eigenes
Ticker-Universum) mit Gap-, RVOL-, ATR- und RSI-basiertem Scoring, optionalem
Telegram-Versand und optionaler Groq-LLM-Unterstützung (Intent-Parsing +
Kompakt-Briefing).

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
```

`.env` mit den gewünschten Keys befüllen (Telegram/Groq sind optional - ohne
sie läuft der Scan rein regelbasiert und ohne Versand).

## Verwendung

Einmaliger Scan, Konsolenausgabe:

```bash
python main.py scan
```

S&P 500 scannen, CSV exportieren, Telegram-Benachrichtigung inkl. KI-Briefing:

```bash
python main.py scan --universe sp500 --export csv --notify-telegram --ai-briefing
```

Eigenes Ticker-Universum:

```bash
python main.py scan --universe custom --tickers AAPL,NVDA,TSLA,AMD
```

DAX 40 oder EURO STOXX 50 scannen (europäische Ticker, kein echtes "Pre-Market" -
stattdessen Gap zum Vortagesschluss während der regulären Handelszeiten):

```bash
python main.py scan --universe dax40
python main.py scan --universe eurostoxx50
```

Telegram-Bot im Dauerbetrieb starten (Natural-Language-Kommandos wie
"Scanne nur Halbleiter mit hohem Volumen" via Groq, Fallback auf `/scan` und
`/quote TICKER ...` ohne Groq-Key):

```bash
python main.py listen
```

### Wichtige Flags

| Flag | Beschreibung | Default |
|---|---|---|
| `--universe` | `sp500`, `nasdaq100`, `dax40`, `eurostoxx50`, `custom` | `nasdaq100` |
| `--tickers` | Kommagetrennte Liste (nur mit `--universe custom`) | - |
| `--provider` | `yfinance`, `alpaca` (Stub), `fmp` (Stub) | `yfinance` |
| `--min-price` | Mindestkurs in USD | `10.0` |
| `--min-avg-volume` | Mindest-20-Tage-Ø-Volumen | `1000000` |
| `--min-gap-pct` | Mindest-Gap in % (absolut) | `2.0` |
| `--min-rvol` | Mindest-RVOL | `0.0` |
| `--top-n` | Treffer pro Kategorie (Konsole/Telegram) | `10` |
| `--export` | `none`, `csv`, `json`, `both` (nur `scan`) | `none` |
| `--notify-telegram` | Ergebnis per Telegram senden (nur `scan`) | aus |
| `--ai-briefing` | Groq-Kompakt-Briefing anhängen (nur `scan`) | aus |
| `--output-dir` | Zielordner für Exporte/Logs | `./watchlist` |

Exporte landen zeitgestempelt in `./watchlist/` (`watchlist_YYYYMMDD_HHMMSS.csv/json`),
Logs in `./watchlist/screener.log`.

## Ausführung via Cronjob / Scheduler

**Linux/macOS (cron)** - werktags 08:45 Uhr vor US-Pre-Market:

```cron
45 8 * * 1-5 cd /pfad/zum/projekt && /pfad/zu/venv/bin/python main.py scan --universe sp500 --export csv --notify-telegram --ai-briefing >> ./watchlist/cron.log 2>&1
```

**Windows (Aufgabenplanung / Task Scheduler)**:

```powershell
schtasks /create /tn "PreMarketScreener" /tr "python \"F:\AI-CODE-AREA\Wertpapiere Watchliste\main.py\" scan --universe sp500 --export csv --notify-telegram --ai-briefing" /sc weekly /d MON,TUE,WED,THU,FRI /st 08:45
```

## Deployment auf einem Hetzner VPS (Ubuntu/Debian)

Fertige Skripte liegen unter `deploy/`:

```bash
git clone https://github.com/sigmagammalabs/Stock-Pre-Market-Screener.git
cd Stock-Pre-Market-Screener
bash deploy/setup_vps.sh          # Python/venv/Dependencies, .env aus Vorlage anlegen
nano .env                         # TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GROQ_API_KEY eintragen

# Testlauf
.venv/bin/python main.py scan --universe custom --tickers AAPL,NVDA --min-gap-pct 0.1

# Telegram-Listener als Dauerprozess (systemd)
bash deploy/install_listener_service.sh
sudo journalctl -u watchlist-listener -f

# Täglicher Scan per Cronjob
bash deploy/install_cron.sh
```

| Skript | Zweck |
|---|---|
| `deploy/setup_vps.sh` | Einmaliges Setup: Pakete, venv, Dependencies, `.env`-Vorlage |
| `deploy/install_listener_service.sh` | Installiert `watchlist-listener` als systemd-Service (Auto-Restart, Autostart) |
| `deploy/install_cron.sh` | Trägt `deploy/run_scan.sh` werktags 08:15 Uhr Berlin-Zeit (45 Min. vor Xetra-Öffnung) in die Crontab ein |
| `deploy/run_scan.sh` | Cron-Wrapper: aktiviert venv, ruft `main.py scan --universe eurostoxx50` auf |
| `deploy/watchlist-listener.service.template` | systemd-Unit-Vorlage für den Telegram-Listener (`--universe eurostoxx50`) |

**Hinweise:**
- Cron/Listener sind aktuell auf `eurostoxx50` und die Europe/Berlin-Serverzeitzone kalibriert. Für ein US-Setup (`sp500`/`nasdaq100`) `deploy/run_scan.sh`, `deploy/watchlist-listener.service.template` und die Cron-Uhrzeit in `deploy/install_cron.sh` entsprechend anpassen (US-Pre-Market liegt bei Berlin-Serverzeit ca. 6h vor der Cron-Zeit einer europäischen Marktöffnung).
- Serverzeitzone beachten (`timedatectl`) - die Cron-Uhrzeit in `deploy/install_cron.sh` ist auf Serverzeit bezogen.
- Nach jedem `git pull` auf dem VPS: `sudo systemctl restart watchlist-listener`, damit der Listener den neuen Code lädt.
- `.env` niemals ins Git-Repo committen (ist in `.gitignore` ausgeschlossen).

Der Telegram-Listener (`python main.py listen`) ist ein Dauerprozess und
gehört nicht in einen Cronjob - stattdessen z. B. via `systemd`-Service,
`pm2`, oder als geplanter "bei Systemstart"-Task betreiben.

## Architektur

```
main.py                     CLI-Einstiegspunkt (scan / listen)
screener/
  config.py                 Konfiguration & Secrets (.env)
  universe.py                Ticker-Universen (Wikipedia + Offline-Fallback)
  data_fetcher.py            Datenanbieter-Abstraktion (yfinance impl., Alpaca/FMP Stubs)
  indicators.py               SMA / RSI / ATR / RVOL / Gap%
  scoring.py                  Trendausrichtung, gewichtetes Scoring, Setup-Klassifikation
  screener_engine.py          Orchestrierung: Fetch -> Filter -> Score -> DataFrame
  output.py                   Rich-Konsolentabelle, CSV-/JSON-Export
  telegram_notifier.py        Nachrichtenformatierung & Versand (Telegram Bot API)
  telegram_bot.py             Long-Polling-Listener für Freitext-Kommandos
  ai_groq.py                  Intent-Parsing (JSON) & KI-Kompakt-Briefing via Groq
```

## Hinweise

- `--provider alpaca` / `--provider fmp` sind als Interface-Stubs angelegt
  (`screener/data_fetcher.py`) und werfen `NotImplementedError`, bis eine
  konkrete Anbindung ergänzt wird.
- Ohne `GROQ_API_KEY` fallen Intent-Parsing und Briefing geräuschlos auf
  regelbasiertes Verhalten zurück (`/scan`, `/quote TICKER ...`, reine
  Tabellenausgabe ohne KI-Text).
- Ohne `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` wird der Versand übersprungen
  und ein Fehler geloggt, das Hauptskript bricht nicht ab.
