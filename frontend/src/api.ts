// Types mirror the backend's response shape exactly (see
// backend/app/routers/*.py and backend/app/services/route_planner.py) so
// there is exactly one place that has to stay in sync with the API.

export type Scenario = "normal" | "disruption" | "crowded" | "rain";

export interface StationRef {
  code: string;
  name: string;
  lat: number;
  lon: number;
}

export interface WalkLeg {
  mode: "walk";
  label: string;
  points: [number, number][]; // [lat, lon]
  distance_m: number;
  duration_s: number;
  affected?: boolean;
}

// One rail leg = one continuous ride on a single line (e.g. "EWL, Tampines
// -> Buona Vista, 4 stops"), not one leg per station-to-station hop --
// grouped server-side in route_planner._hops_to_legs.
export interface RailLeg {
  mode: "rail";
  line: string;
  from: StationRef;
  to: StationRef;
  stops: number;
  duration_s: number;
  affected: boolean;
  points: [number, number][]; // every intermediate station on this ride, [lat, lon]
}

export interface BusLeg {
  mode: "bus";
  label: string;
  from: StationRef;
  to: StationRef;
  duration_s: number;
  free: boolean;
  note: string;
  affected?: boolean;
}

export type Leg = WalkLeg | RailLeg | BusLeg;

export interface Route {
  id: string;
  label: string;
  legs: Leg[];
  total_duration_s: number;
  uncertainty_s: number;
  has_disruption: boolean;
  affected_stations: string[];
  added_minutes: number;
}

export type Severity = "info" | "warning" | "critical";

export interface Advice {
  severity: Severity;
  headline: string;
  detail: string;
  recommended_route_id: string;
  reason: "disruption" | "crowding" | "weather";
}

export interface CrowdInfo {
  level: "l" | "m" | "h" | "NA";
  label: string;
}

// Common shape both /journey (Rachel's persona demo, schedule-aware) and
// /plan (general station-to-station) return. journey_meta/crowd_now are
// only ever present on the /journey response.
export interface TripResult {
  scenario: Scenario;
  persona?: string;
  origin?: string;
  destination?: string;
  journey_meta?: {
    origin: { label: string; lat: number; lon: number };
    destination: { label: string; lat: number; lon: number };
    usual_departure: string;
    must_arrive_by: string;
  };
  routes: Route[];
  recommended_route_id: string;
  advice: Advice | null;
  crowd_now?: Record<string, CrowdInfo>;
}

export interface StationSearchResult {
  name: string;
  codes: string[];
  lines: string[];
  lat: number;
  lon: number;
}

// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.ts).
// In production, point this at wherever the FastAPI backend is deployed.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`GET ${path} failed: ${res.status} ${body}`);
  }
  return res.json();
}

// Rachel's fixed persona demo: real walking legs, schedule-aware advice.
export function fetchJourney(scenario: Scenario): Promise<TripResult> {
  return getJSON<TripResult>(`/journey?scenario=${scenario}`);
}

// General "pick any two stations" trip planner.
export function fetchPlan(origin: string, destination: string, scenario: Scenario): Promise<TripResult> {
  return getJSON<TripResult>(
    `/plan?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&scenario=${scenario}`
  );
}

export function searchStations(query: string, limit = 8): Promise<StationSearchResult[]> {
  if (!query.trim()) return Promise.resolve([]);
  return getJSON<StationSearchResult[]>(`/stations/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}
