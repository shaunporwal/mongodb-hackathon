import { lazy, Suspense, useState } from "react";
import { ArrowCounterClockwise, Crown, Eye, Key, LockKey, MagnifyingGlass, Warning, Globe, WifiHigh, Laptop, DesktopTower, Printer, Brain } from "@phosphor-icons/react";
import { EDGES, NODES } from "../data/network";
import { COLORS, STATUS_COLORS, STATUS_LABELS } from "../lib/colors";
import { Legend } from "./Legend";

const VoiceSphereScene = lazy(() => import("../three/VoiceSphereScene").then((module) => ({ default: module.VoiceSphereScene })));
const ICONS = { internet: Globe, router: WifiHigh, laptopA: Laptop, laptopB: Laptop, server: DesktopTower, printer: Printer, database: Crown };
const ACTIONS = { isolate: LockKey, reset_creds: Key, scan: MagnifyingGlass, review_logins: Eye, restore: ArrowCounterClockwise };
const nodeById = (id) => NODES.find((node) => node.id === id);
const route = (a, b) => { const mid = (a.pos[0] + b.pos[0]) / 2; return `M${a.pos[0]},${a.pos[1]} C${mid},${a.pos[1]} ${mid},${b.pos[1]} ${b.pos[0]},${b.pos[1]}`; };

export function NetworkScene({ state, hoveredNodeId, onHoverNode, isPlaying }) {
  const [selectedId, setSelectedId] = useState(null);
  const event = state.currentEvent;
  const latestMemory = state.log.find((entry) => entry.side === "MEM");
  const inspected = nodeById(hoveredNodeId || selectedId);
  const eventColor = event?.side === "red" ? COLORS.red : COLORS.blue;
  const source = nodeById(event?.from);
  const target = nodeById(event?.target);
  const actionPath = source && target && source.id !== target.id ? route(source, target) : null;

  return (
    <div className={`panel network-scene${isPlaying ? "" : " arena-paused"}`}>
      <div className="section-heading"><h3>01 / Network arena</h3><span className="section-meta"><Crown size={12} /> Objective: Database</span></div>
      <div className="arena-stage">
        <Suspense fallback={null}><VoiceSphereScene /></Suspense>
        <svg viewBox="0 0 1000 560" className="network-svg" aria-label="Interactive network arena">
          <defs>
            <filter id="glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="6" /></filter>
            {Object.entries(STATUS_COLORS).map(([status, color]) => <radialGradient key={status} id={`device-${status}`} cx="35%" cy="25%"><stop stopColor={color} stopOpacity=".24" /><stop offset="1" stopColor={COLORS.panel} /></radialGradient>)}
          </defs>
          {EDGES.map(([aId, bId]) => <path key={`${aId}-${bId}`} d={route(nodeById(aId), nodeById(bId))} fill="none" stroke={COLORS.line} strokeWidth="2" opacity=".38" />)}
          {actionPath && <g>
            <path d={actionPath} fill="none" stroke={eventColor} strokeWidth="9" opacity=".15" filter="url(#glow)" />
            <path d={actionPath} fill="none" stroke={eventColor} strokeWidth="2.5" opacity=".85" strokeDasharray={event.success === false ? "7 7" : undefined} />
            {isPlaying && [0, 1, 2].map((index) => <circle key={`${state.log[0]?.id}-${index}`} className="network-traffic" r="3.5" fill={eventColor}><animateMotion dur="1.8s" begin={`${index * -0.6}s`} repeatCount="indefinite" path={actionPath} /></circle>)}
          </g>}
          {NODES.map((node) => {
            const status = state.nodeStatus[node.id] ?? "safe";
            const color = STATUS_COLORS[status];
            const active = event?.target === node.id;
            const hovered = hoveredNodeId === node.id || selectedId === node.id;
            const Icon = ICONS[node.id];
            const ActionIcon = active && event?.side === "blue" ? ACTIONS[event.action] : null;
            const radius = node.r + 6;
            return <g key={node.id} className="arena-device" role="button" tabIndex={0} aria-label={`${node.name}: ${STATUS_LABELS[status]}. Inspect device`} aria-pressed={selectedId === node.id}
              onMouseEnter={() => onHoverNode(node.id)} onMouseLeave={() => onHoverNode(null)}
              onFocus={() => onHoverNode(node.id)} onBlur={() => onHoverNode(null)}
              onClick={() => setSelectedId(selectedId === node.id ? null : node.id)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setSelectedId(selectedId === node.id ? null : node.id); } if (e.key === "Escape") setSelectedId(null); }}>
              <circle className={`node-halo${active ? " node-halo-active" : ""}`} cx={node.pos[0]} cy={node.pos[1]} r={radius} fill="none" stroke={eventColor} strokeWidth="1.5" style={{ transformOrigin: `${node.pos[0]}px ${node.pos[1]}px` }} />
              <circle className={`node-disc${active ? " node-disc-active" : ""}${hovered ? " node-disc-hovered" : ""}`} cx={node.pos[0]} cy={node.pos[1]} r={radius} fill={`url(#device-${status})`} stroke={node.crownJewel ? COLORS.amber : color} strokeWidth={active ? 2.5 : 1.8} style={{ transformOrigin: `${node.pos[0]}px ${node.pos[1]}px` }} />
              <foreignObject x={node.pos[0] - 14} y={node.pos[1] - 14} width="28" height="28" style={{ pointerEvents: "none" }}><Icon size={28} weight={node.crownJewel ? "fill" : "regular"} color={node.crownJewel ? COLORS.amber : COLORS.text} /></foreignObject>
              <text x={node.pos[0]} y={node.pos[1] + radius + 27} fill={COLORS.text} fontSize="16" fontWeight="600" textAnchor="middle">{node.name}</text>
              <text className="device-status" x={node.pos[0]} y={node.pos[1] + radius + 45} fill={node.crownJewel ? COLORS.amber : color} fontSize="10" textAnchor="middle">{node.crownJewel ? "CROWN JEWEL" : STATUS_LABELS[status].toUpperCase()}</text>
              {ActionIcon && <foreignObject x={node.pos[0] - 44} y={node.pos[1] - radius - 35} width="88" height="22" style={{ overflow: "visible", pointerEvents: "none" }}><div className="node-action-badge"><ActionIcon size={11} />{event.action.replaceAll("_", " ")}</div></foreignObject>}
            </g>;
          })}
        </svg>
        <div className="arena-corner arena-corner-tl" /><div className="arena-corner arena-corner-br" />
      </div>
      <div className="arena-event" style={{ borderLeftColor: inspected ? STATUS_COLORS[state.nodeStatus[inspected.id]] : eventColor }}>
        {inspected ? <><Eye size={16} /><span><strong>{inspected.name}</strong><span>{STATUS_LABELS[state.nodeStatus[inspected.id]]}{inspected.crownJewel ? " · Capture this device to win" : " · Network device"}</span></span></> : <><Warning size={16} /><span><strong>{event ? `${event.side.toUpperCase()} · TURN ${event.turn}` : "READY"}</strong><span>{event?.text ?? "Waiting for the opening move"}</span></span></>}
      </div>
      <div className="arena-memory"><Brain size={15} /><span>{latestMemory ? <><strong>{latestMemory.recalledBy} recalled</strong> {latestMemory.text.replace(/^Recalled: /, "")}</> : "Recalled lessons will appear here during the replay."}</span></div>
      <Legend />
    </div>
  );
}
