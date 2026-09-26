import { STATUS_COLORS, STATUS_LABELS } from "../lib/colors";

export function Legend() {
  return (
    <div className="legend">
      {Object.entries(STATUS_LABELS).map(([status, label]) => (
        <span key={status}>
          <i style={{ background: STATUS_COLORS[status] }} />
          {label}
        </span>
      ))}
      <span className="legend-note">Simulation only, no real network or exploits</span>
    </div>
  );
}
