import { Crosshair, ShieldCheck } from "@phosphor-icons/react";

export function ArenaHud({ state, isPlaying }) {
  const devices = Object.entries(state.nodeStatus).filter(([id]) => id !== "internet");
  const taken = devices.filter(([, status]) => status === "taken").length;
  const safe = devices.filter(([, status]) => status === "safe").length;
  return (
    <header className="arena-hud">
      <div className="arena-team arena-team-red">
        <Crosshair size={24} weight="duotone" />
        <div><span className="team-role">Learning attacker</span><h1>RED <span>TEAM</span></h1></div>
        <div className="team-score"><strong>{taken}<small> / {devices.length}</small></strong><span>devices captured</span></div>
      </div>
      <div className="arena-round"><span className="arena-level">DEFENSE LEVEL {state.level ?? 1}</span><strong>RED <span>vs</span> BLUE</strong><span className="arena-status">{state.result ? "Round complete" : isPlaying ? "Replay running" : "Replay paused"} · Turn {state.turn}/{state.maxTurns}</span></div>
      <div className="arena-team arena-team-blue">
        <div className="team-score"><strong>{safe}<small> / {devices.length}</small></strong><span>devices secure</span></div>
        <div><span className="team-role">Fixed defender</span><h2>BLUE <span>TEAM</span></h2></div>
        <ShieldCheck size={24} weight="duotone" />
      </div>
    </header>
  );
}
