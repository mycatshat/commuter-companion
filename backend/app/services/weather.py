"""data.gov.sg weather -- 2-hour nowcast. No API key required in real mode."""

import httpx

from .. import config
from .. import mock_data


async def get_nowcast(scenario: str) -> dict:
    if config.USE_MOCK:
        return mock_data.weather_nowcast(scenario)
    url = f"{config.WEATHER_BASE_URL}/two-hr-forecast"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
