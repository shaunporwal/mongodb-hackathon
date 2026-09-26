// "Show learning. A chart of the attacker's success rate climbing, game
// after game, is the centerpiece." (attacker_overview_for_ui_team.pdf) --
// Red is the learner now, so this tracks Red's win rate, not Blue's. The
// underlying number is still generations.csv's win_rate; Red's rate is just
// its complement in this zero-sum game (see useGameReplay.js).
const WIDTH = 800;
const HEIGHT = 120;
const AXIS_Y = 110;

export function WinRateSparkline({ history, gameNumber }) {
  if (history.length < 2) {
    return <div className="panel"><h3>04 / Attacker performance</h3><div className="chart-summary"><strong>{Math.round(history[0] ?? 0)}%</strong><span>Red win rate</span></div><div className="chart-empty">History appears after the next evaluation.</div></div>;
  }

  const max = 100;
  const stepX = WIDTH / (history.length - 1);
  const toY = (value) => AXIS_Y - (value / max) * (AXIS_Y - 10);
  const points = history.map((value, i) => `${(i * stepX).toFixed(1)},${toY(value).toFixed(1)}`).join(" ");
  const last = history.at(-1);
  const lastX = (history.length - 1) * stepX;

  return (
    <div className="panel">
      <h3>04 / Attacker performance</h3><div className="chart-summary"><strong>{Math.round(last)}%</strong><span>Red win rate · {gameNumber.toLocaleString()} games</span></div>
      <svg className="win-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} width="100%" height={HEIGHT}>
        <line x1="0" y1={AXIS_Y} x2={WIDTH} y2={AXIS_Y} stroke="var(--line)" />
        <polyline points={points} fill="none" stroke="var(--red)" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={lastX} cy={toY(last)} r="5" fill="var(--red)" />
        <text x={Math.max(0, lastX - 70)} y={toY(last) - 12} fill="var(--heading)" fontSize="14" fontWeight="600" fontFamily="var(--font-mono)">{Math.round(last)}%</text>
        <text x="4" y={toY(history[0]) - 6} fill="var(--mut)" fontSize="12" fontFamily="var(--font-mono)">{Math.round(history[0])}%</text>
      </svg>
    </div>
  );
}
