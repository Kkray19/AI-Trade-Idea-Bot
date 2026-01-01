````markdown
# AI Trade Idea Bot (Lane A: EDGAR Catalyst Dashboard)

A local Streamlit dashboard that tracks **small-cap catalysts** by ingesting recent **SEC EDGAR filings** for a configurable watchlist. It stores filings in a local SQLite database and surfaces a quick “what changed” view you can scan daily.

> Focus: **Small-cap catalysts** (offerings/dilution, 8-K events, insider Form 4s, ownership changes, etc.)

---

## Features

- **EDGAR ingestion (one-click refresh)** from the dashboard
- **Watchlist-driven**: edit `watchlist.txt` to control which tickers are tracked
- **Catalyst tagging** by filing type (e.g., offering / 8-K / insider / ownership)
- **Local persistence** via SQLite (keeps history across runs)
- **Dashboard views**
  - Recent catalysts (last 48h)
  - Ranked ideas (by recency / frequency)
  - Drilldown: filings for a specific symbol

---

## Tech Stack

- Python
- Streamlit (local dashboard)
- SQLAlchemy + SQLite (local DB)
- Requests (SEC data)

---

## Getting Started

### 1) Clone and create a virtual environment
```bash
git clone https://github.com/Kkray19/AI-Trade-Idea-Bot.git
cd "AI Trade Idea Bot"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
````

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure SEC User-Agent (recommended)

SEC requests should include a descriptive User-Agent with contact info.

Create a `.env` file in the project root:

```bash
SEC_USER_AGENT=AI-Trade-Idea-Bot (contact: youremail@example.com)
```

> Do **not** commit `.env` to GitHub.

### 4) Set your watchlist

Edit `watchlist.txt` (one ticker per line), for example:

```txt
SOUN
MARA
RIOT
GME
PLTR
```

### 5) Run the app

```bash
streamlit run app.py
```

Then click **Ingest EDGAR now** to refresh filings.

---

## How It Works

1. Reads tickers from `watchlist.txt`
2. Resolves tickers → CIK using SEC’s `company_tickers.json`
3. Pulls recent filings from SEC submissions JSON:

   * `https://data.sec.gov/submissions/CIK##########.json`
4. Stores each filing as a `Post` (`platform="edgar"`)
5. Stores ticker + catalyst classification as `Mention`
6. Dashboard queries the local SQLite DB to show recent catalysts + ranked ideas

---

## Catalyst Tags (current logic)

* **offering**: S-1, S-3, 424B*, and similar offering-related forms
* **8k**: 8-K
* **insider**: Form 4
* **ownership**: 13D / 13G
* **earnings/filing**: 10-Q / 10-K
* **other**: anything uncategorized

> You can refine the tagging logic in `tradebot/collectors/edgar.py`.

---

## Notes / Limitations

* This is a **research tool**, not trading advice.
* EDGAR filings are authoritative but sometimes lag press releases.
* Options volatility metrics are not included in Lane A (planned for Lane B).

---

## Roadmap

* Better offering detection (ATM language, pricing terms, share counts)
* Filing text extraction (lightweight snippets without heavy scraping)
* Severity scoring for “dilution risk” and “compliance risk”
* Lane B: options volatility module (broker/vendor integration)

---

## License

MIT (or replace with your preferred license)

```

If you want, I can also generate:
- a matching `LICENSE` file (MIT),
- a `.env.example` that’s safe to commit,
- and a short “Contributing” section.
::contentReference[oaicite:0]{index=0}
```
