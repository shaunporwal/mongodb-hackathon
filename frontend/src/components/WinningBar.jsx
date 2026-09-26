// Top bar's red/blue split bar -- distinct from the bottom panel's win-rate
// *history* chart. This one just shows this instant's estimated split.
// Red is the side climbing now, so the fill grows in red as it wins more.
export function WinningBar({ redPct }) {
  const red = Math.max(0, Math.min(100, redPct));
  return (
    <div className="winning-bar-wrap">
      <div className="k">Red win rate: {red}%</div>
      <div className="winning-bar">
        <div className="winning-bar-fill" style={{ width: `${red}%` }} />
      </div>
    </div>
  );
}
