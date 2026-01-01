from datetime import datetime, timezone
import praw
from ..config import settings
from ..db import SessionLocal
from ..models import Post, Mention
from ..nlp.tickers import extract_symbols, classify_asset_type

SUBS_DEFAULT = ["wallstreetbets", "stocks", "options", "investing"]

def reddit_client():
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        raise RuntimeError("Missing REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET. Check your .env.")
    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )

def ingest_reddit(limit_per_sub=50, subs=None):
    subs = subs or SUBS_DEFAULT
    r = reddit_client()

    db = SessionLocal()
    new_posts = 0

    try:
        for sub in subs:
            for s in r.subreddit(sub).hot(limit=limit_per_sub):
                created = datetime.fromtimestamp(s.created_utc, tz=timezone.utc).replace(tzinfo=None)
                p = Post(
                    platform="reddit",
                    platform_post_id=s.id,
                    url=f"https://www.reddit.com{s.permalink}",
                    author=str(s.author) if s.author else None,
                    title=s.title,
                    body=getattr(s, "selftext", None),
                    created_at=created,
                    score=int(getattr(s, "score", 0) or 0),
                    comments=int(getattr(s, "num_comments", 0) or 0),
                )

                # upsert behavior
                exists = db.query(Post).filter_by(platform="reddit", platform_post_id=s.id).first()
                if exists:
                    exists.score = p.score
                    exists.comments = p.comments
                    continue

                db.add(p)
                db.flush()

                text = f"{p.title or ''}\n{p.body or ''}"
                syms = extract_symbols(text)
                for sym in syms:
                    db.add(Mention(
                        post_id=p.id,
                        symbol=sym,
                        asset_type=classify_asset_type(sym),
                        confidence=0.6,
                    ))
                new_posts += 1

        db.commit()
        return {"new_posts": new_posts}
    finally:
        db.close()
