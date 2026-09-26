import { WinningBar } from "./WinningBar";

// Red is the side that learns now (attacker_overview_for_ui_team.pdf) --
// the headline stat line reads "Game #N | Beating Defense Level L | Red
// controls K devices | Red win rate: R%", Blue's 5 levels are fixed.
export function TopBar({ state }) {
  const latestWinRate = state.redWinRateHistory.at(-1) ?? 50;
  const redHeldCount = Object.values(state.nodeStatus).filter((s) => s === "taken").length;

  return (
    <div className="top-bar">
      <div className="top-bar-brand" aria-label="Red versus Blue">
        <img className="brand-mark" src="/logo-mark.svg" alt="" width="40" height="40" />
        <span className="brand-wordmark" aria-hidden="true">RED <span className="brand-versus">vs</span> BLUE</span>
      </div>
      <Stat label="Game" value={`#${state.gameNumber}`} />
      <Stat label="Def. level" value={state.level ?? "--"} />
      <Stat label="Turn" value={`${state.turn} / ${state.maxTurns || "?"}`} />
      <Stat label="Red controls" value={`${redHeldCount} device${redHeldCount === 1 ? "" : "s"}`} color={redHeldCount > 0 ? "var(--red)" : undefined} />
      <div className="top-bar-spacer" />
      <WinningBar redPct={Math.round(latestWinRate)} />
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div className="stat">
      <div className="k">{label}</div>
      <div className="v" style={color ? { color } : undefined}>{value}</div>
    </div>
  );
}
