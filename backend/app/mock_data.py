"""
Mock data matching the real DataMall / data.gov.sg response shapes.

Used whenever USE_MOCK=true (the default -- see .env.example). Every
function here returns exactly the JSON shape documented in the LTA DataMall
API User Guide v6.8 / the OpenAPI specs bundled with the problem statement,
so `services/datamall.py` and `services/weather.py` can be pointed at the
real endpoints later with zero changes to any caller.

Four demo scenarios (Section 2.6 of the brief explicitly allows a labelled
injected/replay scenario, since TrainServiceAlerts.AffectedSegments is
empty on an ordinary day):

  normal      - everything running fine, nothing proactive to say
  disruption  - signalling fault on EWL between Eunos and Aljunied
                (squarely on Rachel's route)
  crowded     - no disruption, but the 07:30-08:00 forecast for Tampines
                platform is "high" -- the proactive-before-anything-breaks
                case
  rain        - heavy rain over Tampines, affecting the walking legs
"""

from datetime import datetime, timedelta, timezone

from .stations import EWL_TAMPINES_TO_RAFFLES_PLACE

SGT = timezone(timedelta(hours=8))


def _now_sgt() -> datetime:
    return datetime.now(SGT)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")


# ---------------------------------------------------------------------------
# TrainServiceAlerts
# ---------------------------------------------------------------------------

def train_service_alerts(scenario: str) -> dict:
    now = _now_sgt()

    if scenario == "disruption":
        return {
            "Status": 2,
            "AffectedSegments": [
                {
                    "Line": "EWL",
                    "Direction": "Both",
                    "Stations": "EW7,EW8,EW9",
                    "FreePublicBus": "Eunos, Paya Lebar, Aljunied",
                    "FreeMRTShuttle": "NIL",
                    "MRTShuttleDirection": "NA",
                }
            ],
            "Message": [
                {
                    "Content": (
                        f"({now.strftime('%d %b %H:%M')}) Due to a signalling fault, "
                        "EWL train services between Eunos and Aljunied stations are "
                        "running at about 18-20 min intervals. Free regular bus "
                        "services are available at Eunos, Paya Lebar and Aljunied "
                        "MRT stations. Please add 20 minutes to your travel time."
                    ),
                    "CreatedDate": _iso(now - timedelta(minutes=6)),
                }
            ],
            "_scenario": "disruption",
        }

    # normal / crowded / rain all report Status 1 on the train alerts feed --
    # crowding and rain are surfaced through PCDForecast / weather, not
    # through TrainServiceAlerts, which is accurate to how the real feed
    # behaves (it only reports service unavailability, not crowding or
    # weather).
    return {
        "Status": 1,
        "AffectedSegments": [],
        "Message": [
            {
                "Content": (
                    f"({now.strftime('%d %b %H:%M')}) Bus service 15 will be "
                    "diverted due to a road closure along New Bridge Road for "
                    "roadworks. Affected commuters may alight at the bus stop "
                    "before the diversion and walk to their destination."
                ),
                "CreatedDate": _iso(now - timedelta(hours=2)),
            }
        ],
        "_scenario": scenario,
    }


# ---------------------------------------------------------------------------
# PCDRealTime / PCDForecast  (Station Crowd Density)
# ---------------------------------------------------------------------------

def _base_crowd_for_station(code: str, scenario: str, clock_hhmm: str) -> str:
    """
    Deterministic-but-plausible crowd level per station/scenario.

    clock_hhmm is the time-of-day ("HH:MM") the reading applies to -- for
    PCDRealTime that's "right now"; for PCDForecast it's each 30-min
    block's start. Keying off time-of-day rather than distance from the
    real wall-clock means the "crowded" scenario always demonstrates
    correctly against Rachel's fixed 07:40 departure, whatever time of day
    you actually run the demo (Section 2.6 explicitly allows a labelled
    injected scenario for exactly this reason).
    """
    peak_stations = {"EW2", "EW7", "EW8", "EW9", "EW12", "EW13", "EW14"}
    in_am_peak = "07:00" <= clock_hhmm < "08:30"

    if scenario == "crowded" and code == "EW2" and in_am_peak:
        return "h"
    if scenario == "disruption" and code in {"EW7", "EW8", "EW9"}:
        return "h"
    if code in peak_stations and in_am_peak:
        return "m"
    if code in peak_stations:
        return "l"
    return "l"


def pcd_realtime(scenario: str) -> dict:
    now = _now_sgt()
    clock_hhmm = now.strftime("%H:%M")
    stations = []
    for s in EWL_TAMPINES_TO_RAFFLES_PLACE:
        stations.append(
            {
                "Station": s["code"],
                "StartTime": _iso(now),
                "EndTime": _iso(now + timedelta(minutes=10)),
                "CrowdLevel": _base_crowd_for_station(s["code"], scenario, clock_hhmm),
            }
        )
    return {"odata.metadata": "PCDRealTime", "value": stations, "_scenario": scenario}


def pcd_forecast(scenario: str) -> dict:
    """
    Forecast blocks anchored to a fixed 06:30-09:30 morning window (today's
    date, SGT) rather than to the real wall-clock time. The real
    PCDForecast is published once a day for the whole day's service hours;
    a demo fixture that instead chased "now" would only ever show a
    crowded 07:40 platform if you happened to run the demo at 07:40.
    """
    now = _now_sgt()
    base = now.replace(hour=6, minute=30, second=0, microsecond=0)
    forecast = []
    for block in range(6):  # 06:30 .. 09:30
        start = base + timedelta(minutes=30 * block)
        end = start + timedelta(minutes=30)
        clock_hhmm = start.strftime("%H:%M")
        stations = []
        for s in EWL_TAMPINES_TO_RAFFLES_PLACE:
            stations.append(
                {
                    "Station": s["code"],
                    "CrowdLevel": _base_crowd_for_station(s["code"], scenario, clock_hhmm),
                }
            )
        forecast.append(
            {"Interval": {"Start": _iso(start), "End": _iso(end)}, "Stations": stations}
        )
    return {"odata.metadata": "PCDForecast", "value": forecast, "_scenario": scenario}


# ---------------------------------------------------------------------------
# v3/BusArrival -- alternative bus near Eunos/Paya Lebar used when EWL is
# disrupted between EW7-EW9.
# ---------------------------------------------------------------------------

def bus_arrival(bus_stop_code: str, scenario: str) -> dict:
    now = _now_sgt()

    def _svc(no: str, mins: list, load: str, wab: bool, vtype: str):
        arrivals = []
        for m in mins:
            arrivals.append(
                {
                    "EstimatedArrival": _iso(now + timedelta(minutes=m)),
                    "Load": load,
                    "Feature": "WAB" if wab else "",
                    "Type": vtype,
                }
            )
        return {
            "ServiceNo": no,
            "Operator": "SBST",
            "NextBus": arrivals[0] if len(arrivals) > 0 else {},
            "NextBus2": arrivals[1] if len(arrivals) > 1 else {},
            "NextBus3": arrivals[2] if len(arrivals) > 2 else {},
        }

    if scenario == "disruption":
        services = [
            _svc("47", [3, 14, 26], "SDA", True, "SD"),
            _svc("13", [7, 19, 33], "LSD", True, "DD"),
        ]
    else:
        services = [
            _svc("47", [6, 17, 29], "SEA", True, "SD"),
        ]

    return {"BusStopCode": bus_stop_code, "Services": services, "_scenario": scenario}


# ---------------------------------------------------------------------------
# v2/FacilitiesMaintenance -- lift status. Not on Rachel's critical path
# (she doesn't rely on a lift), included so the endpoint/UI has real data to
# show and so the Mdm Lim persona can be picked up later without new mocks.
# ---------------------------------------------------------------------------

def facilities_maintenance(scenario: str) -> dict:
    now = _now_sgt()
    return {
        "value": [
            {
                "StationCode": "EW8",
                "LiftID": "L3",
                "ExitCode": "Exit A",
                "Status": "Under Maintenance",
                "StartDate": _iso(now - timedelta(hours=3)),
                "EstEndDate": _iso(now + timedelta(hours=5)),
            }
        ],
        "_scenario": scenario,
    }


# ---------------------------------------------------------------------------
# data.gov.sg 2-hour nowcast
# ---------------------------------------------------------------------------

def weather_nowcast(scenario: str) -> dict:
    now = _now_sgt()
    if scenario == "rain":
        forecasts = [
            {"area": "Tampines", "forecast": "Heavy Thundery Showers"},
            {"area": "Bedok", "forecast": "Moderate Rain"},
            {"area": "City", "forecast": "Cloudy"},
            {"area": "Raffles Place", "forecast": "Cloudy"},
        ]
    else:
        forecasts = [
            {"area": "Tampines", "forecast": "Partly Cloudy"},
            {"area": "Bedok", "forecast": "Partly Cloudy"},
            {"area": "City", "forecast": "Fair"},
            {"area": "Raffles Place", "forecast": "Fair"},
        ]
    return {
        "code": 0,
        "data": {
            "area_metadata": [],
            "items": [{"timestamp": _iso(now), "forecasts": forecasts}],
        },
        "_scenario": scenario,
    }
