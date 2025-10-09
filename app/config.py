import logging
import os
from typing import List

DEFAULT_SQLITE_URL = "sqlite:///./legendai.db"


def get_database_url() -> str:
    db = os.getenv("DATABASE_URL")
    if not db:
        legacy = os.getenv("SERVICE_DATABASE_URL")
        if legacy:
            logging.warning("Using legacy SERVICE_DATABASE_URL; please rename to DATABASE_URL.")
            db = legacy
    if not db:
        logging.warning("DATABASE_URL missing; defaulting to %s", DEFAULT_SQLITE_URL)
        db = DEFAULT_SQLITE_URL
    return db


def allowed_origins() -> List[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


def mock_enabled() -> bool:
    return os.getenv("LEGEND_MOCK_MODE", "0") == "1" or os.getenv("LEGEND_MOCK", "0") == "1"
