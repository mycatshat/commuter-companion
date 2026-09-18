"""
Proactive decision-support logic.

This is the part of the brief that separates "decision support" from
"status reporting" (Section 1): the app does not just say "line delayed",
it decides whether *this* delay costs *this* commuter their meeting, and if
so, what to do about it in one line.

`build_disruption_advice` is network-wide and schedule-optional -- it works
for Rachel's fixed 07:40/08:45 commute AND for an arbitrary ad-hoc trip
planned through /api/plan (where there's no fixed schedule to weigh the
delay against, only the delay itself). `build_rachel_advice` wraps it and
adds Rachel's persona-specific extras (Section 2.2): the schedule-aware
noise/interrupt framing, plus the two non-disruption cases the brief also
asks for -- a forecast-only crowding warning, and a weather nudge for her
walking legs.
"""

from datetime import datetime

from ..stations import RACHEL_JOURNEY

NOISE_THRESHOLD_MIN = 5          # below this: say nothing
INTERRUPT_THRESHOLD_MIN = 15     # at/above this: this is the headline "interrupt them" case
CROWD_LEAVE_EARLY_MIN = 10       # how much earlier to suggest leaving to dodge a crowded platform


def _budget_minutes() -> int:
    dep = datetime.strptime(RACHEL_JOURNEY["usual_departure"], "%H:%M")
    arr = datetime.strptime(RACHEL_JOURNEY["must_arrive_by"], "%H:%M")
    return int((arr - dep).total_seconds() / 60)


def build_disruption_advice(planned: dict, alternative: dict | None, budget_min: float | None = None) -> dict | None:
    """
    budget_min: minutes between departure and a hard arrival deadline, if
    the trip has one (Rachel does; an ad-hoc /api/plan trip doesn't). When
    None, severity/headline fall back to delay-minutes alone -- still
    useful ("this route is running 20 min slow, here's a faster way"),
    just without the "you'll actually be late" framing that needs a
    deadline to mean anything.
    """
    if not planned["has_disruption"]:
        return None

    delay_min = planned.get("added_minutes", 0)
    if delay_min < NOISE_THRESHOLD_MIN:
        return None  # genuinely noise

    planned_min = planned["total_duration_s"] / 60
    baseline_min = planned_min - delay_min
    slack_min = (budget_min - planned_min) if budget_min is not None else None
    still_late = slack_min is not None and slack_min < 0

    affected_lines = sorted({l["line"] for l in planned["legs"] if l.get("mode") == "rail" and l.get("affected")})
    line_str = "/".join(affected_lines) if affected_lines else "your line"

    if alternative is not None:
        alt_min = alternative["total_duration_s"] / 60
        saves_min = planned_min - alt_min
        worth_switching = saves_min >= 5 or still_late

        if worth_switching:
            bus_leg = next((l for l in alternative["legs"] if l["mode"] == "bus"), None)
            if bus_leg:
                headline = (
                    f"Disruption on {line_str} at {bus_leg['from']['name']} – "
                    f"take the free bus to {bus_leg['to']['name']}, arrive ~{round(alt_min)} min from now"
                )
            else:
                alt_lines = sorted({l["line"] for l in alternative["legs"] if l["mode"] == "rail"})
                headline = (
                    f"Disruption on {line_str} – reroute via {', '.join(alt_lines)}, "
                    f"arrive ~{round(alt_min)} min from now"
                )
            detail = (
                f"Your usual route would take about {round(planned_min)} min today "
                f"(normally {round(baseline_min)}) because of a disruption on {line_str} "
                f"between {', '.join(planned['affected_stations'])}. "
                + (
                    f"This alternative gets you in {round(saves_min)} min sooner."
                    if saves_min > 0
                    else "This alternative avoids the disrupted stretch entirely."
                )
            )
            return {
                "severity": "critical" if still_late else "warning",
                "headline": headline,
                "detail": detail,
                "recommended_route_id": "alternative",
                "reason": "disruption",
            }

    if delay_min >= INTERRUPT_THRESHOLD_MIN or still_late:
        if still_late:
            headline = f"{line_str} delayed ~{delay_min} min near {', '.join(planned['affected_stations'])} – leave now"
        else:
            headline = f"{line_str} running ~{delay_min} min slow today"
            if budget_min is not None:
                headline += " – still on time if you leave now"
        detail = (
            f"Your usual route is taking about {round(planned_min)} min today instead of the usual {round(baseline_min)}. "
        )
        if still_late:
            detail += "You have no buffer left before your scheduled arrival."
        elif slack_min is not None:
            detail += f"You still have about {round(slack_min)} min of buffer."
        return {
            "severity": "critical" if still_late else "warning",
            "headline": headline,
            "detail": detail,
            "recommended_route_id": "planned",
            "reason": "disruption",
        }

    return None  # a few minutes late but well inside buffer -- noise


def build_rachel_advice(scenario: str, planned: dict, alternative: dict | None, crowd_now: dict, crowd_forecast: dict, weather: dict) -> dict | None:
    disruption_advice = build_disruption_advice(planned, alternative, budget_min=_budget_minutes())
    if disruption_advice:
        return disruption_advice
    if planned["has_disruption"]:
        return None  # disrupted but noise-level -- stay silent either way

    # 2. No disruption, but the forecast says her platform will be busy --
    if scenario == "crowded":
        dep_hhmm = RACHEL_JOURNEY["usual_departure"]
        for block in crowd_forecast.get("value", []):
            start = block["Interval"]["Start"][11:16]
            end = block["Interval"]["End"][11:16]
            if start <= dep_hhmm < end:
                tampines = next((s for s in block["Stations"] if s["Station"] == "EW2"), None)
                if tampines and tampines["CrowdLevel"] == "h":
                    return {
                        "severity": "info",
                        "headline": f"Tampines platform will be crowded at {dep_hhmm} – leave {CROWD_LEAVE_EARLY_MIN} min earlier",
                        "detail": (
                            "No service disruption today, but the platform forecast shows "
                            f"high crowding around your usual {dep_hhmm} departure. Leaving "
                            f"{CROWD_LEAVE_EARLY_MIN} min earlier gets you a noticeably quieter platform "
                            "and the same arrival time."
                        ),
                        "recommended_route_id": "planned",
                        "reason": "crowding",
                    }
                break

    # 3. No disruption, no crowding -- but rain affects the walking legs -
    if scenario == "rain":
        tampines_wx = next((f for f in weather.get("data", {}).get("items", [{}])[0].get("forecasts", []) if f["area"] == "Tampines"), None)
        if tampines_wx and any(k in tampines_wx["forecast"].lower() for k in ("rain", "shower", "thunder")):
            walk_leg = planned["legs"][0]
            return {
                "severity": "info",
                "headline": f"{tampines_wx['forecast']} near Tampines – bring an umbrella for the walk to the station",
                "detail": (
                    f"Your {round(walk_leg['distance_m'])} m walk to Tampines MRT will likely be wet. "
                    "This doesn't affect your train time, just budget a couple of extra minutes."
                ),
                "recommended_route_id": "planned",
                "reason": "weather",
            }

    return None
