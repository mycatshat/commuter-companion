"""
Door-to-door route planning over the full station graph.

Two entry points:
  plan_trip()      -- general "pick any station, get the best route" case.
                       No fixed schedule, no walking legs (see README "Known
                       limitations": door-to-door for an arbitrary address
                       would need geocoding a free-text address, which isn't
                       wired up -- this plans station-to-station).
  build_rachel_journey() -- Rachel's fixed persona demo: her real walking
                       legs at each end, plus the schedule-aware "does this
                       delay actually cost her the 08:45 meeting" framing
                       that plan_trip() doesn't need for an arbitrary trip.

Both funnel through the same core: find the route a commuter would
normally take (graph.shortest_path, entirely disruption-unaware), then
lay today's disruption on top of THAT specific route -- rather than asking
the search to route around it by itself, which would silently swap the
whole trip for an unrelated one whenever the arithmetic favoured it (see
graph.py's docstring). If today's route does cross a disruption, two
candidate alternatives are computed and the cheaper one is returned:
  (a) the local "bridge" over just the disrupted stretch, riding the free
      bus/shuttle DataMall itself reports (FreePublicBus / FreeMRTShuttle)
      -- "the mitigation is in the feed" (Section 2.4).
  (b) a full network reroute avoiding the disrupted edges entirely.
"""

import re

from ..line_mapping import ALERTS_CODE_TO_CANONICAL, crowd_level_label
from ..network_data import EDGES, STATIONS
from ..stations import RACHEL_JOURNEY
from . import graph, onemap

DOOR_TO_STATION_BUFFER_S = 60  # entering/exiting the station, finding the platform


def _extract_added_minutes(message_content: str) -> int:
    """See README / original docstring: a small deterministic heuristic
    ("please add N minutes") rather than an LLM call, on the reasoning that
    real TrainServiceAlerts notices are formulaic enough that a model would
    mostly re-derive a number this gets in <1ms."""
    m = re.search(r"add\s+(\d+)\s+minutes?", message_content, re.IGNORECASE)
    return int(m.group(1)) if m else 15


def compute_disrupted_edges(alerts: dict) -> tuple[set, dict]:
    """
    Returns (disrupted_edges, segments_by_line):
      disrupted_edges: set of (line, code_from, code_to) -- every graph
        edge whose both endpoints fall within a reported AffectedSegments
        station list, on a matching line. Network-wide, not EWL-specific.
      segments_by_line: canonical_line -> the raw AffectedSegments entry
        (for reading FreePublicBus / FreeMRTShuttle when building the
        local-bridge alternative).
    """
    disrupted_edges = set()
    segments_by_line: dict[str, dict] = {}

    for seg in alerts.get("AffectedSegments", []):
        alerts_code = seg.get("Line")
        station_codes = {s.strip() for s in seg.get("Stations", "").split(",") if s.strip()}
        candidate_lines = ALERTS_CODE_TO_CANONICAL.get(alerts_code, [])
        for _path_key, line, c1, _n1, c2, _n2 in EDGES:
            if line in candidate_lines and c1 in station_codes and c2 in station_codes:
                disrupted_edges.add((line, c1, c2))
                segments_by_line[line] = seg

    return disrupted_edges, segments_by_line


def _hops_to_legs(hops: list, disrupted_edges: set, delay_s_per_edge: int) -> list[dict]:
    """Group consecutive same-line hops into one leg per continuous ride
    (e.g. 'EWL, Tampines -> Buona Vista, 4 stops') rather than one leg per
    station-to-station hop -- matches how a commuter actually experiences
    the trip, and how real transit apps present it."""
    legs = []
    i = 0
    while i < len(hops):
        line = hops[i].line
        j = i
        points = [[STATIONS[hops[i].name_from]["lat"], STATIONS[hops[i].name_from]["lon"]]]
        duration_s = 0
        any_affected = False
        while j < len(hops) and hops[j].line == line:
            affected = graph.is_affected(hops[j].line, hops[j].code_from, hops[j].code_to, disrupted_edges)
            duration_s += hops[j].duration_s + (delay_s_per_edge if affected else 0)
            any_affected = any_affected or affected
            points.append([STATIONS[hops[j].name_to]["lat"], STATIONS[hops[j].name_to]["lon"]])
            j += 1
        legs.append(
            {
                "mode": "rail",
                "line": line,
                "from": {"code": hops[i].code_from, "name": hops[i].name_from, **_latlon(hops[i].name_from)},
                "to": {"code": hops[j - 1].code_to, "name": hops[j - 1].name_to, **_latlon(hops[j - 1].name_to)},
                "stops": j - i,
                "duration_s": duration_s,
                "affected": any_affected,
                "points": points,
            }
        )
        i = j
    return legs


def _latlon(name: str) -> dict:
    s = STATIONS[name]
    return {"lat": s["lat"], "lon": s["lon"]}


def _route_dict(route_id: str, label: str, legs: list[dict]) -> dict:
    total_s = sum(l["duration_s"] for l in legs)
    has_walk = any(l["mode"] == "walk" for l in legs)
    if has_walk:
        total_s += 2 * DOOR_TO_STATION_BUFFER_S
    affected_stations = sorted(
        {s for l in legs if l.get("affected") for s in (l["from"]["name"], l["to"]["name"])}
    )
    return {
        "id": route_id,
        "label": label,
        "legs": legs,
        "total_duration_s": total_s,
        "uncertainty_s": max(120, int(total_s * 0.08)),
        "has_disruption": any(l.get("affected") for l in legs),
        "affected_stations": affected_stations,
    }


def _local_bridge_alternative(hops: list, disrupted_edges: set, segments_by_line: dict, delay_s_per_edge: int) -> list | None:
    """Ride the habitual route right up to the disrupted stretch, bridge it
    with the free bus/shuttle DataMall reports, then resume the habitual
    route. Only applies when the habitual route's disrupted hops are a
    single contiguous run AND the feed names a free-boarding mitigation."""
    flags = [graph.is_affected(h.line, h.code_from, h.code_to, disrupted_edges) for h in hops]
    if not any(flags):
        return None
    first = flags.index(True)
    last = len(flags) - 1 - flags[::-1].index(True)
    if any(not f for f in flags[first : last + 1]):
        return None  # not contiguous -- bail, network reroute will cover it

    line = hops[first].line
    seg = segments_by_line.get(line)
    if not seg:
        return None

    free_bus_stations = {s.strip() for s in seg.get("FreePublicBus", "").split(",") if s.strip() and "island wide" not in s.lower()}
    bridge_from = hops[first].name_from
    bridge_to = hops[last].name_to
    both_confirmed_free = bridge_from in free_bus_stations and bridge_to in free_bus_stations
    if not both_confirmed_free:
        return None  # the feed doesn't actually name this exact bridge -- don't guess

    pre_hops = hops[:first]
    post_hops = hops[last + 1 :]

    legs = []
    if pre_hops:
        legs.extend(_hops_to_legs(pre_hops, disrupted_edges, delay_s_per_edge))
    legs.append(
        {
            "mode": "bus",
            "label": f"Free bus, {bridge_from} → {bridge_to}",
            "from": {"code": hops[first].code_from, "name": bridge_from, **_latlon(bridge_from)},
            "to": {"code": hops[last].code_to, "name": bridge_to, **_latlon(bridge_to)},
            "duration_s": max(1, last - first + 1) * 4 * 60,  # ~4 min/stop-equivalent by road
            "free": True,
            "note": "Free boarding activated by LTA for this disruption (FreePublicBus in TrainServiceAlerts).",
            "affected": False,
        }
    )
    if post_hops:
        legs.extend(_hops_to_legs(post_hops, disrupted_edges, delay_s_per_edge))
    return legs


def _build_alternative(hops: list, disrupted_edges: set, segments_by_line: dict, delay_s_per_edge: int, origin: str, destination: str) -> dict | None:
    if not any(graph.is_affected(h.line, h.code_from, h.code_to, disrupted_edges) for h in hops):
        return None

    candidates = []

    bridge_legs = _local_bridge_alternative(hops, disrupted_edges, segments_by_line, delay_s_per_edge)
    if bridge_legs:
        candidates.append(_route_dict("alternative", "Alternative: free bus around the disruption", bridge_legs))

    reroute_hops = graph.shortest_path_avoiding(origin, destination, disrupted_edges)
    if reroute_hops:
        reroute_legs = _hops_to_legs(reroute_hops, set(), 0)
        lines_used = sorted({l["line"] for l in reroute_legs})
        candidates.append(
            _route_dict("alternative", f"Alternative: via {', '.join(lines_used)}", reroute_legs)
        )

    if not candidates:
        return None
    return min(candidates, key=lambda r: r["total_duration_s"])


def plan_trip(origin: str, destination: str, alerts: dict) -> tuple[dict, dict | None]:
    """General case: station name -> station name, no fixed schedule."""
    hops = graph.shortest_path(origin, destination)
    if hops is None:
        raise ValueError(f"No route found between {origin!r} and {destination!r}")

    disrupted_edges, segments_by_line = compute_disrupted_edges(alerts)
    route_hops_affected = sum(1 for h in hops if graph.is_affected(h.line, h.code_from, h.code_to, disrupted_edges))
    added_minutes = 0
    if route_hops_affected and alerts.get("Message"):
        added_minutes = _extract_added_minutes(alerts["Message"][0]["Content"])
    delay_s_per_edge = int(added_minutes * 60 / route_hops_affected) if route_hops_affected else 0

    legs = _hops_to_legs(hops, disrupted_edges, delay_s_per_edge)
    planned = _route_dict("planned", f"{origin} → {destination}", legs)
    planned["added_minutes"] = added_minutes

    alternative = _build_alternative(hops, disrupted_edges, segments_by_line, delay_s_per_edge, origin, destination)
    if alternative:
        alternative["added_minutes"] = 0

    return planned, alternative


async def build_rachel_journey(alerts: dict) -> tuple[dict, dict | None]:
    """Rachel's persona demo: real walking legs + the graph search for the
    EWL corridor (which, absent a disruption crossing another line, will
    naturally return her usual all-EWL route -- the graph doesn't need to
    be told she's an EWL-only commuter, it just happens to be the fastest
    way from Tampines to Raffles Place on a normal day)."""
    j = RACHEL_JOURNEY
    origin_name = STATIONS_NAME_BY_CODE[j["origin_station"]]
    dest_name = STATIONS_NAME_BY_CODE[j["destination_station"]]

    hops = graph.shortest_path(origin_name, dest_name)
    if hops is None:
        raise ValueError("No route found for Rachel's journey -- network data problem")

    disrupted_edges, segments_by_line = compute_disrupted_edges(alerts)
    route_hops_affected = sum(1 for h in hops if graph.is_affected(h.line, h.code_from, h.code_to, disrupted_edges))
    added_minutes = 0
    if route_hops_affected and alerts.get("Message"):
        added_minutes = _extract_added_minutes(alerts["Message"][0]["Content"])
    delay_s_per_edge = int(added_minutes * 60 / route_hops_affected) if route_hops_affected else 0

    origin_st = STATIONS[origin_name]
    dest_st = STATIONS[dest_name]
    walk_in = await _walk_leg("Home to Tampines MRT", (j["origin"]["lat"], j["origin"]["lon"]), (origin_st["lat"], origin_st["lon"]))
    walk_out = await _walk_leg("Raffles Place MRT to office", (dest_st["lat"], dest_st["lon"]), (j["destination"]["lat"], j["destination"]["lon"]))

    rail_legs = _hops_to_legs(hops, disrupted_edges, delay_s_per_edge)
    planned = _route_dict("planned", "Your usual route", [walk_in, *rail_legs, walk_out])
    planned["added_minutes"] = added_minutes

    alt_core = _build_alternative(hops, disrupted_edges, segments_by_line, delay_s_per_edge, origin_name, dest_name)
    alternative = None
    if alt_core:
        alternative = _route_dict("alternative", alt_core["label"], [walk_in, *alt_core["legs"], walk_out])
        alternative["added_minutes"] = 0

    return planned, alternative


async def _walk_leg(label: str, start_latlon, end_latlon) -> dict:
    route = await onemap.get_walk_route(start_latlon, end_latlon)
    return {
        "mode": "walk",
        "label": label,
        "points": route["points"],
        "distance_m": route["distance_m"],
        "duration_s": route["duration_s"],
        "affected": False,
    }


def crowd_lookup(pcd: dict) -> dict:
    """Station code -> {"level": "h", "label": "High"} for quick UI lookup."""
    out = {}
    for row in pcd.get("value", []):
        out[row["Station"]] = {"level": row["CrowdLevel"], "label": crowd_level_label(row["CrowdLevel"])}
    return out


STATIONS_NAME_BY_CODE = {code: name for name, s in STATIONS.items() for code in s["codes"]}
