"""FastAPI backend for web/ (the teammate's React UI, adapted). Read-only over our Atlas data.

"Live" games are replays of real games stored in Atlas, one event per step, so anything run
from the CLI (runner / evolve / compare) shows up here. Same endpoint shapes as
red-vs-blue/api so the UI components work unchanged.

    .venv/bin/uvicorn backend.api:app --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import db, store

app = FastAPI(title="Red vs. Blue harness")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

COLOR_TO_STATE = {"blue": "safe", "amber": "under_attack", "red": "taken", "gray": "offline"}
WIN_TEXT = {
    "crown_jewel_stolen": "Red stole the crown jewel",
    "half_network_taken": "Red controls most of the network",
    "survived_20_turns": "Blue survived all 20 turns",
    "red_evicted": "Blue evicted Red from the network",
}


class Replay:
    def __init__(self):
        self.shown: list[str] = []
        self.game: dict | None = None
        self.events: list[dict] = []
        self.cursor = 0

    def load_next(self) -> None:
        """Newest finished game not shown yet (cycles back to newest when exhausted)."""
        q = {"winner": {"$ne": None}}
        g = db.games().find_one({**q, "_id": {"$nin": self.shown}}, sort=[("started_at", -1)])
        if g is None:
            self.shown = []
            g = db.games().find_one(q, sort=[("started_at", -1)])
        self.game, self.cursor = g, 0
        self.events = list(db.events().find({"game_id": g["_id"]}, {"_id": 0})
                           .sort([("turn", 1), ("ts", 1)])) if g else []
        if g:
            self.shown.append(g["_id"])

    def snapshot(self) -> dict:
        net = db.networks().find_one({"_id": db.NETWORK_ID}) or {"nodes": [], "edges": []}
        shown = self.events[:self.cursor]
        board = shown[-1]["node_states"] if shown else {}
        nodes = [{"id": n["id"], "kind": n["type"], "crown": n["crown"],
                  "owner": "red" if board.get(n["id"]) == "red" else "blue",
                  "state": COLOR_TO_STATE.get(board.get(n["id"], "gray" if n["id"] == "internet" else "blue")),
                  "patched": False, "known": False} for n in net["nodes"]]
        log = [{"turn": e["turn"], "side": e["side"], "action": e["action"], "text": e["text"],
                "target": e["target"], "source": e.get("from"), "success": e["success"],
                "detected": e.get("detected"), "reason": e.get("reason"),
                "recalled": e.get("recalled") or [], "guardrail_blocked": e.get("guardrail_blocked")}
               for e in shown]
        g = self.game or {}
        finished = bool(self.events) and self.cursor >= len(self.events)
        result = None
        if finished:
            reason = WIN_TEXT.get(g.get("win_condition"), g.get("win_condition"))
            result = {"winner": g["winner"], "turns": g["turns"], "reason": reason,
                      "red_nodes_held": g.get("max_nodes_red")}
            log.append({"turn": g["turns"], "side": "result", "action": None,
                        "text": f"{g['winner'].upper()} wins: {reason}.", "target": None,
                        "source": None, "success": True})
        return {"turn": shown[-1]["turn"] if shown else 0, "finished": finished,
                "nodes": nodes, "edges": net["edges"], "blocked": [], "log": log, "result": result,
                "game": {k: g.get(k) for k in ("_id", "level", "harness_version", "memory_enabled",
                                                "purpose", "seed")}}

    def step(self) -> dict:
        if self.game is None or self.cursor >= len(self.events):
            self.load_next()
        else:
            self.cursor += 1
        return self.snapshot()


replay = Replay()


@app.get("/api/health")
def health():
    try:
        return {"ok": True, "atlas_connected": db.ping()}
    except Exception:
        return {"ok": True, "atlas_connected": False}


@app.get("/api/state")
def state():
    if replay.game is None:
        replay.load_next()
    return replay.snapshot()


@app.post("/api/live/new")
def live_new():
    replay.load_next()
    return replay.snapshot()


@app.post("/api/live/step")
def live_step():
    return replay.step()


@app.post("/api/train")
def train(n: int = 0):
    # Training runs from the CLI (python -m backend.evolve); the UI only watches.
    return status()


@app.get("/api/curve")
def curve():
    """Win rate per harness version (evolution), else rolling win rate over games."""
    gens = list(db.harness_versions().find({"eval": {"$ne": None}}, {"_id": 0, "version": 1,
                                                                      "eval": 1, "kept": 1,
                                                                      "diff_summary": 1})
                .sort("version", 1))
    if gens:
        best, pts = None, []
        for h in gens:
            if best is None:
                best = h["eval"]["parent_win_rate"]
            if h["kept"]:
                best = h["eval"]["win_rate"]
            pts.append({"episode": h["version"], "win_rate": best, "level": h["eval"]["level"],
                        "kept": h["kept"], "diff_summary": h["diff_summary"]})
        return {"curve": pts, "x_label": "harness version"}
    games = list(db.games().find({"winner": {"$ne": None}}, {"winner": 1}).sort("started_at", 1))
    pts, wins = [], 0
    for i, g in enumerate(games, 1):
        wins += g["winner"] == "blue"
        pts.append({"episode": i, "win_rate": wins / i})
    return {"curve": pts, "x_label": "games"}


@app.get("/api/status")
def status():
    recent = list(db.games().find({"winner": {"$ne": None}}, {"winner": 1})
                  .sort("started_at", -1).limit(20))
    cur = store.get_curriculum()
    return {"episode": db.games().count_documents({"winner": {"$ne": None}}),
            "win_rate": (sum(g["winner"] == "blue" for g in recent) / len(recent)) if recent else 0,
            "states_learned": db.lessons().count_documents({}),
            "harness_version": store.current_version()["version"],
            "current_level": cur["current_level"],
            "generations": db.harness_versions().count_documents({"eval": {"$ne": None}})}


@app.get("/api/generations")
def generations():
    return {"generations": list(db.harness_versions().find(
        {"eval": {"$ne": None}}, {"_id": 0, "version": 1, "parent": 1, "diff_summary": 1,
                                 "eval": 1, "kept": 1, "level_unlocked": 1}).sort("version", -1).limit(20))}
