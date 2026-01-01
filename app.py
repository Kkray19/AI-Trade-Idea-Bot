import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from tradebot.db import SessionLocal, Base, engine
from tradebot.collectors.edgar import ingest_edgar
from tradebot.config import settings
from tradebot.scoring.score import idea_score
from tradebot.models import Summary

Base.metadata.create_all(bind=engine)

st.set_page_config(page_title="Trade Idea Bot", layout="wide")
st.title("Trade Idea Bot — Local Dashboard")

col1, col2, col3 = st.columns([1,1,2])
with col1:
    if st.button("Ingest EDGAR now"):
        res = ingest_edgar()
        st.success(f"Done: {res}")
with col2:
    asset_filter = st.selectbox("Asset type", ["all", "stock", "future"])
with col3:
    min_score = st.slider("Min score", 0.0, 10.0, 0.5, 0.1)

db = SessionLocal()
try:
    def fetch_edgar_filings(db_session, since_dt, symbol=None):
        base = """
        SELECT p.created_at,
               m.symbol,
               m.thesis_type,
               p.title,
               p.url
        FROM posts p
        JOIN mentions m ON m.post_id = p.id
        WHERE p.platform = 'edgar'
          AND p.created_at >= :since
        """
        params = {"since": since_dt}
        if symbol:
            base += " AND m.symbol = :symbol"
            params["symbol"] = symbol
        base += " ORDER BY p.created_at DESC"
        df_filings = pd.read_sql(text(base), db_session.bind, params=params)
        df_filings["created_at"] = pd.to_datetime(df_filings["created_at"], errors="coerce")
        df_filings["thesis_type"] = df_filings["thesis_type"].fillna("other")
        df_filings["title"] = df_filings["title"].fillna("Filing")
        return df_filings

    def build_daily_brief(df_filings):
        if df_filings.empty:
            return "_No EDGAR filings in the last 48 hours._"

        severity = ["offering", "8k", "insider", "ownership", "earnings/filing", "other"]
        lines = []
        for sev in severity:
            df_sev = df_filings[df_filings["thesis_type"] == sev]
            if df_sev.empty:
                continue
            grouped = df_sev.groupby("symbol")
            for symbol, group in grouped:
                group = group.sort_values("created_at", ascending=False)
                latest_date = group["created_at"].iloc[0].date().isoformat()
                links = []
                for _, row in group.head(3).iterrows():
                    links.append(f"[{row['title']}]({row['url']})")
                link_text = " | ".join(links)
                lines.append(
                    f"- **{symbol}** ({sev}, {len(group)} filings, latest {latest_date}): {link_text}"
                )
        return "\n".join(lines)

    def build_ticker_brief(df_filings, symbol):
        if df_filings.empty:
            return f"_No EDGAR filings for {symbol} in the last 7 days._"

        latest_date = df_filings["created_at"].max().date().isoformat()
        counts = df_filings["thesis_type"].value_counts()
        counts_text = ", ".join([f"{k}: {v}" for k, v in counts.items()])
        links = []
        for _, row in df_filings.sort_values("created_at", ascending=False).head(5).iterrows():
            links.append(f"[{row['title']}]({row['url']})")
        link_text = " | ".join(links)
        return (
            f"**{symbol}** — latest filing {latest_date}\n\n"
            f"Counts by thesis_type: {counts_text}\n\n"
            f"{link_text}"
        )

    def get_cached_summary(db_session, scope, symbol, window_days, source_max):
        q = db_session.query(Summary).filter_by(
            scope=scope,
            symbol=symbol,
            time_window_days=window_days,
        ).order_by(Summary.generated_at.desc())
        cached = q.first()
        if cached and cached.source_max_created_at == source_max:
            return cached.summary_text
        return None

    def save_summary(db_session, scope, symbol, window_days, source_max, text_value):
        db_session.add(Summary(
            scope=scope,
            symbol=symbol,
            time_window_days=window_days,
            summary_text=text_value,
            generated_at=datetime.utcnow(),
            source_max_created_at=source_max,
        ))
        db_session.commit()

    st.subheader("Summary")
    tab_daily, tab_ticker = st.tabs(["Daily Brief (48h)", "Ticker Brief (7d)"])

    with tab_daily:
        since_48h = datetime.utcnow() - timedelta(hours=48)
        df_48h = fetch_edgar_filings(db, since_48h)
        daily_brief = build_daily_brief(df_48h)
        st.markdown(daily_brief)

        if settings.openai_api_key:
            if st.button("Generate AI Summary", key="ai_daily"):
                source_max = df_48h["created_at"].max() if not df_48h.empty else None
                cached = get_cached_summary(db, "daily", None, 2, source_max)
                if cached:
                    st.markdown(cached)
                else:
                    ai_text = (
                        "AI summary unavailable (OpenAI client not installed). "
                        "Showing deterministic summary:\n\n" + daily_brief
                    )
                    save_summary(db, "daily", None, 2, source_max, ai_text)
                    st.markdown(ai_text)

    with tab_ticker:
        symbols = pd.read_sql(text("SELECT DISTINCT symbol FROM mentions ORDER BY symbol"), db.bind)
        symbol_list = symbols["symbol"].dropna().tolist()
        selected_symbol = st.selectbox("Symbol", symbol_list) if symbol_list else ""
        since_7d = datetime.utcnow() - timedelta(days=7)
        df_7d = fetch_edgar_filings(db, since_7d, symbol=selected_symbol) if selected_symbol else pd.DataFrame()
        ticker_brief = build_ticker_brief(df_7d, selected_symbol) if selected_symbol else "_No symbols found._"
        st.markdown(ticker_brief)

        if settings.openai_api_key and selected_symbol:
            if st.button("Generate AI Summary", key="ai_ticker"):
                source_max = df_7d["created_at"].max() if not df_7d.empty else None
                cached = get_cached_summary(db, "ticker", selected_symbol, 7, source_max)
                if cached:
                    st.markdown(cached)
                else:
                    ai_text = (
                        "AI summary unavailable (OpenAI client not installed). "
                        "Showing deterministic summary:\n\n" + ticker_brief
                    )
                    save_summary(db, "ticker", selected_symbol, 7, source_max, ai_text)
                    st.markdown(ai_text)

    q = """
    SELECT m.symbol,
           m.asset_type,
           COUNT(*) as mentions,
           SUM(p.score) as total_score,
           SUM(p.comments) as total_comments,
           MIN(p.created_at) as first_seen,
           MAX(p.created_at) as last_seen
    FROM mentions m
    JOIN posts p ON p.id = m.post_id
    GROUP BY m.symbol, m.asset_type
    ORDER BY last_seen DESC, mentions DESC
    LIMIT 200;
    """
    df = pd.read_sql(text(q), db.bind)

    cutoff = datetime.utcnow() - timedelta(hours=48)
    cq = """
    SELECT p.created_at as filing_date,
           m.symbol,
           m.thesis_type,
           p.title,
           p.url,
           p.body
    FROM posts p
    JOIN mentions m ON m.post_id = p.id
    WHERE p.platform = 'edgar'
      AND p.created_at >= :cutoff
    ORDER BY p.created_at DESC
    LIMIT 200;
    """
    catalysts = pd.read_sql(text(cq), db.bind, params={"cutoff": cutoff})

    df["last_seen"] = pd.to_datetime(df["last_seen"], errors="coerce")
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    age_hours = (now - df["last_seen"]).dt.total_seconds() / 3600.0
    age_hours = age_hours.fillna(9999.0)

    total_score = df["total_score"].fillna(0).astype(int)
    total_comments = df["total_comments"].fillna(0).astype(int)

    df["idea_score"] = [
        float(idea_score(int(s), int(c), float(a)))
        for s, c, a in zip(total_score, total_comments, age_hours)
    ]

    if asset_filter != "all":
        df = df[df["asset_type"] == asset_filter]

    df = df[df["idea_score"] >= min_score].sort_values("idea_score", ascending=False)

    st.subheader("Catalysts (last 48h)")
    st.dataframe(catalysts, use_container_width=True)

    st.subheader("Ranked ideas")
    st.dataframe(df, use_container_width=True)

    st.subheader("Posts for a symbol")
    sym = st.text_input("Symbol (e.g., TSLA, NVDA, ES)", "")
    if sym:
        pq = """
        SELECT p.platform, p.url, p.created_at, p.score, p.comments, p.title
        FROM posts p
        JOIN mentions m ON m.post_id = p.id
        WHERE m.symbol = :sym
        ORDER BY p.created_at DESC
        LIMIT 50;
        """
        posts = pd.read_sql(text(pq), db.bind, params={"sym": sym.upper()})
        st.dataframe(posts, use_container_width=True)
finally:
    db.close()
