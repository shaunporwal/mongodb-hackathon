import { useEffect, useRef } from "react";

export function LogPanel({ log, hoveredNodeId, onHoverNode }) {
  const listRef = useRef(null);
  const newestId = log[0]?.id;

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [newestId]);

  return (
    <div className="panel log-panel">
      <div className="section-heading"><h3>02 / Activity feed</h3><span className="section-meta">Newest first</span></div>
      <div className="log-list" ref={listRef}>
        {log.map((entry, index) => (
          <div
            key={entry.id}
            className={[
              "log-entry",
              `log-entry-${entry.side.toLowerCase()}`,
              index === 0 ? "log-entry-newest" : "",
              entry.nodeId && entry.nodeId === hoveredNodeId ? "log-entry-highlight" : "",
            ].filter(Boolean).join(" ")}
            onMouseEnter={() => entry.nodeId && onHoverNode(entry.nodeId)}
            onMouseLeave={() => onHoverNode(null)}
          >
            <div className="log-entry-main">
              <span className={`log-turn-tag log-turn-tag-${entry.side.toLowerCase()}`}>{entry.side === "RED" ? "R" : entry.side === "BLUE" ? "B" : "M"} / {String(entry.turn).padStart(2, "0")}</span>
              <span className="log-entry-text">{entry.text}</span>
            </div>
            {entry.detail && <div className="log-entry-detail">{entry.detail}</div>}
          </div>
        ))}
        {log.length === 0 && <div className="log-empty">Waiting for the first move...</div>}
      </div>
    </div>
  );
}
