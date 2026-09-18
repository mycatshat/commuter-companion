"""
Station-graph pathfinding over the full MRT/LRT network (network_data.py).

Each graph node is a physical station (by name); interchange stations
naturally become junctions because they appear in more than one line's
edge list under the same name. Dijkstra runs over (station, arrived_on_line)
states rather than bare stations, so a same-line continuation and a
line-change at an interchange can be weighted differently (the interchange
transfer penalty below) -- a standard technique for transit routing.

Two searches are exposed:
  shortest_path()          -- plain Dijkstra, entirely disruption-unaware.
                               This is "the route you'd normally take" --
                               route_planner.py applies today's delay to
                               whichever of ITS edges happen to be
                               disrupted, rather than asking the search
                               itself to reroute. (An earlier version let
                               disrupted edges cost extra *inside* the
                               search instead, but that lets Dijkstra
                               silently swap Rachel's EWL trip for an
                               unrelated DTL/TEL path whenever the numbers
                               favour it -- technically "optimal", but not
                               what "your usual route, delayed" means to a
                               commuter. Keeping the two searches separate
                               keeps that distinction legible.)
  shortest_path_avoiding() -- disrupted edges are removed entirely, for the
                               "alternative route" recommendation.
"""

import heapq
from collections import defaultdict
from dataclasses import dataclass, field

from ..network_data import EDGES, STATIONS

MRT_SECONDS_PER_STOP = 130  # ~2.2 min, typical MRT dwell+run time
LRT_SECONDS_PER_STOP = 90   # LRT hops are shorter
INTERCHANGE_PENALTY_S = 4 * 60  # walking + waiting time when changing lines

LRT_LINES = {"BPL", "SLRT", "PLRT"}


@dataclass
class Edge:
    to: str
    line: str
    code_from: str
    code_to: str
    duration_s: int


def _base_duration(line: str) -> int:
    return LRT_SECONDS_PER_STOP if line in LRT_LINES else MRT_SECONDS_PER_STOP


def build_graph() -> dict[str, list[Edge]]:
    graph: dict[str, list[Edge]] = defaultdict(list)
    for _path_key, line, c1, n1, c2, n2 in EDGES:
        w = _base_duration(line)
        graph[n1].append(Edge(to=n2, line=line, code_from=c1, code_to=c2, duration_s=w))
        graph[n2].append(Edge(to=n1, line=line, code_from=c2, code_to=c1, duration_s=w))
    return graph


# Built once at import time -- network_data.py is static.
GRAPH = build_graph()


@dataclass
class PathHop:
    line: str
    code_from: str
    name_from: str
    code_to: str
    name_to: str
    duration_s: int
    affected: bool


def is_affected(line: str, code_from: str, code_to: str, disrupted_edges: set) -> bool:
    return (line, code_from, code_to) in disrupted_edges or (line, code_to, code_from) in disrupted_edges


def _dijkstra(origin: str, destination: str, excluded_edges: set) -> list[PathHop] | None:
    """excluded_edges: set of (line, code_from, code_to) tuples to exclude
    entirely (both directions checked). Empty set = plain, disruption-unaware
    search."""
    if origin not in STATIONS or destination not in STATIONS:
        return None

    # state key: (station, line_arrived_on) -- line_arrived_on is None at the start.
    dist = {(origin, None): 0}
    prev: dict[tuple, tuple] = {}
    pq = [(0, origin, None)]
    visited = set()

    while pq:
        cost, node, line = heapq.heappop(pq)
        if (node, line) in visited:
            continue
        visited.add((node, line))

        if node == destination:
            break

        for edge in GRAPH.get(node, []):
            if excluded_edges and is_affected(edge.line, edge.code_from, edge.code_to, excluded_edges):
                continue
            weight = edge.duration_s
            if line is not None and line != edge.line:
                weight += INTERCHANGE_PENALTY_S
            new_cost = cost + weight
            state = (edge.to, edge.line)
            if new_cost < dist.get(state, float("inf")):
                dist[state] = new_cost
                prev[state] = (node, line, edge)
                heapq.heappush(pq, (new_cost, edge.to, edge.line))

    # Find the best-cost state that reached the destination, on any line.
    best_state = None
    best_cost = float("inf")
    for (node, line), cost in dist.items():
        if node == destination and cost < best_cost:
            best_cost = cost
            best_state = (node, line)

    if best_state is None:
        return None

    # Walk back through `prev` to reconstruct the hop list.
    hops: list[PathHop] = []
    state = best_state
    while state in prev:
        p_node, p_line, edge = prev[state]
        hops.append(
            PathHop(
                line=edge.line,
                code_from=edge.code_from,
                name_from=p_node,
                code_to=edge.code_to,
                name_to=edge.to,
                duration_s=edge.duration_s,
                affected=False,  # caller fills this in against today's disruption, if any
            )
        )
        state = (p_node, p_line)

    hops.reverse()
    return hops


def shortest_path(origin: str, destination: str) -> list[PathHop] | None:
    """Plain Dijkstra, entirely disruption-unaware -- "the route you'd normally take"."""
    return _dijkstra(origin, destination, excluded_edges=set())


def shortest_path_avoiding(origin: str, destination: str, disrupted_edges: set) -> list[PathHop] | None:
    """Dijkstra excluding disrupted edges entirely -- the alternative route."""
    return _dijkstra(origin, destination, excluded_edges=disrupted_edges)


def station_exists(name: str) -> bool:
    return name in STATIONS
