"""
OneMap routing (Section 2.3 of the brief) -- used for the door-to-door
walking legs at each end of Rachel's journey.

Real mode: OneMap issues a short-lived bearer token from an email+password
via /api/auth/post/getToken (not a static API key), which this module
fetches once and caches in-process. It then calls the "walk" routing mode
of /api/public/routingsvc/route, which itself uses OSM-derived pedestrian
path data (footways, crossings, etc. -- see Section 2.3), satisfying the
required-OSM-base condition without this backend needing to run its own
OSRM/GraphHopper instance.

Mock mode: no network call. Returns a straight-line path broken into a few
intermediate points so the frontend has a polyline to draw. This is a
known simplification -- see README "Known limitations": it does not
reflect real footpaths, stairs, or covered walkways, and should be replaced
by a real OneMap/OSRM call (or a self-hosted OSRM foot profile over the
Geofabrik SG extract) before this is used for anything but a demo.
"""

import time

import httpx

from .. import config

_token_cache = {"token": None, "expires_at": 0}


async def _get_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    url = f"{config.ONEMAP_BASE_URL}/auth/post/getToken"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            url,
            json={"email": config.ONEMAP_EMAIL, "password": config.ONEMAP_PASSWORD},
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["token"] = data["access_token"]
    # OneMap tokens are typically valid ~3 days; refresh a little early.
    _token_cache["expires_at"] = now + int(data.get("expiry_timestamp", now + 3600)) - now - 300
    return _token_cache["token"]


def _interpolate(start: tuple, end: tuple, steps: int = 4) -> list:
    lat1, lon1 = start
    lat2, lon2 = end
    pts = []
    for i in range(steps + 1):
        t = i / steps
        pts.append([lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t])
    return pts


async def get_walk_route(start: tuple, end: tuple) -> dict:
    """Returns {"points": [[lat, lon], ...], "distance_m": float, "duration_s": float}."""

    if config.USE_MOCK or not (config.ONEMAP_EMAIL and config.ONEMAP_PASSWORD):
        points = _interpolate(start, end, steps=4)
        # Rough haversine so distance/duration are at least the right order
        # of magnitude for a demo.
        import math

        lat1, lon1 = start
        lat2, lon2 = end
        r = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        distance_m = 2 * r * math.asin(math.sqrt(a))
        walking_speed_mps = 1.2  # ~4.3 km/h, a touch slower than brisk to be conservative
        return {
            "points": points,
            "distance_m": round(distance_m, 1),
            "duration_s": round(distance_m / walking_speed_mps, 1),
        }

    token = await _get_token()
    url = f"{config.ONEMAP_BASE_URL}/public/routingsvc/route"
    params = {
        "start": f"{start[0]},{start[1]}",
        "end": f"{end[0]},{end[1]}",
        "routeType": "walk",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params, headers={"Authorization": token})
        resp.raise_for_status()
        data = resp.json()

    # NOTE (see README "Known limitations"): OneMap's walk-route response
    # carries an encoded polyline in route_geometry (Google polyline
    # algorithm, not GeoJSON) which needs a decoder we haven't wired in
    # without a real account to test the exact response shape against.
    # Distance/duration below ARE real, from route_summary; only the
    # intermediate points fall back to a straight line until that decoder
    # is added. This only affects the two ~400m walking legs' polyline
    # shape on the map -- not the timing anywhere else in the app.
    summary = data.get("route_summary", {})
    return {
        "points": [start, end],
        "distance_m": summary.get("total_distance", 0),
        "duration_s": summary.get("total_time", 0),
    }
