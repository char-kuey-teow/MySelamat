import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration settings"""
    def load_bedrock_config():
        path = Path(__file__).parent.absolute()
        with open(path / "bedrock_config.json", encoding="utf-8") as f:
            return json.load(f)

    # API Keys
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
    TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
    TWITTER_API_SECRET_KEY = os.getenv("TWITTER_API_SECRET_KEY")
    TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    WEATHER_LOCATION_KB_ID = os.getenv("WEATHER_LOCATION_KB_ID")
    ENDPOINT_NAME = os.getenv("ENDPOINT_NAME")
    BEDROCK_CONFIG = load_bedrock_config()