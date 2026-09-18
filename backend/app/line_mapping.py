"""
Canonical line table.

DataMall is not internally consistent about line codes: the same physical
line is spelled differently depending on which endpoint you call (see
Section 2.4 "A trap" in the problem statement). Everything in this backend
maps through CANONICAL_LINES so the rest of the code only ever deals with
one code per line.

canonical key -> {
    "name": human-readable line name,
    "alerts_code": code used by TrainServiceAlerts,
    "crowd_code":  code used by PCDRealTime / PCDForecast,
    "colour":      official line colour, for the map,
}
"""

CANONICAL_LINES = {
    "NSL": {"name": "North South Line", "alerts_code": "NSL", "crowd_code": "NSL", "colour": "#D42E12"},
    "EWL": {"name": "East West Line", "alerts_code": "EWL", "crowd_code": "EWL", "colour": "#009645"},
    "CGL": {"name": "Changi Extension", "alerts_code": "EWL", "crowd_code": "CGL", "colour": "#009645"},
    "NEL": {"name": "North East Line", "alerts_code": "NEL", "crowd_code": "NEL", "colour": "#9900AA"},
    "CCL": {"name": "Circle Line", "alerts_code": "CCL", "crowd_code": "CCL", "colour": "#FA9E0D"},
    "CEL": {"name": "Circle Line Extension", "alerts_code": "CCL", "crowd_code": "CEL", "colour": "#FA9E0D"},
    "DTL": {"name": "Downtown Line", "alerts_code": "DTL", "crowd_code": "DTL", "colour": "#005EC4"},
    "TEL": {"name": "Thomson-East Coast Line", "alerts_code": "TEL", "crowd_code": "TEL", "colour": "#9D5B25"},
    "BPL": {"name": "Bukit Panjang LRT", "alerts_code": "BPL", "crowd_code": "BPL", "colour": "#748477"},
    "SLRT": {"name": "Sengkang LRT", "alerts_code": "STL", "crowd_code": "SLRT", "colour": "#748477"},
    "PLRT": {"name": "Punggol LRT", "alerts_code": "PTL", "crowd_code": "PLRT", "colour": "#748477"},
}

# Reverse lookups, built once at import time.
ALERTS_CODE_TO_CANONICAL = {}
CROWD_CODE_TO_CANONICAL = {}
for _canon, _info in CANONICAL_LINES.items():
    ALERTS_CODE_TO_CANONICAL.setdefault(_info["alerts_code"], []).append(_canon)
    CROWD_CODE_TO_CANONICAL.setdefault(_info["crowd_code"], []).append(_canon)


def crowd_level_label(level: str) -> str:
    """Map DataMall's single-letter crowd level to a display label."""
    return {"l": "Low", "m": "Moderate", "h": "High", "NA": "No data"}.get(level, "No data")
