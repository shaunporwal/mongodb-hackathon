import React, { useEffect, useState } from "react";
import { api } from "./api.js";

// Shows the self-improving harness: each proposed mutation, whether it was KEPT or
// rolled back after evaluation, and the win rates that decided it. This is the
// "recursive harnessing" story — the harness editing its own rules.
export default function HarnessPanel() {
  const [gens, setGens] = useState([]);

  useEffect(() => {
    const load = () => api.generations().then((d) => setGens(d.generations || [])).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="harness">
      <div className="harness-title">HARNESS EVOLUTION</div>
      <div className="harness-scroll">
        {gens.length === 0 && (
          <div className="harness-empty">
            Run <code>python -m backend.evolve</code> to watch the harness mutate.
          </div>
        )}
        {gens.map((g) => (
          <div key={g.version} className={`gen ${g.kept ? "kept" : "rolled"}`}>
            <div className="gen-head">
              <span className="gen-ver">v{g.version}</span>
              <span className="gen-from">from v{g.parent}</span>
              <span className={`gen-badge ${g.kept ? "kept" : "rolled"}`}>
                {g.kept ? "KEPT" : "ROLLED BACK"}
              </span>
              {g.level_unlocked && <span className="gen-unlock">→ L{g.level_unlocked} unlocked</span>}
            </div>
            <div className="gen-diff">{g.diff_summary}</div>
            {g.eval && (
              <div className="gen-eval">
                L{g.eval.level} · win {Math.round(g.eval.win_rate * 100)}% vs parent{" "}
                {Math.round(g.eval.parent_win_rate * 100)}% ({g.eval.games} games)
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
