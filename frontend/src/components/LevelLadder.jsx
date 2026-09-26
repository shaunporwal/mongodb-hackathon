const MAX_LEVEL = 5; // Blue's defenses come in 5 fixed difficulty levels (attacker_overview_for_ui_team.pdf)

// Red must beat level N before facing level N+1 -- this is that ladder,
// derived straight from the current game's `level` field (games.csv), no
// separate progress data needed.
export function LevelLadder({ currentLevel }) {
  const level = currentLevel ?? 1;

  return (
    <div className="panel ladder">
      <h3>05 / Defense progression</h3>
      <div className="ladder-track">
        {Array.from({ length: MAX_LEVEL }, (_, i) => i + 1).map((lvl) => {
          const cleared = lvl < level;
          const current = lvl === level;
          const heightPct = 26 + (lvl / MAX_LEVEL) * 64;
          return (
            <div key={lvl} className="ladder-col">
              <div
                className={["ladder-bar", cleared ? "ladder-bar-cleared" : "", current ? "ladder-bar-current" : ""].filter(Boolean).join(" ")}
                style={{ height: `${heightPct}%` }}
              >
                {cleared && <span className="ladder-bar-tag">cleared</span>}
                {current && <span className="ladder-bar-tag ladder-bar-tag-current">current</span>}
              </div>
              <div className="ladder-axis-label">Lvl {lvl}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
