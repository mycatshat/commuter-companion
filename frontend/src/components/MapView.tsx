import { useEffect, useRef } from "react";
import maplibregl, { Map as MLMap, Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { CrowdInfo, Route, StationRef } from "../api";
import { lineColor } from "../lineColors";

/**
 * OpenFreeMap ("Liberty" style) -- a free, no-API-key vector tile service
 * built from OpenStreetMap data and explicitly intended for exactly this
 * kind of use (unlike tile.openstreetmap.org, whose usage policy forbids
 * bulk/app traffic -- see Section 2.3 of the brief). It is self-hostable
 * (https://openfreemap.org) if you outgrow the hosted endpoint.
 *
 * We still add an explicit AttributionControl below rather than relying on
 * the style to carry it, since "Display (c) OpenStreetMap contributors
 * wherever you show the map" is a mandatory condition, not a style default
 * to trust blindly.
 */
const MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

const CROWD_COLOR: Record<string, string> = {
  l: "#1f8a4c",
  m: "#b9860b",
  h: "#c23b3b",
  NA: "#8a8f8c",
};

// Shape (not just colour) per crowd level, so the map reads correctly for
// colour-blind users too -- Section 3.2.3's accessibility requirement.
function crowdMarkerEl(level: string): HTMLDivElement {
  const el = document.createElement("div");
  const color = CROWD_COLOR[level] ?? CROWD_COLOR.NA;
  el.style.width = "16px";
  el.style.height = "16px";
  el.style.background = color;
  el.style.border = "2px solid white";
  el.style.boxShadow = "0 1px 3px rgba(0,0,0,0.35)";
  if (level === "l") {
    el.style.borderRadius = "50%"; // circle = low
  } else if (level === "m") {
    el.style.borderRadius = "3px"; // square = moderate
  } else {
    el.style.borderRadius = "3px";
    el.style.transform = "rotate(45deg)"; // diamond = high
  }
  return el;
}

function legToLineString(leg: Route["legs"][number]): [number, number][] | null {
  // MapLibre/GeoJSON coordinate order is [lon, lat]; our API gives [lat, lon].
  if (leg.mode === "walk") {
    return leg.points.map(([lat, lon]) => [lon, lat]);
  }
  if (leg.mode === "rail") {
    // Real intermediate-station polyline (one continuous ride can span many
    // stops), not just a straight line between boarding and alighting.
    return leg.points.map(([lat, lon]) => [lon, lat]);
  }
  if (leg.mode === "bus") {
    return [
      [leg.from.lon, leg.from.lat],
      [leg.to.lon, leg.to.lat],
    ];
  }
  return null;
}

function routeLineColor(leg: Route["legs"][number], emphasise: boolean): string {
  if (leg.mode === "walk") return emphasise ? "#5b6b66" : "#a9b3af";
  if (leg.mode === "rail") {
    if (leg.affected) return "#c23b3b";
    const base = lineColor(leg.line);
    return emphasise ? base : `${base}88`; // dim (alpha) when not the selected route
  }
  if (leg.mode === "bus") return emphasise ? "#0b5fa5" : "#a8c7e0";
  return "#999";
}

interface Props {
  routes: Route[];
  selectedRouteId: string;
  // Only populated on Rachel's /journey response (EWL-scoped mock data --
  // see README). Absent on a general /plan trip; markers just show "no
  // data" grey diamonds rather than crashing.
  crowdNow?: Record<string, CrowdInfo>;
}

export default function MapView({ routes, selectedRouteId, crowdNow }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markersRef = useRef<Marker[]>([]);

  // Initialise the map once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
      center: [103.87, 1.32], // roughly the middle of the Tampines-Raffles Place corridor
      zoom: 11,
      attributionControl: false,
    });

    map.addControl(
      new maplibregl.AttributionControl({
        customAttribution: "© OpenStreetMap contributors",
      }),
      "bottom-right"
    );
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Redraw route layers + station markers whenever the data or selection changes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const draw = () => {
      // Clear old markers.
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      // Clear old route layers/sources (ids are stable per route+leg index).
      const style = map.getStyle();
      if (style?.layers) {
        for (const layer of style.layers) {
          if (layer.id.startsWith("route-")) {
            if (map.getLayer(layer.id)) map.removeLayer(layer.id);
          }
        }
      }
      if (style && "sources" in style) {
        for (const sourceId of Object.keys(style.sources ?? {})) {
          if (sourceId.startsWith("route-")) {
            if (map.getSource(sourceId)) map.removeSource(sourceId);
          }
        }
      }

      const allCoords: [number, number][] = [];
      const stationsSeen = new Map<string, StationRef>();

      // Draw the non-selected route(s) first (dimmed), selected route last
      // (on top, full colour) -- "the alternative shown against the
      // original, so the commuter can judge the trade-off."
      const ordered = [...routes].sort((a, b) =>
        a.id === selectedRouteId ? 1 : b.id === selectedRouteId ? -1 : 0
      );

      ordered.forEach((route) => {
        const emphasise = route.id === selectedRouteId;
        route.legs.forEach((leg, i) => {
          const coords = legToLineString(leg);
          if (!coords) return;
          coords.forEach((c) => allCoords.push(c));

          if (leg.mode === "rail" || leg.mode === "bus") {
            stationsSeen.set(leg.from.code, leg.from);
            stationsSeen.set(leg.to.code, leg.to);
          }

          const sourceId = `route-${route.id}-${i}`;
          map.addSource(sourceId, {
            type: "geojson",
            data: {
              type: "Feature",
              properties: {},
              geometry: { type: "LineString", coordinates: coords },
            },
          });

          const isDashed = leg.mode === "walk" || leg.mode === "bus";
          map.addLayer({
            id: sourceId,
            type: "line",
            source: sourceId,
            layout: { "line-join": "round", "line-cap": "round" },
            paint: {
              "line-color": routeLineColor(leg, emphasise),
              "line-width": emphasise ? (leg.mode === "rail" && leg.affected ? 6 : 5) : 3,
              "line-opacity": emphasise ? 1 : 0.55,
              ...(isDashed ? { "line-dasharray": [2, 1.5] } : {}),
            },
          });
        });
      });

      // Crowd markers at every station on the route.
      stationsSeen.forEach((station) => {
        const info = crowdNow?.[station.code];
        const level = info?.level ?? "NA";
        const el = crowdMarkerEl(level);
        el.title = `${station.name} (${station.code}): ${info?.label ?? "No data"} crowding`;
        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([station.lon, station.lat])
          .addTo(map);
        markersRef.current.push(marker);
      });

      if (allCoords.length > 0) {
        const lons = allCoords.map((c) => c[0]);
        const lats = allCoords.map((c) => c[1]);
        map.fitBounds(
          [
            [Math.min(...lons), Math.min(...lats)],
            [Math.max(...lons), Math.max(...lats)],
          ],
          { padding: { top: 40, bottom: 40, left: 30, right: 30 }, duration: 400, maxZoom: 14 }
        );
      }
    };

    if (map.isStyleLoaded()) {
      draw();
    } else {
      map.once("load", draw);
    }
  }, [routes, selectedRouteId, crowdNow]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
