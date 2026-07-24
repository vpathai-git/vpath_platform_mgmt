"""
Configuration settings for the project.

Loads configuration from environment variables (and a .env file via
python-dotenv) and provides defaults for development. Import-time behavior is
limited to reading values — call ensure_dirs() explicitly before using the
file paths.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Application settings
APP_NAME = os.getenv("APP_NAME", "YourProjectName")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"  # secure default: off
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# File paths
DATA_PATH = Path(os.getenv("DATA_PATH", str(BASE_DIR / "data")))
LOG_PATH = Path(os.getenv("LOG_PATH", str(BASE_DIR / "logs")))

# Feature flags
ENABLE_FEATURE_X = os.getenv("ENABLE_FEATURE_X", "False").lower() == "true"

# External service configuration
SERVICE_URL = os.getenv("SERVICE_URL", "https://api.example.com")
API_KEY = os.getenv("API_KEY", "")

# Timeout and retry settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "30"))

# Database configuration (if needed)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_PATH}/app.db")


def ensure_dirs() -> None:
    """Create the data and log directories. Call once at application startup."""
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    LOG_PATH.mkdir(parents=True, exist_ok=True)
