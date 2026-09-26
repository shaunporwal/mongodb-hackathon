import { Pause, Play, SkipForward } from "@phosphor-icons/react";

const SPEEDS = [1, 10, 100];

export function BottomControls({ turn, maxTurns, isPlaying, speed, onPlay, onPause, onStep, onSpeedChange }) {
  return (
    <div className="panel">
      <h3>03 / Replay controls</h3>
      <div className="turn-progress"><span>Turn <strong>{turn}</strong> / {maxTurns}</span><div className="turn-track">{Array.from({ length: maxTurns || 1 }, (_, i) => <i key={i} className={i < turn ? "complete" : ""} />)}</div></div>
      <div className="control-row">
      <button type="button" className={`btn${isPlaying ? " on" : ""}`} onClick={onPlay}><Play size={13} weight="fill" /> Play</button>
      <button type="button" className={`btn${!isPlaying ? " on" : ""}`} aria-label="Pause replay" onClick={onPause}><Pause size={13} weight="fill" /></button>
      <button type="button" className="btn" onClick={onStep}><SkipForward size={13} weight="fill" /> Step</button>
      </div>
      <div className="speed-row"><span>Speed</span>
      {SPEEDS.map((s) => (
        <button key={s} type="button" aria-pressed={speed === s} className={`btn${speed === s ? " on" : ""}`} onClick={() => onSpeedChange(s)}>
          {s}x
        </button>
      ))}</div>
    </div>
  );
}
