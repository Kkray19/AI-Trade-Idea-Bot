from datetime import datetime
from pathlib import Path
import time
import requests

from ..config import settings
from ..db import SessionLocal
from ..models import Post, Mention

DEFAULT_WATCHLIST = ["SOUN", "MARA", "RIOT", "PLTR", "GME"]
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

def project_root():
    return Path(__file__).resolve().parents[2]

def load_watchlist():
    watchlist_path = project_root() / "watchlist.txt"
    if not watchlist_path.exists():
        return DEFAULT_WATCHLIST

    tickers = []
    for line in watchlist_path.read_text(encoding="utf-8").splitlines():
        sym = line.strip().upper()
        if not sym or sym.startswith("#"):
            continue
        tickers.append(sym)
    return tickers or DEFAULT_WATCHLIST

def sec_headers():
    return {"User-Agent": settings.sec_user_agent}

def fetch_company_tickers(session):
    resp = session.get(COMPANY_TICKERS_URL, headers=sec_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    mapping = {}
    for entry in data.values():
        ticker = str(entry.get("ticker", "")).upper()
        cik_str = entry.get("cik_str")
        if ticker and cik_str:
            mapping[ticker] = int(cik_str)
    return mapping

def resolve_cik(ticker, mapping):
    cik = mapping.get(ticker.upper())
    if not cik:
        return None
    return str(cik).zfill(10)

def build_filing_url(cik, accession, primary_doc):
    accession_no_dashes = accession.replace("-", "")
    cik_int = str(int(cik))
    if primary_doc:
        return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dashes}/{primary_doc}"
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dashes}/{accession}-index.html"

def classify_thesis_type(form, description):
    form_upper = (form or "").upper()
    text = (description or "").lower()

    if "reverse split" in text:
        return "reverse_split"
    if "compliance" in text or "listing" in text:
        return "compliance"
    if form_upper.startswith("8-K"):
        return "8k"
    if form_upper in {"4", "4/A"}:
        return "insider"
    if form_upper in {"SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A", "13D", "13G"}:
        return "ownership"
    if form_upper.startswith("10-Q") or form_upper.startswith("10-K"):
        return "earnings/filing"
    if form_upper.startswith("S-1") or form_upper.startswith("S-3") or form_upper.startswith("424B"):
        return "offering"
    if "atm" in text or "at-the-market" in text or "offering" in text:
        return "offering"
    return "other"

def ingest_edgar(limit_per_ticker=25, sleep_seconds=0.3):
    tickers = load_watchlist()
    session = requests.Session()

    mapping = fetch_company_tickers(session)
    db = SessionLocal()
    new_posts = 0
    skipped = 0

    try:
        for ticker in tickers:
            cik = resolve_cik(ticker, mapping)
            if not cik:
                skipped += 1
                continue

            url = SUBMISSIONS_URL.format(cik=cik)
            resp = session.get(url, headers=sec_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            recent = data.get("filings", {}).get("recent", {})

            accessions = recent.get("accessionNumber", [])
            forms = recent.get("form", [])
            filing_dates = recent.get("filingDate", [])
            report_dates = recent.get("reportDate", [])
            primary_docs = recent.get("primaryDocument", [])
            descriptions = recent.get("primaryDocDescription", [])

            for i in range(min(len(accessions), limit_per_ticker)):
                accession = accessions[i]
                form = forms[i] if i < len(forms) else ""
                filing_date = filing_dates[i] if i < len(filing_dates) else ""
                report_date = report_dates[i] if i < len(report_dates) else ""
                primary_doc = primary_docs[i] if i < len(primary_docs) else ""
                description = descriptions[i] if i < len(descriptions) else ""

                if not accession or not filing_date:
                    continue

                try:
                    created_at = datetime.strptime(filing_date, "%Y-%m-%d")
                except ValueError:
                    continue

                title_desc = primary_doc or description or "Filing"
                title = f"{form} - {title_desc}".strip(" -")
                body = (
                    f"Form: {form}\n"
                    f"Filing date: {filing_date}\n"
                    f"Report date: {report_date or 'n/a'}\n"
                    f"Accession: {accession}"
                )
                platform_post_id = f"{cik}-{accession}-{form}"
                url = build_filing_url(cik, accession, primary_doc)

                exists = db.query(Post).filter_by(platform="edgar", platform_post_id=platform_post_id).first()
                if exists:
                    exists.url = url
                    exists.title = title
                    exists.body = body
                    exists.created_at = created_at
                    continue

                post = Post(
                    platform="edgar",
                    platform_post_id=platform_post_id,
                    url=url,
                    author=None,
                    title=title,
                    body=body,
                    created_at=created_at,
                    score=0,
                    comments=0,
                )
                db.add(post)
                db.flush()

                thesis_type = classify_thesis_type(form, f"{title} {description} {body}")
                db.add(Mention(
                    post_id=post.id,
                    symbol=ticker,
                    asset_type="stock",
                    stance=None,
                    thesis_type=thesis_type,
                    confidence=0.8,
                ))
                new_posts += 1

            time.sleep(sleep_seconds)

        db.commit()
        return {"new_posts": new_posts, "skipped": skipped}
    finally:
        db.close()
