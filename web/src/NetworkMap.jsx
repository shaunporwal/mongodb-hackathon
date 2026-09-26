import React, { useMemo } from "react";
import { NODE_POS, NODE_LABEL, STATE_COLOR } from "./layout.js";

// Renders the network as an SVG. Nodes are colored by ownership state.
// A red dashed pulse marks Red's most recent hop; a shield ring flashes on the
// node Blue just defended.
export default function NetworkMap({ snapshot, hovered, onHoverNode }) {
  const nodes = snapshot?.nodes || [];
  const edges = snapshot?.edges || [];
  const blocked = new Set((snapshot?.blocked || []).map((b) => b.slice().sort().join("|")));

  const lastLog = snapshot?.log?.[snapshot.log.length - 1];
  const redHop = useMemo(() => {
    const red = [...(snapshot?.log || [])].reverse().find((e) => e.side === "red");
    if (red && red.source && red.target && red.success) {
      return [red.source, red.target];
    }
    return null;
  }, [snapshot]);
  const blueTarget = useMemo(() => {
    const blue = [...(snapshot?.log || [])].reverse().find((e) => e.side === "blue");
    return blue?.success ? blue.target : null;
  }, [snapshot]);

  const posOf = (id) => NODE_POS[id] || { x: 50, y: 50 };

  return (
    <svg className="map" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
      {/* edges */}
      {edges.map(([a, b], i) => {
        const p1 = posOf(a), p2 = posOf(b);
        const key = [a, b].slice().sort().join("|");
        const isBlocked = blocked.has(key);
        const isHopEdge =
          redHop &&
          ((redHop[0] === a && redHop[1] === b) || (redHop[0] === b && redHop[1] === a));
        return (
          <g key={i}>
            <line
              x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
              className={isBlocked ? "edge blocked" : "edge"}
            />
            {isHopEdge && (
              <line
                x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                className="edge-pulse"
              />
            )}
          </g>
        );
      })}

      {/* nodes */}
      {nodes.map((n) => {
        const p = posOf(n.id);
        const color = STATE_COLOR[n.state] || "#888";
        const isHover = hovered === n.id;
        return (
          <g
            key={n.id}
            className="node-group"
            transform={`translate(${p.x} ${p.y})`}
            onMouseEnter={() => onHoverNode?.(n.id)}
            onMouseLeave={() => onHoverNode?.(null)}
          >
            {blueTarget === n.id && <circle className="shield-flash" r="7.5" />}
            {n.crown && <circle className="crown-ring" r="6.4" />}
            <circle
              r={n.crown ? 5 : 4.2}
              fill={color}
              className={`node ${isHover ? "hover" : ""} ${n.state}`}
            />
            {n.patched && <text className="patch-mark" y="1.4">🛡</text>}
            <text className="node-label" y={n.crown ? 9.6 : 8.4}>
              {NODE_LABEL[n.id] || n.id}
            </text>
            {n.crown && <text className="crown-label" y={12.4}>crown jewel</text>}
          </g>
        );
      })}
    </svg>
  );
}
