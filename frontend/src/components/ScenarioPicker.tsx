import type { Scenario } from "../api";

const LABELS: Record<Scenario, string> = {
  normal: "Normal day",
  disruption: "EWL disruption",
  crowded: "Crowded platform",
  rain: "Rain",
};

interface Props {
  value: Scenario;
  onChange: (s: Scenario) => void;
}

/**
 * Judging aid, not a real product surface. Section 2.6 of the brief notes
 * that TrainServiceAlerts.AffectedSegments is empty on an ordinary day and
 * explicitly allows demonstrating the disruption path "by replay or
 * injected test data provided it is labelled as such." This control is
 * that label: it switches which mock scenario the backend serves, so a
 * judge can see the proactive/critical path without waiting for a real
 * signalling fault. Wire it to nothing (or hide it) once real DataMall
 * keys are live and USE_MOCK=false in backend/.env.
 */
export default function ScenarioPicker({ value, onChange }: Props) {
  return (
    <div className="scenario-picker">
      <label htmlFor="scenario-select" style={{ fontSize: 11, color: "var(--color-muted)" }}>
        Demo:
      </label>
      <select id="scenario-select" value={value} onChange={(e) => onChange(e.target.value as Scenario)}>
        {(Object.keys(LABELS) as Scenario[]).map((s) => (
          <option key={s} value={s}>
            {LABELS[s]}
          </option>
        ))}
      </select>
    </div>
  );
}
