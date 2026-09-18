import type { Advice } from "../api";

const ICONS: Record<string, string> = {
  info: "ℹ️",
  warning: "⚠️",
  critical: "⛔",
};

interface Props {
  advice: Advice | null;
  // Only present on Rachel's fixed-schedule demo (/journey); an ad-hoc
  // /plan trip has no fixed departure time to reference.
  usualDeparture?: string;
}

/**
 * The one moment the brief cares about most: "reaches the commuter before
 * the problem does" + "recommends an action, not just a status." When
 * there's nothing worth interrupting Rachel for, this renders a quiet,
 * visually de-emphasised strip rather than nothing at all -- on a real
 * phone a blank space where a banner might be reads as "did this load?",
 * whereas Section 2.2 asks for silence *from being bothered*, not silence
 * from the interface.
 */
export default function AdviceBanner({ advice, usualDeparture }: Props) {
  if (!advice) {
    return (
      <div className="advice-banner quiet" role="status">
        <span className="icon">{"✅"}</span>
        <div>
          <p className="headline">{usualDeparture ? `All clear for your ${usualDeparture} trip` : "All clear for this trip"}</p>
          <p className="detail">
            {usualDeparture
              ? "No disruption, no unusual crowding. Nothing you need to do differently today."
              : "No disruption on this route right now."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`advice-banner ${advice.severity}`} role="alert">
      <span className="icon">{ICONS[advice.severity]}</span>
      <div>
        <p className="headline">{advice.headline}</p>
        <p className="detail">{advice.detail}</p>
      </div>
    </div>
  );
}
