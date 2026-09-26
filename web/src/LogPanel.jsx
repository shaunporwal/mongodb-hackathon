import React from "react";

// Running play-by-play. Newest at top (per the design brief). Hovering a line
// highlights its node on the map, and vice versa.
export default function LogPanel({ log, hovered, onHoverNode }) {
  const entries = [...(log || [])].reverse();
  return (
    <div className="log">
      <div className="log-title">THE LOG</div>
      <div className="log-scroll">
        {entries.map((e, i) => {
          if (e.side === "result") {
            return (
              <div key={i} className="log-line result">
                <span className="badge result">RESULT</span>
                <span className="log-text">{e.text}</span>
              </div>
            );
          }
          const cls = e.side === "red" ? "red" : "blue";
          return (
            <div
              key={i}
              className={`log-line ${cls} ${hovered === e.target ? "hi" : ""} ${
                e.success ? "" : "fail"
              } ${e.side === "red" && e.detected === false ? "unseen" : ""}`}
              title={e.side === "red" && e.detected === false ? "Blue did not see this move" : ""}
              onMouseEnter={() => onHoverNode?.(e.target)}
              onMouseLeave={() => onHoverNode?.(null)}
            >
              <span className={`badge ${cls}`}>{e.side.toUpperCase()}</span>
              <span className="turn">T{e.turn}</span>
              <span className="log-text">
                {e.text}
                {e.side === "blue" && e.reason && <span className="log-reason">why: {e.reason}</span>}
                {e.side === "blue" && e.recalled?.length > 0 && (
                  <span className="log-reason">recalled {e.recalled.length} lesson(s): {e.recalled.join(", ")}</span>
                )}
                {e.guardrail_blocked && <span className="log-reason guard">guardrail: {e.guardrail_blocked}</span>}
              </span>
            </div>
          );
        })}
        {entries.length === 0 && <div className="log-empty">Press Play to begin…</div>}
      </div>
    </div>
  );
}
