// Saved routes, entirely client-side (localStorage) -- no accounts, no
// server-side storage, matching the privacy-first stance already in the
// README. Lives only in this browser, on this device.

// Discriminated union (rather than one shape with optional fields) so
// `route.kind === "custom"` narrows `origin`/`destination` to plain
// strings wherever they're used -- a flat interface with `origin?: string`
// would let e.g. fetchPlan(route.origin, ...) compile against a value that
// might be undefined, which strict mode (on in tsconfig.json) is right to
// reject.
export type SavedRoute =
  | { id: string; label: string; kind: "rachel-demo"; createdAt: number }
  | { id: string; label: string; kind: "custom"; origin: string; destination: string; createdAt: number };

const KEY = "commuter-companion:saved-routes:v1";

function safeParse(json: string | null): SavedRoute[] {
  if (!json) return [];
  try {
    const parsed = JSON.parse(json);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function loadSavedRoutes(): SavedRoute[] {
  try {
    return safeParse(localStorage.getItem(KEY));
  } catch {
    return []; // private-browsing / storage-blocked -- degrade quietly
  }
}

function persist(routes: SavedRoute[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(routes));
  } catch {
    // storage unavailable -- the route list just won't survive a reload
  }
}

// Seeds Rachel's Tampines -> Raffles Place demo route once, on first ever
// load, as a worked example of what "save your daily route" means. Never
// re-adds it if the user has deleted it.
const SEEDED_KEY = "commuter-companion:seeded-rachel:v1";

export function ensureSeeded(): SavedRoute[] {
  let routes = loadSavedRoutes();
  let alreadySeeded = false;
  try {
    alreadySeeded = localStorage.getItem(SEEDED_KEY) === "1";
  } catch {
    alreadySeeded = routes.length > 0;
  }

  if (!alreadySeeded) {
    routes = [
      {
        id: "rachel-demo",
        label: "Work (Tampines → Raffles Place)",
        kind: "rachel-demo",
        createdAt: Date.now(),
      },
      ...routes,
    ];
    persist(routes);
    try {
      localStorage.setItem(SEEDED_KEY, "1");
    } catch {
      /* ignore */
    }
  }
  return routes;
}

// Deliberately its own type rather than `Omit<SavedRoute, "id"|"createdAt">`:
// Omit collapses a discriminated union down to its *common* keys (id/label/
// kind/createdAt here), which would silently drop origin/destination from
// the "custom" branch entirely rather than just making them optional.
export type NewSavedRoute =
  | { label: string; kind: "rachel-demo" }
  | { label: string; kind: "custom"; origin: string; destination: string };

export function addSavedRoute(route: NewSavedRoute): SavedRoute[] {
  const routes = loadSavedRoutes();
  const next: SavedRoute = { ...route, id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, createdAt: Date.now() };
  const updated = [...routes, next];
  persist(updated);
  return updated;
}

export function removeSavedRoute(id: string): SavedRoute[] {
  const updated = loadSavedRoutes().filter((r) => r.id !== id);
  persist(updated);
  return updated;
}
