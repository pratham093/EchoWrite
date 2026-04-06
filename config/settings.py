"""
EchoWrite Configuration Management
Uses dataclasses + environment variables for clean, typed config.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


@dataclass
class Settings:
    """Central configuration for the EchoWrite system."""

    # --- API Keys ---
    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # --- Model Defaults ---
    MODEL_NAME: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "gemini-2.5-flash"))
    TEMPERATURE: float = field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.7")))
    MAX_OUTPUT_TOKENS: int = field(default_factory=lambda: int(os.getenv("MAX_OUTPUT_TOKENS", "8192")))

    # --- Directory Paths ---
    CONTENT_VERSIONS_DIR: Path = field(
        default_factory=lambda: Path(os.getenv("CONTENT_VERSIONS_DIR", "./content_versions"))
    )
    CHROMA_DB_DIR: Path = field(
        default_factory=lambda: Path(os.getenv("CHROMA_DB_DIR", "./chroma_db"))
    )
    REWARD_DATA_DIR: str = field(
        default_factory=lambda: os.getenv("REWARD_DATA_DIR", "./reward_data")
    )
    SCREENSHOT_DIR: Path = field(
        default_factory=lambda: Path(os.getenv("SCREENSHOT_DIR", "./screenshots"))
    )
    OUTPUT_DIR: Path = field(
        default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "./output"))
    )

    # --- Scraper Settings ---
    SCRAPE_TIMEOUT: int = 30
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # --- RL Settings ---
    EXPLORATION_RATE: float = 0.1
    HUMAN_WEIGHT: float = 0.7
    AI_WEIGHT: float = 0.3

    # --- Voice Settings ---
    VOICE_LANGUAGE: str = "en"
    VOICE_TIMEOUT: int = 5

    def __post_init__(self):
        """Create required directories on init."""
        for dir_path in [
            self.CONTENT_VERSIONS_DIR,
            self.CHROMA_DB_DIR,
            Path(self.REWARD_DATA_DIR),
            self.SCREENSHOT_DIR,
            self.OUTPUT_DIR,
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


# Singleton instance
settings = Settings()
