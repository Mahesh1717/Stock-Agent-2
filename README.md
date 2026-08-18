# Stock Agent RAG

Personal stock alert agent for Indian equities.

Pipeline:

```text
RSS news -> stock matching -> FinBERT sentiment -> technical indicators -> RAG evidence -> signal score -> Telegram alert
```

This is not financial advice and it does not place trades. It is an alerting tool to help you notice market-moving news with technical confirmation.

## Features

- Reads market news from RSS feeds.
- Matches headlines to a broad NSE watchlist based on Nifty 500 constituents.
- Scores financial sentiment with FinBERT.
- Pulls NSE price data through `yfinance`.
- Calculates RSI, MACD, SMA20, SMA50, and volume ratio.
- Retrieves local financial-document evidence from ChromaDB.
- Adds fundamental context from annual reports, quarterly results, investor presentations, and transcripts.
- Generates BUY / HOLD / SELL signals using an explainable scoring engine.
- Sends Telegram alerts.
- Stores processed article links to avoid duplicate alerts.

## Setup

Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\stock_agent_env\Scripts\Activate.ps1
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
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
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

## Local RAG For Financial Documents

This version uses local retrieval from company financial documents by default. It is not a generic PDF chatbot. The agent uses retrieved earnings and management-commentary evidence as extra context before sending BUY / HOLD / SELL alerts.

### Add Documents

The repo includes folders for all 500 watchlist symbols. Place PDFs under `documents/<STOCK_SYMBOL>/`:

```text
documents/
  TCS/
    Q4_FY26_results.pdf
    Annual_Report_FY25.pdf
  INFY/
    Q1_FY26_results.pdf
  HDFCBANK/
```

For NSE stocks, prefer company investor-relations pages, NSE/BSE disclosures, annual reports, quarterly results, investor presentations, and earnings-call transcripts.

To recreate the stock folders after changing the watchlist:

```powershell
python scripts/scaffold_document_folders.py
```

To download annual reports from NSE into the stock folders:

```powershell
python scripts/download_nse_documents.py --max-annual-reports 3
```

Test with a few stocks first:

```powershell
python scripts/download_nse_documents.py --symbols TCS,INFY,HDFCBANK --max-annual-reports 2
```

The downloader writes a resumable manifest to `database/document_manifest.json`. NSE throttles requests, so downloading reports for all 500 stocks can take a long time and should be done after market hours.

Downloaded PDFs are ignored by Git on purpose:

```text
documents/**/*.pdf
```

The latest annual-report crawl for 500 stocks is several GB. Do not push those PDFs to a normal GitHub repo. Keep them local, on a VPS disk, or use a dedicated document store. The code, folder structure, downloader, and manifest can live in Git; the PDF corpus should be recreated with the downloader where the agent runs.

### Install RAG Dependencies

```powershell
pip install -r requirements.txt
```

The local RAG packages are:

- `pypdf` for PDF text extraction
- `chromadb` for the local vector database
- `sentence-transformers` for local embeddings

### Ingest Documents

```powershell
python app.py --ingest-documents
```

This reads PDFs from `documents/`, chunks the text, embeds it locally, and stores vectors under `chroma_db/`.

### Test Retrieval

```powershell
python app.py --rag-query "European banking growth and deal wins" --stock TCS
```

### RAG Settings

These are the default `.env` settings:

```text
DOCUMENTS_PATH=documents
CHROMA_PATH=chroma_db
RAG_COLLECTION=financial_reports
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_TOP_K=5
```

Run the agent:

```powershell
python app.py --once
```

When news matches a stock with ingested documents, the Telegram alert includes:

- retrieved evidence summary
- fundamental score from `-2` to `+2`
- positive evidence
- document risks
- source document/page citations

### Optional Ollama Analysis

The default RAG assessment uses a simple local heuristic, so no LLM server is required.

To use a local LLM explanation layer:

```powershell
ollama pull llama3.1:8b
```

Set:

```text
OLLAMA_ENABLED=true
OLLAMA_MODEL=llama3.1:8b
OLLAMA_URL=http://localhost:11434/api/generate
```

The prompt instructs the model to use only retrieved evidence and return structured JSON. It should not predict tomorrow's stock price.

For GitHub Actions, the workflow ingests `documents/` before each run. Keep reports reasonably scoped because embedding hundreds of large PDFs on every scheduled run can be slow. For heavier document sets, run this on your laptop or VPS where `chroma_db/` persists.

## Watchlist

The default file is:

```text
data/nifty_watchlist.csv
```

The current watchlist is generated from the official NSE Nifty 500 constituent CSV, covering large, mid, and small-cap names across financial services, IT, pharma, auto, FMCG, power, energy, realty, defence-linked, railway-linked, PSU, and other actively traded sectors.

Columns:

```text
symbol,yahoo_symbol,name,aliases
```

Add aliases separated by `|`.
If a stock has changed ticker, add Yahoo fallback symbols separated by `|` in `yahoo_symbol`, for example `TMPV.NS|TATAMOTORS.NS`.

With a 300-500 stock universe, exact aliases are preferred and fuzzy matching is intentionally stricter to reduce false matches from short symbols.

## Signal Rules

The signal engine uses a deterministic score:

- Positive news above threshold: `+3`
- High-trust positive news source: `+1`
- RSI below 35: `+2`
- MACD bullish: `+2`
- Volume ratio above 1.5x: `+1`
- Price above SMA20: `+1`
- Fundamental evidence from RAG: `-2` to `+2`

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
