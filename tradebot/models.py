from sqlalchemy import Column, Integer, String, DateTime, Float, Text, UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    platform = Column(String, nullable=False)  # reddit/x/...
    platform_post_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
    author = Column(String, nullable=True)
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    score = Column(Integer, default=0)      # upvotes/likes
    comments = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("platform", "platform_post_id", name="uq_post"),)

class Mention(Base):
    __tablename__ = "mentions"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    symbol = Column(String, nullable=False)         # AAPL, TSLA, ES, NQ...
    asset_type = Column(String, nullable=False)     # stock/option/future
    stance = Column(String, nullable=True)          # bull/bear/neutral
    thesis_type = Column(String, nullable=True)     # technical/catalyst/flow/macro/meme
    confidence = Column(Float, default=0.5)

    post = relationship("Post", backref="mentions")

class Summary(Base):
    __tablename__ = "summaries"
    id = Column(Integer, primary_key=True)
    scope = Column(String, nullable=False)  # daily/ticker
    symbol = Column(String, nullable=True)
    time_window_days = Column(Integer, nullable=False)
    summary_text = Column(Text, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    source_max_created_at = Column(DateTime, nullable=True)
