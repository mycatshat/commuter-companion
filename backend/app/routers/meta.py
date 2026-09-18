from fastapi import APIRouter, Query

from ..line_mapping import CANONICAL_LINES
from ..network_data import STATIONS
from .. import config

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "use_mock": config.USE_MOCK, "default_scenario": config.DEFAULT_SCENARIO}


@router.get("/lines")
async def lines():
    return CANONICAL_LINES


@router.get("/stations")
async def stations():
    """Every station in the network (all MRT + LRT lines). ~190 entries --
    mainly useful for debugging/inspection; the frontend uses
    /stations/search for its autocomplete."""
    return [
        {"name": name, "codes": s["codes"], "lines": s["lines"], "lat": s["lat"], "lon": s["lon"]}
        for name, s in sorted(STATIONS.items())
    ]


@router.get("/stations/search")
async def search_stations(q: str = Query(default="", min_length=0, max_length=64), limit: int = Query(default=8, le=25)):
    """Simple substring match on station name (case-insensitive), for the
    destination-picker autocomplete. Matches starting with the query rank
    above matches containing it elsewhere, so typing 'jur' surfaces
    'Jurong East' before something like 'Ang Mo Kio' would ever compete."""
    q = q.strip().lower()
    if not q:
        return []

    starts = []
    contains = []
    for name, s in STATIONS.items():
        low = name.lower()
        entry = {"name": name, "codes": s["codes"], "lines": s["lines"], "lat": s["lat"], "lon": s["lon"]}
        if low.startswith(q):
            starts.append(entry)
        elif q in low:
            contains.append(entry)

    starts.sort(key=lambda e: e["name"])
    contains.sort(key=lambda e: e["name"])
    return (starts + contains)[:limit]
