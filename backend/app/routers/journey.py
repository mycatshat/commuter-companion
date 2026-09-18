from fastapi import APIRouter, HTTPException, Query

from .. import config
from ..stations import RACHEL_JOURNEY
from ..services import datamall, weather, route_planner, advice_engine

router = APIRouter()


def _validate_scenario(scenario: str) -> str:
    if scenario not in config.VALID_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"scenario must be one of {sorted(config.VALID_SCENARIOS)}")
    return scenario


@router.get("/journey")
async def get_journey(scenario: str = Query(default=None)):
    """
    Everything the frontend needs for Rachel's journey screen in one call:
    the planned route, an alternative (if warranted), current + forecast
    crowding, and the proactive advice banner (or null, if there's nothing
    worth interrupting her for).
    """
    scenario = _validate_scenario(scenario or config.DEFAULT_SCENARIO)

    alerts = await datamall.get_train_service_alerts(scenario)
    pcd_now = await datamall.get_pcd_realtime("EWL", scenario)
    pcd_forecast = await datamall.get_pcd_forecast("EWL", scenario)
    wx = await weather.get_nowcast(scenario)

    planned, alternative = await route_planner.build_rachel_journey(alerts)
    advice = advice_engine.build_rachel_advice(scenario, planned, alternative, pcd_now, pcd_forecast, wx)

    return {
        "scenario": scenario,
        "persona": RACHEL_JOURNEY["persona"],
        "journey_meta": RACHEL_JOURNEY,
        "routes": [planned] + ([alternative] if alternative else []),
        "recommended_route_id": (advice or {}).get("recommended_route_id", "planned"),
        "advice": advice,
        "crowd_now": route_planner.crowd_lookup(pcd_now),
        "crowd_forecast": pcd_forecast,
        "raw_alerts": alerts,  # kept for judges/debugging -- see AlertsPanel in the frontend
        "weather": wx,
    }
