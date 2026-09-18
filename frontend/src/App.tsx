import { useCallback, useEffect, useRef, useState } from "react";
import { fetchJourney, fetchPlan, type Scenario, type TripResult } from "./api";
import MapView from "./components/MapView";
import AdviceBanner from "./components/AdviceBanner";
import JourneyCard from "./components/JourneyCard";
import CrowdingLegend from "./components/CrowdingLegend";
import ScenarioPicker from "./components/ScenarioPicker";
import SavedRoutesHome from "./components/SavedRoutesHome";
import TripPlanner from "./components/TripPlanner";
import { ensureSeeded, addSavedRoute, removeSavedRoute, type SavedRoute } from "./storage";
import { getPermission, requestPermission, maybeNotify } from "./notifications";

const REFRESH_MS = 30_000;

type Screen = "home" | "planning" | "results";

// The trip currently being shown on the results screen -- either one of the
// saved routes, or a not-yet-saved ad-hoc plan.
type ActiveTrip = SavedRoute | { id: "adhoc"; kind: "custom"; label: string; origin: string; destination: string };

export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [scenario, setScenario] = useState<Scenario>("normal");
  const [savedRoutes, setSavedRoutes] = useState<SavedRoute[]>([]);
  const [activeTrip, setActiveTrip] = useState<ActiveTrip | null>(null);

  const [data, setData] = useState<TripResult | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [notifPermission, setNotifPermission] = useState<NotificationPermission | "unsupported">(getPermission());
  const [saveFormOpen, setSaveFormOpen] = useState(false);
  const [saveLabel, setSaveLabel] = useState("");
  const [justSaved, setJustSaved] = useState(false);

  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;
  const savedRoutesRef = useRef(savedRoutes);
  savedRoutesRef.current = savedRoutes;

  useEffect(() => {
    setSavedRoutes(ensureSeeded());
  }, []);

  const fetchForRoute = useCallback(async (route: ActiveTrip, s: Scenario): Promise<TripResult> => {
    if (route.kind === "rachel-demo") return fetchJourney(s);
    return fetchPlan(route.origin, route.destination, s);
  }, []);

  const loadActiveTrip = useCallback(
    async (route: ActiveTrip, s: Scenario, opts: { silent?: boolean } = {}) => {
      if (!navigator.onLine) return;
      if (!opts.silent) setLoading(true);
      setError(null);
      try {
        const res = await fetchForRoute(route, s);
        setData(res);
        setSelectedRouteId(res.recommended_route_id);
        setLastUpdated(new Date());
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    [fetchForRoute]
  );

  // Re-fetch whenever the active trip or scenario changes.
  useEffect(() => {
    if (screen === "results" && activeTrip) {
      loadActiveTrip(activeTrip, scenario);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTrip, scenario, screen]);

  // Background refresh of whatever's on screen, AND a disruption check
  // across every saved route (not just the one being viewed) so a
  // notification can fire for "School" while you're looking at "Work".
  useEffect(() => {
    const id = setInterval(async () => {
      if (screen === "results" && activeTrip) {
        loadActiveTrip(activeTrip, scenarioRef.current, { silent: true });
      }
      for (const route of savedRoutesRef.current) {
        try {
          const res = await fetchForRoute(route, scenarioRef.current);
          maybeNotify(route, res.advice);
        } catch {
          // offline or backend unreachable -- skip this route this tick
        }
      }
    }, REFRESH_MS);
    return () => clearInterval(id);
  }, [screen, activeTrip, loadActiveTrip, fetchForRoute]);

  // Also check immediately once saved routes first load (don't make the
  // user wait 30s for the first disruption check).
  useEffect(() => {
    if (savedRoutes.length === 0) return;
    (async () => {
      for (const route of savedRoutes) {
        try {
          const res = await fetchForRoute(route, scenarioRef.current);
          maybeNotify(route, res.advice);
        } catch {
          /* ignore */
        }
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedRoutes.length]);

  useEffect(() => {
    const onOnline = () => {
      setIsOnline(true);
      if (screen === "results" && activeTrip) loadActiveTrip(activeTrip, scenarioRef.current, { silent: true });
    };
    const onOffline = () => setIsOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, [screen, activeTrip, loadActiveTrip]);

  const openRoute = (route: ActiveTrip) => {
    setActiveTrip(route);
    setData(null);
    setSaveFormOpen(false);
    setJustSaved(false);
    setScreen("results");
  };

  const handlePlan = (origin: string, destination: string) => {
    openRoute({ id: "adhoc", kind: "custom", label: `${origin} → ${destination}`, origin, destination });
  };

  const handleEnableNotifications = async () => {
    const perm = await requestPermission();
    setNotifPermission(perm);
  };

  const handleSaveRoute = () => {
    if (!activeTrip || activeTrip.kind !== "custom") return;
    const label = saveLabel.trim() || activeTrip.label;
    const updated = addSavedRoute({ label, kind: "custom", origin: activeTrip.origin, destination: activeTrip.destination });
    setSavedRoutes(updated);
    setSaveFormOpen(false);
    setJustSaved(true);
  };

  const stale = !isOnline || (error !== null && data !== null);
  // Captured as its own precisely-typed const (rather than re-narrowing
  // `activeTrip` inline) so it can be referenced safely from inside the
  // onClick closures below -- narrowing a union via a conditional does not
  // reliably carry into a nested arrow function, but a const already typed
  // to the "custom" shape needs no narrowing to use.
  const customTrip = activeTrip !== null && activeTrip.kind === "custom" ? activeTrip : null;
  const alreadySaved =
    customTrip !== null &&
    savedRoutes.some((r) => r.kind === "custom" && r.origin === customTrip.origin && r.destination === customTrip.destination);

  return (
    <div className="app">
      <div className="topbar">
        <div className="topbar-left">
          {screen !== "home" && (
            <button
              type="button"
              className="back-button"
              onClick={() => setScreen("home")}
              aria-label="Back to home"
            >
              <span aria-hidden="true">&larr;</span> Back
            </button>
          )}
          <div>
            <h1
              onClick={() => setScreen("home")}
              role="button"
              tabIndex={0}
              style={{ cursor: "pointer" }}
            >
              Commuter Companion
            </h1>
            <span className="persona-tag">
              {screen === "results" && activeTrip
                ? activeTrip.kind === "rachel-demo"
                  ? "Rachel · Tampines → Raffles Place"
                  : activeTrip.label
                : screen === "planning"
                ? "Plan a new trip"
                : "Your saved routes"}
            </span>
          </div>
        </div>
        <ScenarioPicker value={scenario} onChange={setScenario} />
      </div>

      {screen === "home" && (
        <SavedRoutesHome
          routes={savedRoutes}
          onSelect={openRoute}
          onRemove={(id) => setSavedRoutes(removeSavedRoute(id))}
          onPlanNew={() => setScreen("planning")}
          notificationPermission={notifPermission}
          onEnableNotifications={handleEnableNotifications}
        />
      )}

      {screen === "planning" && <TripPlanner onPlan={handlePlan} onCancel={() => setScreen("home")} />}

      {screen === "results" && (
        <>
          {stale && data && (
            <div className="advice-banner quiet" role="status" style={{ marginBottom: 0 }}>
              <span className="icon">{"📶"}</span>
              <div>
                <p className="headline">{isOnline ? "Couldn't refresh" : "Offline"}</p>
                <p className="detail">
                  Showing your last known journey from{" "}
                  {lastUpdated?.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}. This is normal
                  between stations underground &mdash; it'll refresh once you're back in signal.
                </p>
              </div>
            </div>
          )}

          {loading && !data && <div className="loading">Loading your journey&hellip;</div>}

          {error && !data && (
            <div className="error-box">
              Couldn't reach the backend ({error}). Is it running at the URL in VITE_API_BASE_URL?
            </div>
          )}

          {data && (
            <>
              <AdviceBanner advice={data.advice} usualDeparture={data.journey_meta?.usual_departure} />

              <div className="map-wrap">
                <MapView
                  routes={data.routes}
                  selectedRouteId={selectedRouteId ?? data.recommended_route_id}
                  crowdNow={data.crowd_now}
                />
                <CrowdingLegend />
              </div>

              <JourneyCard
                routes={data.routes}
                selectedRouteId={selectedRouteId ?? data.recommended_route_id}
                recommendedRouteId={data.recommended_route_id}
                onSelect={setSelectedRouteId}
              />

              {customTrip !== null && !alreadySaved && !justSaved && (
                <div className="save-route-bar">
                  {!saveFormOpen ? (
                    <button className="text-button" onClick={() => { setSaveFormOpen(true); setSaveLabel(customTrip.label); }}>
                      {"☆"} Save this route
                    </button>
                  ) : (
                    <div className="save-route-form">
                      <input
                        type="text"
                        value={saveLabel}
                        placeholder="e.g. Work, School"
                        onChange={(e) => setSaveLabel(e.target.value)}
                      />
                      <button className="primary-button small" onClick={handleSaveRoute}>
                        Save
                      </button>
                      <button className="text-button" onClick={() => setSaveFormOpen(false)}>
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              )}
              {justSaved && <p className="save-route-confirm">Saved — find it on your home screen.</p>}

              <p className="osm-note">&copy; OpenStreetMap contributors</p>
            </>
          )}
        </>
      )}
    </div>
  );
}
