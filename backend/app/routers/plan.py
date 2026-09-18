from fastapi import APIRouter, HTTPException, Query

from .. import config
from ..network_data import STATIONS
from ..services import datamall, route_planner, advice_engine

router = APIRouter()


def _validate_scenario(scenario: str) -> str:
    if scenario not in config.VALID_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"scenario must be one of {sorted(config.VALID_SCENARIOS)}")
    return scenario


@router.get("/plan")
async def plan(
    origin: str = Query(..., description="Station name, e.g. 'Jurong East'"),
    destination: str = Query(..., description="Station name, e.g. 'Punggol'"),
    scenario: str = Query(default=None),
):
    """
    The general "pick any two stations, get the best route" case (as
    opposed to /journey, which is Rachel's fixed persona demo). No fixed
    schedule here, so advice is delay-based rather than
    deadline-based -- see advice_engine.build_disruption_advice.
    """
    scenario = _validate_scenario(scenario or config.DEFAULT_SCENARIO)

    if origin not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown origin station: {origin!r}")
    if destination not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Unknown destination station: {destination!r}")
    if origin == destination:
        raise HTTPException(status_code=400, detail="Origin and destination must be different stations")

    alerts = await datamall.get_train_service_alerts(scenario)

    try:
        planned, alternative = route_planner.plan_trip(origin, destination, alerts)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    advice = advice_engine.build_disruption_advice(planned, alternative)

    return {
        "scenario": scenario,
        "origin": origin,
        "destination": destination,
        "routes": [planned] + ([alternative] if alternative else []),
        "recommended_route_id": (advice or {}).get("recommended_route_id", "planned"),
        "advice": advice,
        "raw_alerts": alerts,
    }
