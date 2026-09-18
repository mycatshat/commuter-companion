"""
Station reference data for the EWL corridor used in Rachel's journey
(Tampines EW2 -> Raffles Place EW14).

IMPORTANT / ASSUMPTION (see README "Known limitations"):
Coordinates below are approximate (hand-placed near each station's real
entrance, accurate to roughly 50-150m) so the map and walking-leg distances
look and behave correctly for a demo. The hackathon repository ships
PS2/data/AmendmenttoMP2014RailStation.geojson with surveyed station
footprint polygons -- that file was not available in this sandbox, so it
was not used here. Before judging/production use, swap these for centroids
(or exit points, via the TrainStationExit GeospatialWholeIsland layer)
computed from that file. The station *codes*, *names* and *line order*
below are real and are the part that matters for the routing/advice logic.
"""

# Ordered west-bound (Tampines -> Raffles Place direction, i.e. "towards
# Tuas Link"), which is Rachel's direction of travel every weekday morning.
EWL_TAMPINES_TO_RAFFLES_PLACE = [
    {"code": "EW2", "name": "Tampines", "lat": 1.3546, "lon": 103.9437},
    {"code": "EW3", "name": "Simei", "lat": 1.3430, "lon": 103.9530},
    {"code": "EW4", "name": "Tanah Merah", "lat": 1.3272, "lon": 103.9463},
    {"code": "EW5", "name": "Bedok", "lat": 1.3240, "lon": 103.9300},
    {"code": "EW6", "name": "Kembangan", "lat": 1.3208, "lon": 103.9128},
    {"code": "EW7", "name": "Eunos", "lat": 1.3197, "lon": 103.9030},
    {"code": "EW8", "name": "Paya Lebar", "lat": 1.3177, "lon": 103.8925},
    {"code": "EW9", "name": "Aljunied", "lat": 1.3164, "lon": 103.8827},
    {"code": "EW10", "name": "Kallang", "lat": 1.3115, "lon": 103.8714},
    {"code": "EW11", "name": "Lavender", "lat": 1.3072, "lon": 103.8631},
    {"code": "EW12", "name": "Bugis", "lat": 1.3006, "lon": 103.8559},
    {"code": "EW13", "name": "City Hall", "lat": 1.2931, "lon": 103.8520},
    {"code": "EW14", "name": "Raffles Place", "lat": 1.2839, "lon": 103.8514},
]

# Rachel's fixed door-to-door journey. Home/office coordinates are
# illustrative (placed near real Tampines Ave / Raffles Place addresses),
# not a real person's address.
RACHEL_JOURNEY = {
    "persona": "rachel",
    "origin": {
        "label": "Home (Tampines Ave 4)",
        "lat": 1.3560,
        "lon": 103.9450,
    },
    "origin_station": "EW2",
    "destination_station": "EW14",
    "destination": {
        "label": "Office (Raffles Place)",
        "lat": 1.2838,
        "lon": 103.8511,
    },
    "usual_departure": "07:40",
    "must_arrive_by": "08:45",
}


def station_by_code(code: str):
    for s in EWL_TAMPINES_TO_RAFFLES_PLACE:
        if s["code"] == code:
            return s
    return None
