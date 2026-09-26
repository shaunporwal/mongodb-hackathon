import { useEffect, useRef, useState } from "react";
import { loadGameData } from "../lib/loadGameData";
import { NODE_STATE_TO_STATUS, NODES } from "../data/network";

const BASE_INTERVAL_MS = 900; // roughly one event/second at 1x
const NEXT_GAME_DELAY_MS = 1800;

const WIN_CONDITION_TEXT = {
  crown_jewel_stolen: "Red captured the crown jewel (Database).",
  red_evicted: "Blue evicted Red from every node.",
  half_network_taken: "Red took over half the network.",
  survived_20_turns: "Blue survived to the end without losing the database.",
};

function safeNodeStatus() {
  const status = {};
  NODES.forEach((n) => {
    status[n.id] = "safe";
  });
  return status;
}

function statusFromNodeStates(nodeStates) {
  if (!nodeStates) return safeNodeStatus();
  const status = {};
  NODES.forEach((n) => {
    status[n.id] = NODE_STATE_TO_STATUS[nodeStates[n.id]] ?? "safe";
  });
  return status;
}

// Drives the whole UI from *real* recorded games (public/data/*.csv) instead
// of a scripted simulation -- this is a replay, not a live sim, so "playing"
// just means revealing pre-recorded events one at a time. When a game runs
// out of recorded events, it loops to the next replayable game_id (currently
// just g_0042 has full per-turn events; more games get added to events.csv
// as the real backend exports them, and this picks them up automatically).
export function useGameReplay() {
  const [data, setData] = useState(null);
  const [gameCursor, setGameCursor] = useState(0);
  const [eventIndex, setEventIndex] = useState(0);
  const [genIndex, setGenIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const nextGameTimerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    loadGameData().then((loaded) => {
      if (!cancelled) setData(loaded);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const gameIds = data?.replayableGameIds ?? [];
  const currentGameId = gameIds.length ? gameIds[gameCursor % gameIds.length] : null;
  const currentEvents = currentGameId ? data.eventsByGame[currentGameId] : [];
  const currentGame = currentGameId ? data.games.find((g) => g.game_id === currentGameId) : null;
  const isGameOver = Boolean(data) && currentEvents.length > 0 && eventIndex >= currentEvents.length;

  const advance = () => setEventIndex((i) => Math.min(currentEvents.length, i + 1));

  useEffect(() => {
    if (!isPlaying || !data || isGameOver || currentEvents.length === 0) return undefined;
    const interval = Math.max(8, BASE_INTERVAL_MS / speed);
    const id = setInterval(advance, interval);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, speed, data, isGameOver, currentGameId]);

  useEffect(() => {
    if (!isGameOver) return undefined;
    nextGameTimerRef.current = setTimeout(() => {
      setGameCursor((i) => i + 1);
      setEventIndex(0);
      setGenIndex((i) => (data && i + 1 < data.generations.length ? i + 1 : 0));
    }, NEXT_GAME_DELAY_MS / Math.max(1, Math.min(speed, 10)));
    return () => clearTimeout(nextGameTimerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isGameOver]);

  if (!data || !currentGameId) {
    return {
      loading: true,
      state: null,
      isPlaying,
      speed,
      play: () => setIsPlaying(true),
      pause: () => setIsPlaying(false),
      step: () => {},
      setSpeed,
    };
  }

  const revealed = currentEvents.slice(0, eventIndex);
  const upcoming = currentEvents.slice(eventIndex);
  const lastEvent = revealed.at(-1) ?? null;
  const nextRed = upcoming.find((e) => e.side === "red");

  // Red is the side that learns now (see attacker_overview_for_ui_team.pdf) --
  // a recalled lesson gets its own "MEM" log line instead of being buried in
  // the acting row's detail text, matching the brief's sketch. The real data
  // still records recalls on whichever row triggered them (currently Blue's,
  // since lessons.csv predates the reframe); we surface that field honestly
  // rather than reattributing it to Red.
  const log = [];
  revealed.forEach((e) => {
    const hasMemNote = e.recalled_lessons.length > 0 && Boolean(e.reason);
    log.push({
      id: `${e.game_id}-${e.turn}-${e.side}-${e.action}`,
      turn: e.turn,
      side: e.side.toUpperCase(),
      action: e.action,
      text: e.text,
      nodeId: e.target || e.from || null,
      detail: e.guardrail_blocked || (!hasMemNote ? e.reason : null) || e.outcome || null,
    });
    if (hasMemNote) {
      log.push({
        id: `${e.game_id}-${e.turn}-${e.side}-${e.action}-mem`,
        turn: e.turn,
        side: "MEM",
        recalledBy: e.side.toUpperCase(),
        action: null,
        text: `Recalled: ${e.reason}`,
        nodeId: e.target || e.from || null,
        detail: null,
      });
    }
  });
  log.reverse();

  // generations.csv tracks the defender's playbook improving generation over
  // generation (win_rate = Blue's win rate). Red's win rate is just the
  // complement of that in this zero-sum game -- the headline "getting
  // smarter" metric now points at Red per the updated brief.
  const blueWinRateHistory = data.generations.slice(0, genIndex + 1).map((g) => Math.round((g.win_rate ?? 0) * 100));
  const redWinRateHistory = blueWinRateHistory.map((v) => 100 - v);

  const state = {
    gameId: currentGameId,
    gameNumber: Number(currentGameId.replace(/\D/g, "")) || gameCursor + 1,
    level: currentGame?.level,
    turn: lastEvent?.turn ?? 0,
    maxTurns: currentGame?.turns ?? currentEvents.at(-1)?.turn ?? 0,
    nodeStatus: statusFromNodeStates(lastEvent?.node_states),
    currentEvent: lastEvent,
    log,
    lastAttackTarget: lastEvent?.side === "red" ? lastEvent.target : null,
    lastBlueTarget: lastEvent?.side === "blue" ? lastEvent.target : null,
    nextRedPreview: nextRed ? { text: nextRed.text, target: nextRed.target } : null,
    result: isGameOver ? (currentGame?.winner === "blue" ? "blue_win" : "red_win") : null,
    resultReason: isGameOver ? WIN_CONDITION_TEXT[currentGame?.win_condition] ?? currentGame?.win_condition : "",
    blueWinRateHistory,
    redWinRateHistory,
  };

  return {
    loading: false,
    state,
    isPlaying,
    speed,
    play: () => setIsPlaying(true),
    pause: () => setIsPlaying(false),
    step: () => {
      setIsPlaying(false);
      advance();
    },
    setSpeed,
  };
}
