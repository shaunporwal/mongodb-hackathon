import { useState } from "react";
import { useGameReplay } from "./hooks/useGameReplay";
import { ArenaHud } from "./components/ArenaHud";
import { TopBar } from "./components/TopBar";
import { NetworkScene } from "./components/NetworkScene";
import { LogPanel } from "./components/LogPanel";
import { BottomControls } from "./components/BottomControls";
import { WinRateSparkline } from "./components/WinRateSparkline";
import { LevelLadder } from "./components/LevelLadder";
import { ResultBanner } from "./components/ResultBanner";
import "./App.css";

// Rebuilt to replay *real* recorded games (public/data/*.csv, exported from
// the backend's MongoDB collections) instead of a scripted simulation --
// see src/hooks/useGameReplay.js for how a "turn" is just revealing the next
// pre-recorded event. Per attacker_overview_for_ui_team.pdf, RED is now the
// side that learns (Blue's 5 difficulty levels are fixed) -- same board,
// same log, just pointed at Red: bottom row is now
// controls | Red's win-rate history | the level ladder Red is climbing.
function App() {
  const { state, loading, isPlaying, speed, play, pause, step, setSpeed } = useGameReplay();
  const [hoveredNodeId, setHoveredNodeId] = useState(null);

  if (loading) {
    return (
      <div className="app-shell">
        <div className="panel" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
          Loading real game data...
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <TopBar state={state} />
      <ArenaHud state={state} isPlaying={isPlaying} />
      <div className="mid">
        <NetworkScene isPlaying={isPlaying} state={state} hoveredNodeId={hoveredNodeId} onHoverNode={setHoveredNodeId} />
        <LogPanel log={state.log} hoveredNodeId={hoveredNodeId} onHoverNode={setHoveredNodeId} />
      </div>
      <div className="bot">
        <BottomControls turn={state.turn} maxTurns={state.maxTurns} isPlaying={isPlaying} speed={speed} onPlay={play} onPause={pause} onStep={step} onSpeedChange={setSpeed} />
        <WinRateSparkline history={state.redWinRateHistory} gameNumber={state.gameNumber} />
        <LevelLadder currentLevel={state.level} />
      </div>
      <footer className="page-footer"><span>RED vs BLUE — Adversarial learning lab</span><span>Recorded simulation / MongoDB</span></footer>
      <ResultBanner result={state.result} reason={state.resultReason} />
    </div>
  );
}

export default App;
