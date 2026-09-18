# Smart Commuter Companion

A proactive decision-support companion for Singapore's rail network. Pick any two stations and get the best route, with disruption-aware rerouting; save your daily commute (work, school, whatever you ride every day) and get warned the moment something changes it. Built end-to-end for **Rachel** — fixed-schedule commuter, Tampines → Raffles Place on the East West Line, leaves 07:40, must be at her desk by 08:45 (Section 2.2 of the problem statement) — with a general trip planner layered on top of the same routing/disruption logic for any other trip.

This README is written to be followed on a clean machine, per Section 3.2.4 of the brief ("Judges follow your README on a clean machine; what does not run does not score").

## 1. What's here

- `backend/` — FastAPI. Wraps LTA DataMall, OneMap and data.gov.sg weather; routes over the full MRT/LRT network graph; layers live conditions onto whichever route is being asked about; decides whether and what to tell the commuter. Runs entirely on realistic mock data out of the box (`USE_MOCK=true`), so it works before you have API keys.
- `frontend/` — React + Vite + TypeScript, mobile-first. Saved-routes home screen, a station-search trip planner, MapLibre GL map on an OpenStreetMap base (OpenFreeMap tiles), proactive advice banner, route comparison, crowding visualisation, and browser-notification disruption warnings.
- `scripts/build_network.py` — the (one-time, already-run) generator for `backend/app/network_data.py`, the full station/line topology. Kept for provenance — see Section 6.

## 2. Quick start

You'll need Python 3.11+ and Node 18+.

**Backend**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env         # defaults to USE_MOCK=true — no API keys needed yet
uvicorn app.main:app --reload --port 8000
```

Try it:
- `http://localhost:8000/api/journey?scenario=disruption` — Rachel's fixed persona demo, full payload with a proactive advice object.
- `http://localhost:8000/api/plan?origin=Jurong%20East&destination=Punggol&scenario=disruption` — the general planner, routed across three different lines.
- `http://localhost:8000/api/stations/search?q=bishan` — the autocomplete endpoint the frontend's trip planner uses.
- `http://localhost:8000/docs` — interactive API docs for everything above.

**Frontend** (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open the printed `http://localhost:5173` URL **on your phone** (or your browser's device toolbar, but see the note in Section 3.2.3 of the brief about why that's not sufficient for judging) — the Vite dev server is reachable from other devices on the same network via `--host` (already set in `vite.config.ts`).

There's a "Demo:" dropdown in the top bar — switch between **Normal day / EWL disruption / Crowded platform / Rain**. This exists because TrainServiceAlerts is empty on an ordinary day (Section 2.6); it swaps which mock scenario the backend serves, clearly labelled as a demo control, not a hidden fake. It applies network-wide, so you can see a trip that crosses the disrupted stretch reroute while an unrelated trip elsewhere on the network stays unaffected and silent.

**Sanity-checking the logic without installing anything**

```bash
cd backend
python3 tests/test_logic.py
```

Runs the route-planning and advice logic directly (no FastAPI/uvicorn needed) against Rachel's four demo scenarios *and* the network-wide planner (a same-line trip, a multi-interchange trip, a trip correctly unaffected by a disruption elsewhere, a trip that correctly reroutes around one). Useful as a first check, or in an environment where installing the full dependency list isn't convenient.

## 3. Using the app

- **Home screen** shows your saved routes. Rachel's Tampines → Raffles Place commute is pre-seeded as a worked example on first load (you can delete it).
- **"+ Plan a new trip"** opens a station search (autocomplete over the whole MRT/LRT network) for an origin and destination, then shows the best route.
- On the results screen for an ad-hoc trip, **"☆ Save this route"** adds it to your home screen under whatever label you give it (e.g. "School").
- The home screen offers to **turn on notifications**; once granted, the app polls every 30s (in the background, while the tab is open) and fires a real browser notification the moment a saved route is hit by a disruption — see Section 6 for exactly what this does and doesn't cover.

## 4. Going from mock data to live data

Set `USE_MOCK=false` in `backend/.env` and fill in:

- `LTA_ACCOUNT_KEY` — register free at https://datamall.lta.gov.sg
- `ONEMAP_EMAIL` / `ONEMAP_PASSWORD` — register free at https://www.onemap.gov.sg/apidocs/ (OneMap issues a short-lived bearer token from credentials, not a static key; `backend/app/services/onemap.py` fetches and caches it)

No code changes needed — every caller goes through `backend/app/services/*.py`, which is the only place that knows whether it's talking to a mock fixture or the real endpoint.

## 5. Architecture

```
frontend (React/Vite)
  ├─ /api/journey?scenario=...          Rachel's fixed persona demo
  ├─ /api/plan?origin=&destination=     general station-to-station trip
  └─ /api/stations/search?q=            autocomplete
              │
              ▼
        backend (FastAPI)
              │
   ┌──────────┼──────────────┐
   │          │              │
datamall.py  onemap.py   weather.py
(alerts,     (walk         (2-hr
 crowding)    routing)      nowcast)
   │
   ▼
graph.py            network_data.py
(Dijkstra over the   (~186 stations, all
 whole network,       MRT+LRT lines, real
 interchange-aware)   codes/names/order)
   │
   ▼
route_planner.py     (habitual route via graph.shortest_path; disruption
   │                  laid on top of THAT route rather than letting the
   │                  search silently reroute on its own; alternative =
   │                  free-bus bridge if the feed names one, else full
   │                  network reroute avoiding the disrupted edges)
   ▼
advice_engine.py     (decides: silent, or one actionable line)
```

- **`network_data.py`** — the whole MRT/LRT network: every station's real code(s), name, which line(s) serve it, and approximate coordinates. Generated once by `scripts/build_network.py` — see Section 6 for exactly how, and its accuracy caveat.
- **`graph.py`** — Dijkstra over the network, with interchange stations as natural junctions (a station reachable via more than one line's edge list is automatically a transfer point) and a transfer-time penalty when the path changes line. Two searches: a plain one (`shortest_path`, entirely disruption-unaware — "the route you'd normally take") and one that excludes a given set of edges (`shortest_path_avoiding` — the alternative). Deliberately *not* one search that lets disrupted edges cost extra internally — see the docstring in `graph.py` for why that seemingly-simpler option was rejected (it can silently swap a commuter's whole route for an unrelated one whenever the arithmetic favours it).
- **`route_planner.py`** — two entry points. `build_rachel_journey()` is her full persona demo (real walking legs at each end, her fixed EWL trip). `plan_trip()` is the general case (any two stations, station-to-station, no walking legs — see Section 6). Both apply today's disruption to whichever edges of *that specific route* are actually affected, and build up to two alternative candidates when disrupted — the free-bus/shuttle bridge DataMall itself names in `FreePublicBus`/`FreeMRTShuttle` (Section 2.4: "the mitigation is in the feed"), and a full network reroute — returning whichever is faster.
- **`line_mapping.py`** — the canonical line-code table that maps DataMall's inconsistent codes (STL vs SLRT, EWL vs CGL, etc. — Section 2.4's "trap") onto one name used everywhere else in the code.
- **`advice_engine.py`** — `build_disruption_advice()` is network-wide and schedule-optional: it works for an ad-hoc trip (delay-based only) and, wrapped by `build_rachel_advice()`, for Rachel's fixed schedule too (deadline-aware: delays under ~5 min are noise, ~15 min is the headline "interrupt her, tell her what to do" case — Section 2.2, close to literally). `build_rachel_advice()` also covers the two non-disruption cases the brief asks for: a forecast-only crowding warning before anything has gone wrong (PCDForecast), and a weather nudge for her walking legs (data.gov.sg nowcast).
- **Frontend** — `MapView.tsx` draws the route(s) on an OpenStreetMap base (OpenFreeMap vector tiles, attribution shown per Section 2.3), each rail leg in its real line colour, the disrupted segment visually distinct, the alternative shown against the original, and station crowding shown as colour **and shape** (circle/square/diamond) so it doesn't rely on colour alone. `JourneyCard.tsx` groups a continuous ride into one leg ("EWL, Tampines → Buona Vista, 4 stops") and shows time as a range, not a single confident number. `AdviceBanner.tsx` is the proactive one-liner. `StationInput.tsx` + `TripPlanner.tsx` are the destination picker; `SavedRoutesHome.tsx` + `storage.ts` are the saved-routes feature (localStorage only — see Section 6); `notifications.ts` is the disruption-warning system.

## 6. Known limitations / assumptions (read before judging)

**Network topology and coordinates.** Every station's code(s), name, line membership and service order (`network_data.py`) were fetched from Wikipedia's "List of Singapore MRT stations" and "List of Singapore LRT stations" on 2026-09-18 and are accurate as of that date — this is the part that matters for routing *correctness* and it's real data, not invented. Coordinates are a different story: this environment's network policy blocked the geocoding/bulk-coordinate sources that would have given survey-accurate positions (Overpass API, OneMap, a coordinates dataset on GitHub all returned `403`/organization-policy-denied when fetched), so `scripts/build_network.py` instead hand-places ~50 well-known anchor stations from general geographic knowledge and linearly interpolates everything in between along each line. Every station lands within Singapore's real bounds and in a geographically plausible spot (spot-checked after generation), but this is accurate to roughly 100–400m, not centimetres — the same documented simplification the original EWL-only build used for Rachel's corridor, now applied network-wide. Before production use, replace `network_data.py`'s coordinates with the surveyed `PS2/data/AmendmenttoMP2014RailStation.geojson` polygons (or `TrainStationExit` for door-level accuracy).
- **Rail geometry between consecutive stations is a straight line** in the underlying anchor data, though the map draws every intermediate stop along a continuous ride (not just a straight line from boarding to alighting station), which is closer to the real alignment than a single chord would be.
- **LRT loops** (Bukit Panjang / Sengkang / Punggol) are modelled correctly as closed loops for routing purposes, but their in-loop station coordinates are placed on a rough circle around the interchange rather than their real tightly-packed layout — cosmetic only, doesn't affect route correctness.

**Walking legs.** Rachel's persona demo has real walking legs at each end; the general planner (`/api/plan`) is station-to-station only, with no walking legs, because door-to-door for an arbitrary trip needs geocoding a free-text address (OneMap's geocoder), which isn't wired up. `services/onemap.py`'s walk-routing call is wired to OneMap's real endpoint but its polyline decode is stubbed (see the code comment) since it couldn't be tested against a live response without an account — distance/duration in real mode come from OneMap's own summary either way; only the visual shape of Rachel's ~400m walks is the simplification.

**Crowding data stays EWL-scoped.** DataMall's PCDRealTime/PCDForecast mocks (and the "crowded platform" demo scenario) only cover the EWL corridor, matching Rachel's persona demo. A `/api/plan` trip on another line won't show crowding markers — not because the code can't handle it, but because scaling the mock crowding fixture to every line wasn't done in this pass. Swapping to real DataMall in Section 4 already covers every line `PCDRealTime`/`PCDForecast` support; only the mock fixture is EWL-only.

**Saved routes and notifications are entirely client-side**, per the scope chosen for this build: no accounts, nothing stored server-side. This means:
- Saved routes live in one browser, on one device — they don't sync anywhere.
- Disruption notifications use the browser Notification API, checked by a 30-second poll while the app's tab is open (foreground or backgrounded). They do **not** work after the browser is fully closed, and won't wake a phone that's put the browser to sleep — that would need a real Web Push setup (service worker, VAPID keys, and a backend that stores subscriptions and runs its own watcher independent of any open tab), which was scoped out in favour of shipping the simpler version end-to-end. See Section 7.
- A disruption notification only fires once per distinct disruption per route (deduplicated in-memory, not persisted) — reloading the page resets that memory, so it's possible to be notified again about a disruption you already saw if you reload mid-disruption. Fine for a demo, worth a persisted dedupe key (e.g. `sessionStorage`) before relying on it daily.

**Underground / no-signal behaviour** (Section 2.6): the frontend keeps showing the last successfully fetched journey with a visible "stale, last updated HH:MM" banner rather than blanking the screen, and resumes polling automatically on the browser's `online` event. It does not attempt to detect "in a train tunnel" specifically (the browser can't tell that apart from any other network loss) — it degrades the same way for any connectivity gap.

**The delay-minutes figure is extracted with a regex**, not an LLM (`route_planner._extract_added_minutes`), on the reasoning that real TrainServiceAlerts notices are formulaic enough ("please add N minutes to your travel time") that a model would mostly re-derive a number a regex gets deterministically and near-instantly. This is a place Section 3.3.1 explicitly invites AI; a regex was chosen on the "well-argued decision not to use a model where a simpler method works" clause in that section — worth revisiting against a larger sample of real notices (the SG MRT Updates Telegram archive, Section 2.4) before trusting it in production.

**Privacy.** No personal data is collected, stored, or persisted server-side anywhere. Rachel's routine (origin, destination, usual departure time) is hardcoded in `backend/app/stations.py` as a stand-in for what would, in a real product, be a user's own saved profile. Saved routes and notification dedupe state live only in the browser making them (localStorage / in-memory), never sent to or stored by the backend. The app has no accounts, no database, no logging of any individual's movements.

**Demo scenarios are clearly labelled**, per Section 2.6's explicit allowance, as `USE_MOCK` mock fixtures / the frontend's "Demo:" dropdown — never presented as live data.

**Dependencies were written and syntax-checked, not build-verified**, because the sandbox this was built in blocked outbound access to `pypi.org`, `registry.npmjs.org`, and general web hosts (Overpass, Wikipedia's raw data endpoints, OneMap, GitHub raw content) at the network-policy level — `pip install`/`npm install` could not be run there, and topology data had to come from what a heavily-summarizing web-fetch tool could relay rather than a bulk data pull. What *was* verified end-to-end there: every backend Python file's syntax; the full routing/advice logic (`tests/test_logic.py`, Rachel's four scenarios plus four network-wide cases) using only the standard library plus `httpx`/`python-dotenv`, both available in that environment; every frontend TS/TSX file's syntax against a bare TypeScript compiler (catching, for instance, a missing `vite-env.d.ts` and a discriminated-union typing bug in `storage.ts` that would otherwise have failed `npm run build` under strict mode). Run the Quick Start above on a normal machine for the parts that couldn't be exercised there; if anything doesn't come up cleanly, it's most likely a small dependency-version pin worth adjusting, not a logic error.

## 7. Beyond the brief / ideas not built

- Turning `TrainServiceAlerts.Message` free text into structured advice with an LLM instead of the current regex, and comparing accuracy/latency against it on the Telegram archive.
- Learning a commuter's *actual* buffer tolerance from history instead of a hardcoded 5/15-minute threshold (Rachel's) — and offering the same schedule-aware framing to a saved route once the user tells the app when they need to arrive, not just Rachel's hardcoded one.
- Full Web Push (service worker + VAPID + a backend subscription store) so disruption notifications survive the browser being closed, instead of the current tab-open-only approach.
- Door-to-door walking legs for the general planner via OneMap geocoding of a free-text address, and extending crowding data beyond the EWL mock.
- Extending `route_planner.py`'s persona-aware layer (the way `build_rachel_journey` wraps the generic graph search) to Arjun (multi-modal, cycling, comfort-over-speed) and Mdm Lim (accessibility: `v2/FacilitiesMaintenance` is already wired into `datamall.py` and mocked, unused by the current flows but ready to plug in).
