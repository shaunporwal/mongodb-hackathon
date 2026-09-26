import React from "react";

// The "wow" chart: Blue's win rate climbing over thousands of self-play games.
// Pure inline SVG so there's no charting dependency.
export default function WinRateChart({ curve }) {
  const pts = curve || [];
  const W = 320, H = 120, pad = 22;
  const maxEp = pts.length ? pts[pts.length - 1].episode : 1;

  const x = (ep) => pad + (ep / Math.max(maxEp, 1)) * (W - pad * 2);
  const y = (r) => H - pad - r * (H - pad * 2); // r in 0..1

  const path = pts
    .map((p, i) => `${i === 0 ? "M" : "L"} ${x(p.episode).toFixed(1)} ${y(p.win_rate).toFixed(1)}`)
    .join(" ");

  const last = pts.length ? pts[pts.length - 1] : null;

  return (
    <div className="chart">
      <div className="chart-head">
        <span>Blue win rate over self-play games</span>
        {last && <span className="chart-now">{Math.round(last.win_rate * 100)}%</span>}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg">
        {/* 50% reference line */}
        <line x1={pad} y1={y(0.5)} x2={W - pad} y2={y(0.5)} className="grid" />
        <text x={pad} y={y(0.5) - 3} className="grid-label">50%</text>
        {/* axes */}
        <line x1={pad} y1={y(0)} x2={W - pad} y2={y(0)} className="axis" />
        <line x1={pad} y1={y(0)} x2={pad} y2={y(1)} className="axis" />
        {path && <path d={path} className="curve" />}
        {last && <circle cx={x(last.episode)} cy={y(last.win_rate)} r="2.6" className="curve-dot" />}
        <text x={W - pad} y={H - 6} className="grid-label end">{maxEp.toLocaleString()} games</text>
      </svg>
      {pts.length === 0 && <div className="chart-empty">Train to watch Blue learn →</div>}
    </div>
  );
}
