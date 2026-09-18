"""
Regression check for the core logic (route_planner / advice_engine /
graph / mock_data) -- deliberately independent of fastapi/uvicorn, so it
can run anywhere Python + httpx + python-dotenv are available, before the
rest of requirements.txt is installed.

Two parts:
  1. Rachel's persona journey (/journey), all four demo scenarios, same
     assertions as before -- her app must stay silent on a normal day, must
     recommend a specific action for a real disruption, etc.
  2. The general network-wide planner (/plan, `route_planner.plan_trip`):
     a same-line trip, a trip that needs interchanges, a trip untouched by
     a disruption elsewhere on the network (must NOT show advice -- a
     disruption on the EWL shouldn't bother someone going Jurong East to
     Punggol), and a trip that IS hit by the disruption (must reroute).

Run from backend/:   python3 tests/test_logic.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config
from app.services import datamall, weather, route_planner, advice_engine, graph


async def run_rachel_scenario(scenario: str):
    print(f"\n{'=' * 60}\nRACHEL SCENARIO: {scenario}\n{'=' * 60}")
    alerts = await datamall.get_train_service_alerts(scenario)
    pcd_now = await datamall.get_pcd_realtime("EWL", scenario)
    pcd_forecast = await datamall.get_pcd_forecast("EWL", scenario)
    wx = await weather.get_nowcast(scenario)

    assert alerts["Status"] in (1, 2)
    assert len(pcd_now["value"]) == 13, "expected 13 EWL stations Tampines->Raffles Place"
    assert len(pcd_forecast["value"]) == 6, "expected 6 x 30-min forecast blocks (06:30-09:30)"

    planned, alternative = await route_planner.build_rachel_journey(alerts)
    advice = advice_engine.build_rachel_advice(scenario, planned, alternative, pcd_now, pcd_forecast, wx)

    print(f"planned: {planned['total_duration_s']/60:.1f} min "
          f"(+/-{planned['uncertainty_s']/60:.1f} min), "
          f"disruption={planned['has_disruption']}, legs={len(planned['legs'])}")
    assert planned["total_duration_s"] > 0
    assert planned["legs"][0]["mode"] == "walk"
    assert planned["legs"][-1]["mode"] == "walk"

    if alternative:
        modes = [l["mode"] for l in alternative["legs"]]
        print(f"alternative: {alternative['total_duration_s']/60:.1f} min, legs={modes}, label={alternative['label']!r}")
        assert alternative["legs"][0]["mode"] == "walk"
        assert alternative["legs"][-1]["mode"] == "walk"
    else:
        print("alternative: (none)")

    if advice:
        print(f"advice [{advice['severity']}]: {advice['headline']}")
        assert advice["headline"]
        assert advice["reason"] in ("disruption", "crowding", "weather")
    else:
        print("advice: (silent -- nothing worth interrupting Rachel for)")

    if scenario == "normal":
        assert advice is None, "normal day should be silent (Section 2.2: Rachel)"
    if scenario == "disruption":
        assert planned["has_disruption"] is True
        assert alternative is not None
        assert advice is not None and advice["reason"] == "disruption"
        # LTA named Eunos/Paya Lebar/Aljunied as free-boarding points in the
        # mock notice, so the local bus bridge should win over the much
        # longer full-network reroute for this specific trip.
        assert any(l["mode"] == "bus" for l in alternative["legs"]), "expected the free-bus bridge to be the chosen alternative here"
    if scenario == "crowded":
        assert planned["has_disruption"] is False
        assert advice is not None and advice["reason"] == "crowding"
    if scenario == "rain":
        assert planned["has_disruption"] is False
        assert advice is not None and advice["reason"] == "weather"

    print("OK")


async def run_network_tests():
    print(f"\n{'=' * 60}\nNETWORK-WIDE GRAPH / PLANNER\n{'=' * 60}")

    # Same-line trip.
    hops = graph.shortest_path("Tampines", "Raffles Place")
    assert hops is not None and len(hops) == 12
    assert {h.line for h in hops} == {"EWL"}
    print(f"Tampines -> Raffles Place: {sum(h.duration_s for h in hops)/60:.1f} min, all EWL -- OK")

    # Trip that needs interchanges.
    hops = graph.shortest_path("Jurong East", "Punggol")
    assert hops is not None
    lines_used = []
    for h in hops:
        if not lines_used or lines_used[-1] != h.line:
            lines_used.append(h.line)
    assert len(lines_used) >= 2, f"expected a multi-line trip, got {lines_used}"
    print(f"Jurong East -> Punggol: {len(hops)} hops via {lines_used} -- OK")

    # A trip nowhere near the EWL disruption must not be affected by it.
    alerts = await datamall.get_train_service_alerts("disruption")
    planned, alternative = route_planner.plan_trip("Jurong East", "Punggol", alerts)
    assert planned["has_disruption"] is False, "an EWL disruption should not affect a Jurong East -> Punggol trip"
    assert alternative is None
    advice = advice_engine.build_disruption_advice(planned, alternative)
    assert advice is None
    print("Jurong East -> Punggol under EWL disruption: correctly unaffected, silent -- OK")

    # A trip that DOES cross the disrupted EWL segment must reroute.
    planned2, alternative2 = route_planner.plan_trip("Tampines", "Raffles Place", alerts)
    assert planned2["has_disruption"] is True
    assert alternative2 is not None
    advice2 = advice_engine.build_disruption_advice(planned2, alternative2)
    assert advice2 is not None and advice2["reason"] == "disruption"
    print(f"Tampines -> Raffles Place under EWL disruption (no schedule): {advice2['headline']!r} -- OK")

    # Unknown station should raise, not silently return nonsense.
    try:
        route_planner.plan_trip("Nonexistent Station", "Raffles Place", alerts)
        raise AssertionError("expected ValueError for unknown station")
    except ValueError:
        print("Unknown station correctly raises ValueError -- OK")


async def main():
    print(f"USE_MOCK={config.USE_MOCK}")
    for scenario in ["normal", "disruption", "crowded", "rain"]:
        await run_rachel_scenario(scenario)
    await run_network_tests()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
