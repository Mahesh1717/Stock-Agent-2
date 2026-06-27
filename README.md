# Stock Agent Phase 1

Personal stock alert agent for Indian equities.

Pipeline:

```text
RSS news -> stock matching -> FinBERT sentiment -> technical indicators -> signal score -> Telegram alert
```

This is not financial advice and it does not place trades. It is an alerting tool to help you notice market-moving news with technical confirmation.

## Features

- Reads market news from RSS feeds.
- Matches headlines to a Nifty 50 / Nifty Next 50 watchlist.
- Scores financial sentiment with FinBERT.
- Pulls NSE price data through `yfinance`.
- Calculates RSI, MACD, SMA20, SMA50, and volume ratio.
- Generates BUY / HOLD / SELL signals using an explainable scoring engine.
- Sends Telegram alerts.
- Stores processed article links to avoid duplicate alerts.

## Setup

Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

If you are on Python 3.13, avoid old exact dependency pins. This project uses version ranges so packages like `pandas` and `torch` can install prebuilt Windows wheels instead of compiling from source.

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your Telegram details:

```text
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

To get these:

1. Create a bot with Telegram `@BotFather`.
2. Send any message to your bot.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates`.
4. Copy the `chat.id` value.

## Run Once

```powershell
python app.py --once
```

## Test Telegram

```powershell
python app.py --test-telegram
```

## Run Continuously

```powershell
python app.py
```

By default it checks every 60 seconds. Change this in `.env`:

```text
RUN_INTERVAL_SECONDS=60
```

## Test Without Telegram

Set:

```text
DRY_RUN=true
```

Alerts will print to the terminal instead of being sent.

## Watchlist

The default file is:

```text
data/nifty_watchlist.csv
```

Columns:

```text
symbol,yahoo_symbol,name,aliases
```

Add aliases separated by `|`.
If a stock has changed ticker, add Yahoo fallback symbols separated by `|` in `yahoo_symbol`, for example `TMPV.NS|TATAMOTORS.NS`.

## Signal Rules

The first version uses a simple deterministic score:

- Positive news above threshold: `+3`
- High-trust positive news source: `+1`
- RSI below 35: `+2`
- MACD bullish: `+2`
- Volume ratio above 1.5x: `+1`
- Price above SMA20: `+1`

Decision:

- Strong negative news + bearish MACD + volume spike + price below SMA20: `SELL`
- `0-2` without strong sell confirmation: `IGNORE`
- `3-5`: HOLD
- `6+`: BUY

You can adjust thresholds in `.env`.

Alerts are sent only when both conditions pass:

- `Action` is listed in `ALERT_ACTIONS`
- For `BUY` / `HOLD`, `Score` is at least `MIN_ALERT_SCORE`
- For `SELL`, the strong-sell rule has fired

Default:

```text
ALERT_ACTIONS=BUY,HOLD,SELL
MIN_ALERT_SCORE=3
```

This avoids sending weak `SELL` labels caused by "no bullish signal found". `SELL` is sent only when negative news has bearish technical confirmation.

To receive every matched signal while testing, temporarily set:

```text
ALERT_ACTIONS=BUY,HOLD,SELL,IGNORE
MIN_ALERT_SCORE=0
```
