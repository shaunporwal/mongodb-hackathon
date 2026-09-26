import { Pause, Play, SkipForward } from "@phosphor-icons/react";

const SPEEDS = [1, 10, 100];

export function BottomControls({ isPlaying, speed, onPlay, onPause, onStep, onSpeedChange }) {
  return (
    <div className="panel">
      <h3>03 / Playback</h3>
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
