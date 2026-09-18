import { useState } from "react";
import StationInput from "./StationInput";

interface Props {
  onPlan: (origin: string, destination: string) => void;
  onCancel: () => void;
  initialOrigin?: string;
  initialDestination?: string;
}

export default function TripPlanner({ onPlan, onCancel, initialOrigin, initialDestination }: Props) {
  const [origin, setOrigin] = useState(initialOrigin ?? "");
  const [destination, setDestination] = useState(initialDestination ?? "");

  const canPlan = origin.length > 0 && destination.length > 0 && origin !== destination;

  return (
    <div className="trip-planner">
      <div className="trip-planner-header">
        <button className="text-button" onClick={onCancel} aria-label="Back">
          {"←"} Back
        </button>
        <h2>Plan a trip</h2>
      </div>

      <StationInput label="From" placeholder="Search a station…" value={origin} onChange={setOrigin} />

      <button
        type="button"
        className="swap-button"
        aria-label="Swap origin and destination"
        onClick={() => {
          setOrigin(destination);
          setDestination(origin);
        }}
      >
        {"⇅"}
      </button>

      <StationInput label="To" placeholder="Search a station…" value={destination} onChange={setDestination} />

      {origin && destination && origin === destination && (
        <p className="trip-planner-error">Origin and destination must be different.</p>
      )}

      <button className="primary-button" disabled={!canPlan} onClick={() => canPlan && onPlan(origin, destination)}>
        Get route
      </button>
    </div>
  );
}
