import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import NetworkMap from "./NetworkMap.jsx";
import LogPanel from "./LogPanel.jsx";
import WinRateChart from "./WinRateChart.jsx";
import HarnessPanel from "./HarnessPanel.jsx";

// Speed presets for replaying stored games from Atlas. Training/evolution runs from the
// CLI (python -m backend.evolve); the UI watches the results land.
const SPEEDS = [
  { label: "1x", stepMs: 900, trainPerTick: 0 },
  { label: "10x", stepMs: 120, trainPerTick: 0 },
  { label: "100x", stepMs: 30, trainPerTick: 0 },
];

export default function App() {
  const [snapshot, setSnapshot] = useState(null);
  const [curve, setCurve] = useState([]);
  const [xLabel, setXLabel] = useState("games");
  const [status, setStatus] = useState({ episode: 0, win_rate: 0, states_learned: 0 });
  const [atlas, setAtlas] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [speedIdx, setSpeedIdx] = useState(0);
  const [hovered, setHovered] = useState(null);
  const [gameNo, setGameNo] = useState(1);

  const timer = useRef(null);
  const speed = SPEEDS[speedIdx];

  const refreshStatus = useCallback(async () => {
    const [s, c] = await Promise.all([api.status(), api.curve()]);
    setStatus(s);
    setCurve(c.curve || []);
    setXLabel(c.x_label || "games");
  }, []);

  useEffect(() => {
    api.health().then((h) => setAtlas(!!h.atlas_connected)).catch(() => {});
    api.state().then(setSnapshot).catch(() => {});
    refreshStatus();
  }, [refreshStatus]);

  const tick = useCallback(async () => {
    // In fast mode, also advance background self-play so the chart moves.
    if (speed.trainPerTick > 0) {
      await api.train(speed.trainPerTick);
      await refreshStatus();
    }
    const snap = await api.stepLive();
    setSnapshot(snap);
    if (snap.finished) {
      refreshStatus();
      // Brief pause on the result, then auto-start the next game.
      setTimeout(async () => {
        const fresh = await api.newLive();
        setSnapshot(fresh);
        setGameNo((g) => g + 1);
      }, speed.stepMs * 3);
    }
  }, [speed, refreshStatus]);

  useEffect(() => {
    if (!playing) return;
    timer.current = setInterval(tick, speed.stepMs);
    return () => clearInterval(timer.current);
  }, [playing, tick, speed.stepMs]);

  const onStep = async () => {
    const snap = await api.stepLive();
    setSnapshot(snap);
    if (snap.finished) {
      const fresh = await api.newLive();
      setTimeout(() => { setSnapshot(fresh); setGameNo((g) => g + 1); }, 400);
    }
  };

  const redOwned = (snapshot?.nodes || []).filter((n) => n.owner === "red").length;
  const result = snapshot?.result;
  const winPct = Math.round((status.win_rate || 0) * 100);

  return (
    <div className="app">
      {/* TOP BAR */}
      <header className="topbar">
        <div className="brand">
          Red <span className="vs">vs.</span> Blue
          <span className="tagline">a cyber defense game that teaches itself</span>
        </div>
        <div className="stats">
          <span>Game <b>{snapshot?.game?._id ?? "-"}</b></span>
          <span>Level <b>{snapshot?.game?.level ?? "-"}</b> (unlocked {status.current_level ?? 1})</span>
          <span>Harness <b>v{snapshot?.game?.harness_version ?? "-"}</b></span>
          <span>Memory <b>{snapshot?.game?.memory_enabled ? "on" : "off"}</b></span>
          <span>Turn <b>{snapshot?.turn ?? 0} / 20</b></span>
          <span>Red owns <b>{redOwned}</b></span>
          <span>Blue win rate (last 20) <b className="rate">{winPct}%</b></span>
          <span className={`atlas ${atlas ? "on" : "off"}`}>
            {atlas ? "● Atlas connected" : "○ Atlas offline"}
          </span>
        </div>
      </header>

      {/* MAIN */}
      <div className="main">
        <section className="left">
          <NetworkMap snapshot={snapshot} hovered={hovered} onHoverNode={setHovered} />
          <div className="legend">
            <span><i className="dot safe" /> Safe</span>
            <span><i className="dot under_attack" /> Under attack</span>
            <span><i className="dot taken" /> Taken by Red</span>
            <span><i className="dot offline" /> Offline</span>
          </div>
          {result && (
            <div className={`banner ${result.winner}`}>
              {result.winner.toUpperCase()} wins — {result.reason}
            </div>
          )}
        </section>

        <aside className="right">
          <LogPanel log={snapshot?.log} hovered={hovered} onHoverNode={setHovered} />
          <WinRateChart curve={curve} xLabel={xLabel} />
          <HarnessPanel />
        </aside>
      </div>

      {/* CONTROLS */}
      <footer className="controls">
        <div className="ctl-buttons">
          <button className={playing ? "primary active" : "primary"} onClick={() => setPlaying((p) => !p)}>
            {playing ? "⏸ Pause" : "▶ Play"}
          </button>
          <button onClick={onStep} disabled={playing}>⏭ Step</button>
          <button onClick={async () => { const f = await api.newLive(); setSnapshot(f); setGameNo((g) => g + 1); }}>
            ⟳ New game
          </button>
        </div>
        <div className="ctl-speed">
          <span>Speed:</span>
          {SPEEDS.map((s, i) => (
            <button
              key={s.label}
              className={i === speedIdx ? "chip active" : "chip"}
              onClick={() => setSpeedIdx(i)}
            >
              {s.label}
            </button>
          ))}
          <span className="hint">
            replaying real games from Atlas (newest first)
          </span>
        </div>
        <div className="ctl-meta">
          {status.states_learned} lessons in memory · harness v{status.harness_version ?? 0} ·{" "}
          {status.generations ?? 0} generations · {status.episode.toLocaleString()} games
        </div>
      </footer>
    </div>
  );
}
