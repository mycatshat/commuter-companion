import type { SavedRoute } from "../storage";

interface Props {
  routes: SavedRoute[];
  onSelect: (route: SavedRoute) => void;
  onRemove: (id: string) => void;
  onPlanNew: () => void;
  notificationPermission: NotificationPermission | "unsupported";
  onEnableNotifications: () => void;
}

export default function SavedRoutesHome({
  routes,
  onSelect,
  onRemove,
  onPlanNew,
  notificationPermission,
  onEnableNotifications,
}: Props) {
  return (
    <div className="home-screen">
      <h2 className="home-heading">Your routes</h2>

      {notificationPermission === "default" && routes.length > 0 && (
        <button className="notify-nudge" onClick={onEnableNotifications}>
          <span className="icon">{"🔔"}</span>
          <span>
            <strong>Get warned about disruptions</strong>
            <br />
            Turn on notifications for your saved routes.
          </span>
        </button>
      )}
      {notificationPermission === "denied" && (
        <p className="notify-denied">
          Notifications are blocked in this browser. You'll still see disruption warnings when you open the app.
        </p>
      )}

      {routes.length === 0 && (
        <p className="home-empty">No saved routes yet. Plan a trip, then save it as your Work or School commute.</p>
      )}

      <div className="saved-route-list">
        {routes.map((r) => (
          <div className="saved-route-card" key={r.id}>
            <button className="saved-route-main" onClick={() => onSelect(r)}>
              <span className="saved-route-label">{r.label}</span>
              <span className="saved-route-sub">
                {r.kind === "rachel-demo" ? "Fixed-schedule demo · 07:40 daily" : `${r.origin} → ${r.destination}`}
              </span>
            </button>
            <button
              className="saved-route-remove"
              aria-label={`Remove ${r.label}`}
              onClick={() => onRemove(r.id)}
            >
              {"✕"}
            </button>
          </div>
        ))}
      </div>

      <button className="primary-button" onClick={onPlanNew}>
        + Plan a new trip
      </button>
    </div>
  );
}
