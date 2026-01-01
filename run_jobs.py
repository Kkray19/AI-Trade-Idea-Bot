from tradebot.db import Base, engine, SessionLocal
from tradebot.collectors.reddit import ingest_reddit

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print(ingest_reddit(limit_per_sub=75))
