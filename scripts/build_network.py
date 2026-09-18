"""
Generates backend/app/network_data.py: the full MRT/LRT topology (real
station codes/names/order/interchanges, verified against Wikipedia on
2026-09-18) plus approximate coordinates (anchor + linear interpolation --
same documented-assumption approach already used for the EWL corridor).

Run once, review the output, then the generated file is committed as a
static module (not recomputed at import time -- easier to review/diff).
"""

import json

# ---------------------------------------------------------------------------
# Service paths: one entry per contiguous, orderable service run. Straight
# lines are a single path. Branches (Changi Airport off EWL) and loops
# (the 3 LRT lines) are modelled as their own path(s) sharing endpoint
# stations with the line they branch/loop from -- that shared station name
# is what stitches the graph together at junctions.
#
# Each path: canonical_line_key -> list of (code, name)
# ---------------------------------------------------------------------------

PATHS = {}

PATHS["NSL"] = [
    ("NS1", "Jurong East"), ("NS2", "Bukit Batok"), ("NS3", "Bukit Gombak"),
    ("NS4", "Choa Chu Kang"), ("NS5", "Yew Tee"), ("NS7", "Kranji"),
    ("NS8", "Marsiling"), ("NS9", "Woodlands"), ("NS10", "Admiralty"),
    ("NS11", "Sembawang"), ("NS12", "Canberra"), ("NS13", "Yishun"),
    ("NS14", "Khatib"), ("NS15", "Yio Chu Kang"), ("NS16", "Ang Mo Kio"),
    ("NS17", "Bishan"), ("NS18", "Braddell"), ("NS19", "Toa Payoh"),
    ("NS20", "Novena"), ("NS21", "Newton"), ("NS22", "Orchard"),
    ("NS23", "Somerset"), ("NS24", "Dhoby Ghaut"), ("NS25", "City Hall"),
    ("NS26", "Raffles Place"), ("NS27", "Marina Bay"), ("NS28", "Marina South Pier"),
]

PATHS["EWL"] = [
    ("EW1", "Pasir Ris"), ("EW2", "Tampines"), ("EW3", "Simei"),
    ("EW4", "Tanah Merah"), ("EW5", "Bedok"), ("EW6", "Kembangan"),
    ("EW7", "Eunos"), ("EW8", "Paya Lebar"), ("EW9", "Aljunied"),
    ("EW10", "Kallang"), ("EW11", "Lavender"), ("EW12", "Bugis"),
    ("EW13", "City Hall"), ("EW14", "Raffles Place"), ("EW15", "Tanjong Pagar"),
    ("EW16", "Outram Park"), ("EW17", "Tiong Bahru"), ("EW18", "Redhill"),
    ("EW19", "Queenstown"), ("EW20", "Commonwealth"), ("EW21", "Buona Vista"),
    ("EW22", "Dover"), ("EW23", "Clementi"), ("EW24", "Jurong East"),
    ("EW25", "Chinese Garden"), ("EW26", "Lakeside"), ("EW27", "Boon Lay"),
    ("EW28", "Pioneer"), ("EW29", "Joo Koon"), ("EW30", "Gul Circle"),
    ("EW31", "Tuas Crescent"), ("EW32", "Tuas West Road"), ("EW33", "Tuas Link"),
]

# Changi Airport branch, off EWL at Tanah Merah.
PATHS["CGL"] = [
    ("EW4", "Tanah Merah"), ("CG1", "Expo"), ("CG2", "Changi Airport"),
]

PATHS["NEL"] = [
    ("NE1", "HarbourFront"), ("NE3", "Outram Park"), ("NE4", "Chinatown"),
    ("NE5", "Clarke Quay"), ("NE6", "Dhoby Ghaut"), ("NE7", "Little India"),
    ("NE8", "Farrer Park"), ("NE9", "Boon Keng"), ("NE10", "Potong Pasir"),
    ("NE11", "Woodleigh"), ("NE12", "Serangoon"), ("NE13", "Kovan"),
    ("NE14", "Hougang"), ("NE15", "Buangkok"), ("NE16", "Sengkang"),
    ("NE17", "Punggol"), ("NE18", "Punggol Coast"),
]

PATHS["CCL"] = [
    ("CC1", "Dhoby Ghaut"), ("CC2", "Bras Basah"), ("CC3", "Esplanade"),
    ("CC4", "Promenade"), ("CC5", "Nicoll Highway"), ("CC6", "Stadium"),
    ("CC7", "Mountbatten"), ("CC8", "Dakota"), ("CC9", "Paya Lebar"),
    ("CC10", "MacPherson"), ("CC11", "Tai Seng"), ("CC12", "Bartley"),
    ("CC13", "Serangoon"), ("CC14", "Lorong Chuan"), ("CC15", "Bishan"),
    ("CC16", "Marymount"), ("CC17", "Caldecott"),
    # CC18 does not exist (reserved). Continue at CC19.
    ("CC19", "Botanic Gardens"), ("CC20", "Farrer Road"), ("CC21", "Holland Village"),
    ("CC22", "Buona Vista"), ("CC23", "one-north"), ("CC24", "Kent Ridge"),
    ("CC25", "Haw Par Villa"), ("CC26", "Pasir Panjang"), ("CC27", "Labrador Park"),
    ("CC28", "Telok Blangah"), ("CC29", "HarbourFront"), ("CC30", "Keppel"),
    ("CC31", "Cantonment"), ("CC32", "Prince Edward Road"),
]

# Circle Line Extension: Promenade -> Bayfront -> Marina Bay, closing the loop.
PATHS["CEL"] = [
    ("CC4", "Promenade"), ("CE1", "Bayfront"), ("CE2", "Marina Bay"),
]

PATHS["DTL"] = [
    ("DT1", "Bukit Panjang"), ("DT2", "Cashew"), ("DT3", "Hillview"),
    ("DT4", "Hume"), ("DT5", "Beauty World"), ("DT6", "King Albert Park"),
    ("DT7", "Sixth Avenue"), ("DT8", "Tan Kah Kee"), ("DT9", "Botanic Gardens"),
    ("DT10", "Stevens"), ("DT11", "Newton"), ("DT12", "Little India"),
    ("DT13", "Rochor"), ("DT14", "Bugis"), ("DT15", "Promenade"),
    ("DT16", "Bayfront"), ("DT17", "Downtown"), ("DT18", "Telok Ayer"),
    ("DT19", "Chinatown"), ("DT20", "Fort Canning"), ("DT21", "Bencoolen"),
    ("DT22", "Jalan Besar"), ("DT23", "Bendemeer"), ("DT24", "Geylang Bahru"),
    ("DT25", "Mattar"), ("DT26", "MacPherson"), ("DT27", "Ubi"),
    ("DT28", "Kaki Bukit"), ("DT29", "Bedok North"), ("DT30", "Bedok Reservoir"),
    ("DT31", "Tampines West"), ("DT32", "Tampines"), ("DT33", "Tampines East"),
    ("DT34", "Upper Changi"), ("DT35", "Expo"), ("DT36", "Xilin"),
    ("DT37", "Sungei Bedok"),
]

PATHS["TEL"] = [
    ("TE1", "Woodlands North"), ("TE2", "Woodlands"), ("TE3", "Woodlands South"),
    ("TE4", "Springleaf"), ("TE5", "Lentor"), ("TE6", "Mayflower"),
    ("TE7", "Bright Hill"), ("TE8", "Upper Thomson"), ("TE9", "Caldecott"),
    # TE10 does not exist (reserved). Continue at TE11.
    ("TE11", "Stevens"), ("TE12", "Napier"), ("TE13", "Orchard Boulevard"),
    ("TE14", "Orchard"), ("TE15", "Great World"), ("TE16", "Havelock"),
    ("TE17", "Outram Park"), ("TE18", "Maxwell"), ("TE19", "Shenton Way"),
    ("TE20", "Marina Bay"),
    # TE21 does not exist (reserved). Continue at TE22.
    ("TE22", "Gardens by the Bay"), ("TE23", "Tanjong Rhu"), ("TE24", "Katong Park"),
    ("TE25", "Tanjong Katong"), ("TE26", "Marine Parade"), ("TE27", "Marine Terrace"),
    ("TE28", "Siglap"), ("TE29", "Bayshore"), ("TE30", "Bedok South"),
    ("TE31", "Sungei Bedok"),
]

PATHS["BPL"] = [
    ("BP1", "Choa Chu Kang"), ("BP2", "South View"), ("BP3", "Keat Hong"),
    ("BP4", "Teck Whye"), ("BP5", "Phoenix"), ("BP6", "Bukit Panjang"),
    ("BP7", "Petir"), ("BP13", "Senja"), ("BP12", "Jelapang"),
    ("BP11", "Segar"), ("BP10", "Fajar"), ("BP9", "Bangkit"),
    ("BP8", "Pending"), ("BP1", "Choa Chu Kang"),  # loop closes back to BP1
]

PATHS["SLRT_EAST"] = [
    ("STC", "Sengkang"), ("SE1", "Compassvale"), ("SE2", "Rumbia"),
    ("SE3", "Bakau"), ("SE4", "Kangkar"), ("SE5", "Ranggung"),
    ("STC", "Sengkang"),
]
PATHS["SLRT_WEST"] = [
    ("STC", "Sengkang"), ("SW2", "Farmway"), ("SW1", "Cheng Lim"),
    ("SW3", "Kupang"), ("SW5", "Fernvale"), ("SW4", "Thanggam"),
    ("SW6", "Layar"), ("SW8", "Renjong"), ("STC", "Sengkang"),
]

PATHS["PLRT_EAST"] = [
    ("PTC", "Punggol"), ("PE1", "Cove"), ("PE2", "Meridian"),
    ("PE3", "Coral Edge"), ("PE4", "Riviera"), ("PE5", "Kadaloor"),
    ("PE6", "Oasis"), ("PE7", "Damai"), ("PTC", "Punggol"),
]
PATHS["PLRT_WEST"] = [
    ("PTC", "Punggol"), ("PW1", "Sam Kee"), ("PW2", "Teck Lee"),
    ("PW3", "Punggol Point"), ("PW5", "Nibong"), ("PW6", "Sumang"),
    ("PW7", "Soo Teck"), ("PW4", "Samudera"), ("PTC", "Punggol"),
]

# Which canonical line (matches line_mapping.CANONICAL_LINES) each path
# counts as, for the "which lines serve this station" list.
PATH_TO_CANONICAL_LINE = {
    "NSL": "NSL", "EWL": "EWL", "CGL": "CGL", "NEL": "NEL", "CCL": "CCL",
    "CEL": "CEL", "DTL": "DTL", "TEL": "TEL", "BPL": "BPL",
    "SLRT_EAST": "SLRT", "SLRT_WEST": "SLRT",
    "PLRT_EAST": "PLRT", "PLRT_WEST": "PLRT",
}

# ---------------------------------------------------------------------------
# Approximate anchor coordinates (see README "Known limitations" -- these
# are hand-placed near each station's real location, not survey data).
# Every path's FIRST and LAST station must have an anchor so interpolation
# never has to extrapolate.
# ---------------------------------------------------------------------------

ANCHORS = {
    # NSL
    "Jurong East": (1.3333, 103.7422),
    "Choa Chu Kang": (1.3854, 103.7443),
    "Woodlands": (1.4370, 103.7863),
    "Yishun": (1.4295, 103.8350),
    "Ang Mo Kio": (1.3700, 103.8496),
    "Bishan": (1.3510, 103.8486),
    "Novena": (1.3204, 103.8438),
    "Newton": (1.3127, 103.8382),
    "Orchard": (1.3040, 103.8318),
    "Dhoby Ghaut": (1.2989, 103.8460),
    "City Hall": (1.2931, 103.8520),
    "Raffles Place": (1.2839, 103.8514),
    "Marina Bay": (1.2762, 103.8546),
    "Marina South Pier": (1.2707, 103.8631),
    # EWL
    "Pasir Ris": (1.3721, 103.9493),
    "Tampines": (1.3546, 103.9437),
    "Tanah Merah": (1.3272, 103.9463),
    "Paya Lebar": (1.3177, 103.8925),
    "Bugis": (1.3006, 103.8559),
    "Outram Park": (1.2802, 103.8394),
    "Queenstown": (1.2946, 103.8059),
    "Buona Vista": (1.3067, 103.7900),
    "Clementi": (1.3151, 103.7653),
    "Chinese Garden": (1.3423, 103.7327),
    "Boon Lay": (1.3387, 103.7064),
    "Joo Koon": (1.3277, 103.6783),
    "Tuas Link": (1.3404, 103.6366),
    # CGL
    "Expo": (1.3350, 103.9617),
    "Changi Airport": (1.3572, 104.0019),
    # NEL
    "HarbourFront": (1.2653, 103.8200),
    "Chinatown": (1.2846, 103.8440),
    "Clarke Quay": (1.2885, 103.8465),
    "Little India": (1.3067, 103.8493),
    "Potong Pasir": (1.3313, 103.8686),
    "Serangoon": (1.3496, 103.8733),
    "Hougang": (1.3712, 103.8926),
    "Sengkang": (1.3917, 103.8951),
    "Punggol": (1.4054, 103.9022),
    "Punggol Coast": (1.4127, 103.9143),
    # CCL / CEL
    "Promenade": (1.2930, 103.8610),
    "Stadium": (1.3028, 103.8755),
    "MacPherson": (1.3266, 103.8901),
    "Serangoon": (1.3496, 103.8733),
    "Lorong Chuan": (1.3517, 103.8645),
    "Caldecott": (1.3378, 103.8395),
    "Botanic Gardens": (1.3226, 103.8154),
    "Holland Village": (1.3113, 103.7963),
    "one-north": (1.2998, 103.7873),
    "Haw Par Villa": (1.2825, 103.7822),
    "Telok Blangah": (1.2706, 103.8093),
    "Keppel": (1.2705, 103.8270),
    "Cantonment": (1.2755, 103.8398),
    "Prince Edward Road": (1.2790, 103.8470),
    "Bayfront": (1.2818, 103.8590),
    # DTL
    "Bukit Panjang": (1.3786, 103.7622),
    "Beauty World": (1.3411, 103.7756),
    "Botanic Gardens": (1.3226, 103.8154),
    "Rochor": (1.3037, 103.8528),
    "Downtown": (1.2792, 103.8527),
    "Bendemeer": (1.3138, 103.8628),
    "Ubi": (1.3299, 103.8996),
    "Bedok Reservoir": (1.3363, 103.9130),
    "Tampines West": (1.3457, 103.9382),
    "Tampines East": (1.3562, 103.9548),
    "Upper Changi": (1.3416, 103.9612),
    "Xilin": (1.3305, 103.9505),
    "Sungei Bedok": (1.3200, 103.9550),
    # TEL
    "Woodlands North": (1.4490, 103.7862),
    "Springleaf": (1.3968, 103.8188),
    "Bright Hill": (1.3630, 103.8329),
    "Upper Thomson": (1.3546, 103.8328),
    "Orchard Boulevard": (1.3016, 103.8255),
    "Great World": (1.2935, 103.8323),
    "Outram Park": (1.2802, 103.8394),
    "Shenton Way": (1.2769, 103.8511),
    "Gardens by the Bay": (1.2810, 103.8644),
    "Katong Park": (1.3018, 103.8894),
    "Marine Parade": (1.3040, 103.9070),
    "Bayshore": (1.3130, 103.9330),
    "Bedok South": (1.3210, 103.9450),
    # BPL loop (small area north of Choa Chu Kang / Bukit Panjang)
    "South View": (1.3796, 103.7476),
    "Petir": (1.3776, 103.7692),
    "Bangkit": (1.3799, 103.7727),
}

# LRT loop "shape" anchors: one extra point per loop so linear interpolation
# doesn't collapse the whole loop onto a single line between two identical
# start/end coordinates. Rough centre-of-loop offsets, not surveyed.
LOOP_SHAPE_ANCHOR = {
    "SLRT_EAST": ("Bakau", (1.3960, 103.9040)),
    "SLRT_WEST": ("Kupang", (1.3860, 103.8790)),
    "PLRT_EAST": ("Riviera", (1.4115, 103.9080)),
    "PLRT_WEST": ("Punggol Point", (1.4145, 103.9010)),
    "BPL": ("Jelapang", (1.3830, 103.7640)),
}


def interpolate_path(path_key, stations):
    """Fill in coordinates for every station in `stations` (list of (code,
    name)) using ANCHORS (+ a loop shape anchor if this path is a loop),
    linearly interpolating between the nearest anchors on either side."""
    names = [n for _, n in stations]
    anchor_points = dict(ANCHORS)
    if path_key in LOOP_SHAPE_ANCHOR:
        shape_name, coord = LOOP_SHAPE_ANCHOR[path_key]
        anchor_points[f"__shape__{path_key}"] = coord
        # Insert the shape anchor's name association by index later.

    anchor_idx = []
    for i, name in enumerate(names):
        if name in anchor_points:
            anchor_idx.append((i, anchor_points[name]))

    # Inject the loop shape anchor at its midpoint index if this path has one.
    if path_key in LOOP_SHAPE_ANCHOR:
        shape_name, coord = LOOP_SHAPE_ANCHOR[path_key]
        try:
            mid_i = names.index(shape_name)
            anchor_idx.append((mid_i, coord))
        except ValueError:
            pass
        anchor_idx.sort(key=lambda t: t[0])

    if len(anchor_idx) < 2:
        raise ValueError(f"{path_key}: need >=2 anchors, got {anchor_idx} for {names}")

    coords = [None] * len(names)
    for k in range(len(anchor_idx) - 1):
        i0, (lat0, lon0) = anchor_idx[k]
        i1, (lat1, lon1) = anchor_idx[k + 1]
        span = i1 - i0
        for i in range(i0, i1 + 1):
            t = 0 if span == 0 else (i - i0) / span
            coords[i] = (lat0 + (lat1 - lat0) * t, lon0 + (lon1 - lon0) * t)

    # Anything before the first anchor or after the last (shouldn't happen
    # if first/last station of every path is an anchor) -- clamp.
    for i in range(len(coords)):
        if coords[i] is None:
            coords[i] = anchor_idx[0][1] if i < anchor_idx[0][0] else anchor_idx[-1][1]

    return coords


def main():
    stations = {}  # name -> {"codes": set(), "lines": set(), "lat":.., "lon":..}
    edges = []  # (path_key, canonical_line, code_a, name_a, code_b, name_b)

    for path_key, seq in PATHS.items():
        coords = interpolate_path(path_key, seq)
        canonical_line = PATH_TO_CANONICAL_LINE[path_key]
        for (code, name), (lat, lon) in zip(seq, coords):
            st = stations.setdefault(name, {"codes": set(), "lines": set(), "lat": lat, "lon": lon})
            st["codes"].add(code)
            st["lines"].add(canonical_line)
        for (c1, n1), (c2, n2) in zip(seq, seq[1:]):
            edges.append((path_key, canonical_line, c1, n1, c2, n2))

    # Sanity: bounding box should be within Singapore.
    lats = [s["lat"] for s in stations.values()]
    lons = [s["lon"] for s in stations.values()]
    print(f"stations: {len(stations)}  edges: {len(edges)}")
    print(f"lat range: {min(lats):.4f} - {max(lats):.4f}")
    print(f"lon range: {min(lons):.4f} - {max(lons):.4f}")

    out_of_bounds = [
        (name, s["lat"], s["lon"])
        for name, s in stations.items()
        if not (1.13 <= s["lat"] <= 1.48 and 103.59 <= s["lon"] <= 104.05)
    ]
    if out_of_bounds:
        print("OUT OF BOUNDS:", out_of_bounds)

    with open("network_data.json", "w") as f:
        json.dump(
            {
                "stations": {
                    name: {"codes": sorted(s["codes"]), "lines": sorted(s["lines"]), "lat": round(s["lat"], 5), "lon": round(s["lon"], 5)}
                    for name, s in stations.items()
                },
                "edges": edges,
            },
            f,
            indent=1,
        )
    print("wrote network_data.json")


if __name__ == "__main__":
    main()
