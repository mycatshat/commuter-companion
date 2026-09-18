export default function CrowdingLegend() {
  return (
    <div className="crowd-legend" aria-label="Platform crowding legend">
      <div className="row">
        <span className="crowd-dot l" /> Low
      </div>
      <div className="row">
        <span className="crowd-dot m" /> Moderate
      </div>
      <div className="row">
        <span className="crowd-dot h" /> High
      </div>
    </div>
  );
}
