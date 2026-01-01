from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    db_url: str = "sqlite:///tradebot.sqlite"
    reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
    reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "tradebot:local:v0.1")
    sec_user_agent: str = os.getenv("SEC_USER_AGENT", "trade_idea_bot (email@example.com)")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    x_bearer_token: str = os.getenv("X_BEARER_TOKEN", "")

settings = Settings()
