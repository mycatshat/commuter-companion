"""
Thin wrapper over LTA DataMall.

Every function returns the mock fixture (app/mock_data.py) when
config.USE_MOCK is true, or calls the real endpoint with the AccountKey
header otherwise. This means route_planner.py / advice_engine.py / the
routers never need to know which mode is active -- swapping in real keys
in backend/.env is the only change needed to go live.
"""

import httpx

from .. import config
from .. import mock_data

_DEFAULT_ALERTS = {"Status": 1, "AffectedSegments": [], "Message": []}


def _headers() -> dict:
    return {"AccountKey": config.LTA_ACCOUNT_KEY, "accept": "application/json"}


async def _get(path: str, params: dict | None = None) -> dict:
    url = f"{config.LTA_BASE_URL}/{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=_headers(), params=params or {})
        resp.raise_for_status()
        return resp.json()


async def get_train_service_alerts(scenario: str) -> dict:
    if config.USE_MOCK:
        return mock_data.train_service_alerts(scenario)
    # The real endpoint's "value" field has been observed as either a
    # single-item list or a bare object depending on the exact response --
    # handle both so route_planner/advice_engine always get the flat shape
    # they expect (mirroring mock_data.train_service_alerts).
    data = await _get("TrainServiceAlerts")
    value = data.get("value")
    if isinstance(value, list):
        return value[0] if value else _DEFAULT_ALERTS
    if isinstance(value, dict):
        return value
    return _DEFAULT_ALERTS


async def get_pcd_realtime(train_line: str, scenario: str) -> dict:
    if config.USE_MOCK:
        return mock_data.pcd_realtime(scenario)
    return await _get("PCDRealTime", {"TrainLine": train_line})


async def get_pcd_forecast(train_line: str, scenario: str) -> dict:
    if config.USE_MOCK:
        return mock_data.pcd_forecast(scenario)
    return await _get("PCDForecast", {"TrainLine": train_line})


async def get_bus_arrival(bus_stop_code: str, scenario: str) -> dict:
    if config.USE_MOCK:
        return mock_data.bus_arrival(bus_stop_code, scenario)
    return await _get("v3/BusArrival", {"BusStopCode": bus_stop_code})


async def get_facilities_maintenance(scenario: str) -> dict:
    if config.USE_MOCK:
        return mock_data.facilities_maintenance(scenario)
    return await _get("v2/FacilitiesMaintenance")
