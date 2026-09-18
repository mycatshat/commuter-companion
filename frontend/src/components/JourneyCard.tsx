import type { CSSProperties } from "react";
import type { Leg, Route } from "../api";
import { lineColor } from "../lineColors";

function fmtMin(seconds: number): string {
  return `${Math.round(seconds / 60)} min`;
}

function legBadge(leg: Leg): { cls: string; label: string; style?: CSSProperties } {
  if (leg.mode === "walk") return { cls: "leg-badge walk", label: "🚶" };
  if (leg.mode === "rail") {
    return {
      cls: `leg-badge rail${leg.affected ? " affected" : ""}`,
      label: "🚆",
      style: leg.affected ? undefined : { background: lineColor(leg.line) },
    };
  }
  return { cls: "leg-badge bus", label: "🚌" };
}

function legTitle(leg: Leg): string {
  if (leg.mode === "walk") return leg.label;
  return `${leg.from.name} → ${leg.to.name}`;
}

function legSub(leg: Leg): string {
  if (leg.mode === "walk") return `${Math.round(leg.distance_m)} m walk`;
  if (leg.mode === "rail") {
    if (leg.affected) return `${leg.line} – delayed segment`;
    return `${leg.line} · ${leg.stops} ${leg.stops === 1 ? "stop" : "stops"}`;
  }
  return leg.free ? "Free bus (LTA mitigation)" : "Bus";
}

interface Props {
  routes: Route[];
  selectedRouteId: string;
  recommendedRouteId: string;
  onSelect: (routeId: string) => void;
}

export default function JourneyCard({ routes, selectedRouteId, recommendedRouteId, onSelect }: Props) {
  const selected = routes.find((r) => r.id === selectedRouteId) ?? routes[0];
  if (!selected) return null;

  const lowMin = Math.round((selected.total_duration_s - selected.uncertainty_s) / 60);
  const highMin = Math.round((selected.total_duration_s + selected.uncertainty_s) / 60);

  return (
    <div className="journey-sheet">
      {routes.length > 1 && (
        <div className="route-tabs">
          {routes.map((r) => {
            const rLow = Math.round((r.total_duration_s - r.uncertainty_s) / 60);
            const rHigh = Math.round((r.total_duration_s + r.uncertainty_s) / 60);
            return (
              <button
                key={r.id}
                className={`route-tab${r.id === selectedRouteId ? " active" : ""}`}
                onClick={() => onSelect(r.id)}
                aria-pressed={r.id === selectedRouteId}
              >
                <span className="tab-label">{r.label}</span>
                <span className="tab-time">
                  {rLow}–{rHigh} min
                </span>
                {r.id === recommendedRouteId && <span className="recommended-pill">Recommended</span>}
              </button>
            );
          })}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
        <strong style={{ fontSize: 13 }}>Door to door</strong>
        <span style={{ fontVariantNumeric: "tabular-nums", fontWeight: 700 }}>
          {lowMin}–{highMin} min
        </span>
      </div>

      <div className="legs-list">
        {selected.legs.map((leg, i) => {
          const badge = legBadge(leg);
          const affected = leg.mode === "rail" && leg.affected;
          return (
            <div className={`leg-row${affected ? " affected" : ""}`} key={i}>
              <span className={badge.cls} aria-hidden="true" style={badge.style}>
                {badge.label}
              </span>
              <div className="leg-text">
                <div className="leg-title">{legTitle(leg)}</div>
                <div className="leg-sub">{legSub(leg)}</div>
              </div>
              <span className="leg-duration">{fmtMin(leg.duration_s)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
