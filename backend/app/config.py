import os
from pathlib import Path

from dotenv import load_dotenv

# backend/.env (not backend/app/.env)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _bool(env_val: str | None, default: bool) -> bool:
    if env_val is None:
        return default
    return env_val.strip().lower() in {"1", "true", "yes", "on"}


USE_MOCK = _bool(os.getenv("USE_MOCK"), True)
LTA_ACCOUNT_KEY = os.getenv("LTA_ACCOUNT_KEY", "")
ONEMAP_EMAIL = os.getenv("ONEMAP_EMAIL", "")
ONEMAP_PASSWORD = os.getenv("ONEMAP_PASSWORD", "")
DEFAULT_SCENARIO = os.getenv("DEMO_SCENARIO", "normal")

LTA_BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"
ONEMAP_BASE_URL = "https://www.onemap.gov.sg/api"
WEATHER_BASE_URL = "https://api-open.data.gov.sg/v2/real-time/api"

VALID_SCENARIOS = {"normal", "disruption", "crowded", "rain"}
