# Trading Copilot

A local, saveable trading dashboard + Chrome overlay that gives **prompt-only** trade feedback.

It watches tickers, pulls chart data, pulls news, categorizes headlines, and gives educational prompts such as:

- WAIT
- LONG bias
- SHORT bias
- BUY_CALL idea
- BUY_PUT idea

It does **not** place live trades by default.

## What it does

### 1. Chart strategy scanner

Uses Yahoo/yfinance research data to scan symbols for:

- Opening range breakouts
- VWAP confirmation
- EMA 9 vs EMA 21 trend
- RSI check
- Volume confirmation
- ATR context

### 2. Options contract idea picker

If a clean setup appears, it looks for an options contract with:

- Bid and ask available
- Reasonable spread
- Minimum volume
- Minimum open interest
- Near-the-money strike

It gives the contract idea as a **paper-trading prompt**, not an order.

### 3. News engine

Pulls from these sources depending on what keys you add:

- Yahoo Finance RSS: works without a key
- Finnhub: optional key
- Alpha Vantage: optional key
- NewsAPI: optional key

Then it sorts the news into:

- Instant-watch
- Current
- Latest
- Background
- Macro / Economy
- Earnings / Guidance
- Analyst / Ratings
- Legal / Regulatory / SEC
- M&A / Deals
- Options / Flow
- Sector / Industry
- Crypto / Digital Assets
- Company / General Market

### 4. Chrome overlay

The extension can sit on top of chart/trading websites and show a bottom-right prompt while your local server is running.

It does not click buttons, read your password, or submit trades.

## Install

### Step 1: unzip the project

Keep the folder somewhere permanent, like:

```bash
Documents/trading-copilot
```

### Step 2: create a virtual environment

Windows PowerShell:

```bash
cd path\to\trading-copilot
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Mac/Linux:

```bash
cd path/to/trading-copilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3: optional API keys

Copy `.env.example` to `.env`.

```bash
cp .env.example .env
```

Then add keys only if you want extra providers.

The app works without keys using yfinance + Yahoo Finance RSS.

### Step 4: run it

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Load the overlay extension

1. Open `chrome://extensions`.
2. Turn on **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension` folder.
5. Keep the local server running.
6. Open a supported trading/chart website.

## Paper-first safety rules

This project is intentionally built as a copilot, not an autopilot.

Default guardrails:

- No live trades by default
- No market orders
- One options contract max in risk logic
- Max trades per day setting
- Max daily loss setting
- Paper bridge only unless you manually change settings
- Uses limit-order-style prices for options prompts

## Optional Alpaca paper bridge

There is an Alpaca paper-order scaffold in `copilot/broker_bridge.py`.

It will refuse to send anything unless:

```env
ENABLE_BROKER_ORDERS=true
```

and your Alpaca URL contains `paper`.

Keep this off until you have tested the strategy, understand options risk, and are legally allowed/approved to trade.

## File map

```text
trading-copilot/
  main.py
  requirements.txt
  .env.example
  README.md
  copilot/
    config.py
    data_providers.py
    indicators.py
    strategy_engine.py
    news_engine.py
    risk.py
    broker_bridge.py
    storage.py
    server.py
  templates/
    dashboard.html
  static/
    app.js
    style.css
  extension/
    manifest.json
    content.js
    overlay.css
    README_EXTENSION.md
  tests/
    test_indicators.py
```

## Important notes

Yahoo/yfinance is best treated as research data. For real orders, broker quotes and broker order status should be the final source of truth.

Options are risky and can lose value quickly. Use this project for learning and paper trading before considering real money.
