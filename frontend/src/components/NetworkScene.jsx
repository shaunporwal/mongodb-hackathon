import { lazy, Suspense } from "react";
import { ArrowCounterClockwise, Crown, Eye, Key, LockKey, MagnifyingGlass, Warning } from "@phosphor-icons/react";
import { EDGES, NODES } from "../data/network";
import { COLORS, STATUS_COLORS } from "../lib/colors";
import { Legend } from "./Legend";

const VoiceSphereScene = lazy(() => import("../three/VoiceSphereScene").then((module) => ({ default: module.VoiceSphereScene })));

const BLUE_ACTION_BADGE = {
  isolate: { icon: LockKey, label: "ISOLATE" },
  reset_creds: { icon: Key, label: "RESET" },
  scan: { icon: MagnifyingGlass, label: "SCAN" },
  review_logins: { icon: Eye, label: "REVIEW" },
  restore: { icon: ArrowCounterClockwise, label: "RESTORE" },
};

function nodeById(id) {
  return NODES.find((n) => n.id === id);
}

function labelY(node) {
  return node.pos[1] + node.r + 24;
}

export function NetworkScene({ state, hoveredNodeId, onHoverNode }) {
  const targetNode = state.nextRedPreview?.target ? nodeById(state.nextRedPreview.target) : null;

  return (
    <div className="panel network-scene">
      <Suspense fallback={null}><VoiceSphereScene /></Suspense>
      <div className="section-heading"><h3>01 / Network topology</h3><span className="section-meta">7 devices · Replay</span></div>

      {state.nextRedPreview && (
        <div className="intent">
          <Warning size={14} weight="bold" />
          Red's next move{targetNode ? ` -> ${targetNode.name}` : ""}: {state.nextRedPreview.text}
        </div>
      )}

      <svg viewBox="0 0 1000 560" width="100%" height="100%" className="network-svg">
        <defs>
          <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="6" />
          </filter>
        </defs>

        {/* Edges */}
        {EDGES.map(([aId, bId]) => {
          const a = nodeById(aId);
          const b = nodeById(bId);
          const downstreamStatus = state.nodeStatus[bId] ?? "safe";
          const isHot = downstreamStatus !== "safe" && (bId === state.lastAttackTarget || aId === state.lastAttackTarget);
          const color = isHot ? STATUS_COLORS[downstreamStatus] : COLORS.line;
          return (
            <g key={`${aId}-${bId}`}>
              <line x1={a.pos[0]} y1={a.pos[1]} x2={b.pos[0]} y2={b.pos[1]} stroke={color} strokeWidth={isHot ? 6 : 3} opacity={isHot ? 0.7 : 0.5} strokeLinecap="round" />
              {isHot && (
                <circle className="network-traffic" r="5" fill={STATUS_COLORS[downstreamStatus]}>
                  <animateMotion dur="0.9s" repeatCount="indefinite" path={`M${a.pos[0]},${a.pos[1]} L${b.pos[0]},${b.pos[1]}`} />
                </circle>
              )}
            </g>
          );
        })}

        {/* Device rings retain status colors without decorative glass effects. */}
        {NODES.map((node) => {
          const status = state.nodeStatus[node.id] ?? "safe";
          const color = STATUS_COLORS[status];
          const isHovered = hoveredNodeId === node.id;
          const isBlueTarget = state.lastBlueTarget === node.id;
          const badge = isBlueTarget && state.log[0]?.side === "BLUE" ? BLUE_ACTION_BADGE[state.log[0]?.action] : null;
          const showGlow = node.id === state.lastAttackTarget && status !== "safe";
          const r = node.r;
          const newestEntry = state.log[0];
          const isPingTarget = newestEntry && newestEntry.nodeId === node.id;
          const pingColor = newestEntry?.side === "RED" ? COLORS.red : newestEntry?.side === "MEM" ? COLORS.green : COLORS.blue;

          return (
            <g key={node.id} onMouseEnter={() => onHoverNode(node.id)} onMouseLeave={() => onHoverNode(null)} style={{ cursor: "pointer" }}>
              {showGlow && <circle cx={node.pos[0]} cy={node.pos[1]} r={r + 16} fill={color} opacity="0.25" filter="url(#glow)" />}
              <circle className={`node-halo${isPingTarget ? " node-halo-active" : ""}`} cx={node.pos[0]} cy={node.pos[1]} r={r} fill="none" stroke={pingColor} strokeWidth="2" style={{ transformOrigin: `${node.pos[0]}px ${node.pos[1]}px` }} />
              <circle className={`node-disc${isPingTarget ? " node-disc-active" : ""}${isHovered ? " node-disc-hovered" : ""}`} cx={node.pos[0]} cy={node.pos[1]} r={r} fill={COLORS.panel} stroke={color} strokeWidth={node.crownJewel ? 3.5 : 2.5} style={{ transformOrigin: `${node.pos[0]}px ${node.pos[1]}px` }} />
              {!node.crownJewel && <circle cx={node.pos[0]} cy={node.pos[1]} r="5" fill={color} />}
              {node.crownJewel && (
                <foreignObject x={node.pos[0] - 11} y={node.pos[1] - 11} width="22" height="22" style={{ pointerEvents: "none" }}>
                  <Crown size={22} weight="fill" color={COLORS.amber} />
                </foreignObject>
              )}
              <text x={node.pos[0]} y={labelY(node)} fill={node.crownJewel ? COLORS.amber : COLORS.text} fontSize="15" fontWeight="600" textAnchor="middle" fontFamily="var(--font-sans)">
                {node.name}
              </text>
              {badge && (
                <foreignObject x={node.pos[0] - 44} y={node.pos[1] - r - 30} width="88" height="22" style={{ overflow: "visible", pointerEvents: "none" }}>
                  <div className="node-action-badge">
                    <badge.icon size={11} weight="bold" />
                    {badge.label}
                  </div>
                </foreignObject>
              )}

            </g>
          );
        })}
      </svg>

      <Legend />
    </div>
  );
}
