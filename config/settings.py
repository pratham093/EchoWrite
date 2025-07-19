import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    PROJECT_ROOT = Path(__file__).parent.parent
    SCREENSHOT_DIR = PROJECT_ROOT / "screenshots"
    OUTPUT_DIR = PROJECT_ROOT / "output"
    CONTENT_VERSIONS_DIR = PROJECT_ROOT / "content_versions"
    CHROMA_DB_DIR = PROJECT_ROOT / "chroma_db"
    REWARD_DATA_DIR = PROJECT_ROOT / "reward_data"
    
    DEFAULT_MODEL = "gemini-pro"
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 8192
    
    WEB_SCRAPER_TIMEOUT = 30
    MAX_CONTENT_LENGTH = 10000
    
    VOICE_ENABLED = True
    VOICE_LANGUAGE = "en"

    def __init__(self):
        if not self.GEMINI_API_KEY:
            raise ValueError("❌ GEMINI_API_KEY not found. Please add it to your .env file.")
        
        self.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.CONTENT_VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.REWARD_DATA_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()