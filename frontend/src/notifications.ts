// Disruption notifications via the browser Notification API -- no service
// worker, no push server, no account. Works while this tab is open or
// backgrounded (not after the browser is fully closed -- see README
// "Known limitations" for why that tradeoff was chosen).

import type { Advice } from "./api";
import type { SavedRoute } from "./storage";

export function notificationsSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function getPermission(): NotificationPermission {
  if (!notificationsSupported()) return "denied";
  return Notification.permission;
}

export async function requestPermission(): Promise<NotificationPermission> {
  if (!notificationsSupported()) return "denied";
  if (Notification.permission !== "default") return Notification.permission;
  try {
    return await Notification.requestPermission();
  } catch {
    return "denied";
  }
}

// route.id -> signature of the last disruption we already notified about,
// so a route that's disrupted across several 30s polls only interrupts the
// user once, not every poll. Deliberately in-memory (not persisted) --
// each fresh page load starts clean, which is the right default for a demo
// and avoids a stale "already notified" flag surviving a real reload days
// later.
const lastNotified = new Map<string, string>();

function signatureFor(advice: Advice): string {
  return `${advice.reason}:${advice.headline}`;
}

export function maybeNotify(route: SavedRoute, advice: Advice | null) {
  if (!advice || advice.reason !== "disruption") {
    return;
  }
  if (getPermission() !== "granted") return;

  const sig = signatureFor(advice);
  if (lastNotified.get(route.id) === sig) return; // already told them about exactly this
  lastNotified.set(route.id, sig);

  try {
    new Notification(`${route.label}: ${advice.headline}`, {
      body: advice.detail,
      tag: `commuter-companion-${route.id}`,
      icon: undefined,
    });
  } catch {
    // Some browsers (notably iOS Safari outside a PWA install) throw
    // rather than silently no-op -- fail quietly either way, the in-app
    // AdviceBanner still shows the same information.
  }
}
