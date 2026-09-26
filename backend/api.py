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
        from backend.board import VULNS
        shown = self.events[:self.cursor]
        board = shown[-1]["node_states"] if shown else {}
        # Which nodes has Red discovered the flaw on? (successful probe up to this point)
        discovered = {e["target"] for e in shown
                      if e.get("action") == "probe" and e.get("success")}
        exploited = {e["target"] for e in shown
                     if e.get("side") == "red" and e.get("success") and board.get(e["target"]) == "red"}
        nodes = [{"id": n["id"], "kind": n["type"], "crown": n["crown"],
                  "owner": "red" if board.get(n["id"]) == "red" else "blue",
                  "state": COLOR_TO_STATE.get(board.get(n["id"], "gray" if n["id"] == "internet" else "blue")),
                  "vuln": VULNS.get(n["id"]),
                  "flaw_discovered": n["id"] in discovered,
                  "exploited": n["id"] in exploited,
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


LEARNER = "red"  # this UI shows the RED attacker learning

# Background trainer: one evolve subprocess at a time. Fast defaults for quick iteration.
_train_proc = {"p": None, "started": None, "goal_generations": 0, "start_versions": 0}


@app.post("/api/train")
def train(generations: int = 3, eval_games: int = 3):
    """Kick off a Red evolve run in the background (non-blocking). Fast, low-fidelity by design."""
    import subprocess
    import sys
    from datetime import datetime, timezone
    p = _train_proc["p"]
    if p and p.poll() is None:
        return {**status(), "note": "already training"}
    _train_proc["p"] = subprocess.Popen(
        [sys.executable, "-m", "backend.evolve", "--env", "sim_red", "--learner", LEARNER,
         "--generations", str(generations), "--eval-games", str(eval_games), "--train-games", "1"],
        cwd=str(__import__("pathlib").Path(__file__).resolve().parent.parent),
    )
    _train_proc["started"] = datetime.now(timezone.utc).isoformat()
    _train_proc["goal_generations"] = generations
    _train_proc["start_versions"] = db.harness_versions().count_documents({"side": LEARNER})
    return {**status(), "note": f"started {generations} generations"}


@app.post("/api/train/stop")
def train_stop():
    """Stop the background training run."""
    p = _train_proc["p"]
    if p and p.poll() is None:
        p.terminate()
    return {**status(), "note": "stopped"}


def _training() -> bool:
    p = _train_proc["p"]
    return bool(p and p.poll() is None)


def _train_progress() -> dict:
    """How far the current/last run has gotten, so the UI never looks frozen."""
    done = db.harness_versions().count_documents({"side": LEARNER}) - _train_proc["start_versions"]
    return {"goal": _train_proc["goal_generations"], "done": max(0, done)}


@app.get("/api/curve")
def curve():
    """Red win rate per harness version (the improvement curve)."""
    gens = list(db.harness_versions().find({"side": LEARNER, "eval": {"$ne": None}},
                                           {"_id": 0, "version": 1, "eval": 1, "kept": 1,
                                            "diff_summary": 1}).sort("version", 1))
    if gens:
        best, pts = None, []
        for h in gens:
            if best is None:
                best = h["eval"].get("parent_win_rate")
                if best is None:
                    best = h["eval"]["win_rate"]
            if h["kept"]:
                best = h["eval"]["win_rate"]
            pts.append({"episode": h["version"], "win_rate": best, "level": h["eval"]["level"],
                        "kept": h["kept"], "diff_summary": h["diff_summary"]})
        return {"curve": pts, "x_label": "harness version"}
    games = list(db.games().find({"winner": {"$ne": None}}, {"winner": 1}).sort("started_at", 1))
    pts, wins = [], 0
    for i, g in enumerate(games, 1):
        wins += g["winner"] == LEARNER
        pts.append({"episode": i, "win_rate": wins / i})
    return {"curve": pts, "x_label": "games"}


@app.get("/api/status")
def status():
    recent = list(db.games().find({"winner": {"$ne": None}}, {"winner": 1})
                  .sort("started_at", -1).limit(20))
    cur = store.get_curriculum(LEARNER)
    return {"episode": db.games().count_documents({"winner": {"$ne": None}}),
            "win_rate": (sum(g["winner"] == LEARNER for g in recent) / len(recent)) if recent else 0,
            "states_learned": db.lessons().count_documents({"side": LEARNER}),
            "harness_version": store.current_version(LEARNER)["version"],
            "current_level": cur["current_level"],
            "generations": db.harness_versions().count_documents({"side": LEARNER, "eval": {"$ne": None}}),
            "learner": LEARNER, "training": _training(), "progress": _train_progress()}


@app.get("/api/config")
def config():
    """The board (nodes, positions, edges, colors) — single source of truth for the UI."""
    from backend import board
    return board.board()


@app.get("/api/harness")
def harness_by_parameter():
    """Per-parameter view of the learner's harness: current value of each of the 5
    evolvable fields, plus every mutation tried on it (kept or rolled back) with the
    eval result that decided it."""
    from backend.store import HARNESS_FIELDS
    versions = {h["version"]: h for h in db.harness_versions().find({"side": LEARNER}, {"_id": 0})}
    current = store.current_version(LEARNER)
    fields = {f: {"current": current.get(f), "tried": 0, "kept": 0, "history": []}
              for f in HARNESS_FIELDS}
    for v in sorted(versions):
        h, parent = versions[v], versions.get(versions[v].get("parent"))
        if not parent or not h.get("eval"):
            continue
        for f in HARNESS_FIELDS:
            if h.get(f) != parent.get(f):
                fields[f]["tried"] += 1
                fields[f]["kept"] += bool(h.get("kept"))
                fields[f]["history"].append({
                    "version": v, "kept": h.get("kept"), "before": parent.get(f), "after": h.get(f),
                    "summary": h.get("diff_summary"), "level": h["eval"]["level"],
                    "win_rate": h["eval"]["win_rate"], "parent_win_rate": h["eval"]["parent_win_rate"]})
    return {"learner": LEARNER, "current_version": current["version"],
            "lessons": db.lessons().count_documents({"side": LEARNER}),
            "fields": fields}


@app.get("/api/generations")
def generations():
    from backend.store import HARNESS_FIELDS
    gens = list(db.harness_versions().find(
        {"side": LEARNER, "eval": {"$ne": None}}).sort("version", -1).limit(20))
    parents = {h["version"]: h for h in db.harness_versions().find({"side": LEARNER})}
    out = []
    for h in gens:
        parent = parents.get(h.get("parent"))
        # Field-level diff: what actually changed from parent -> this version.
        changes = []
        if parent:
            for f in HARNESS_FIELDS:
                before, after = parent.get(f), h.get(f)
                if before != after:
                    changes.append({"field": f, "before": before, "after": after})
        ca = h.get("created_at")
        out.append({"version": h["version"], "parent": h.get("parent"),
                    "diff_summary": h.get("diff_summary"), "eval": h.get("eval"),
                    "kept": h.get("kept"), "level_unlocked": h.get("level_unlocked"),
                    "created_at": ca.isoformat() if hasattr(ca, "isoformat") else ca,
                    "changes": changes})
    return {"generations": out}


# ---- serve the frontend ----
from pathlib import Path  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
for sub in ("designs", "diagrams"):
    if (FRONTEND / sub).exists():
        app.mount(f"/{sub}", StaticFiles(directory=str(FRONTEND / sub)), name=sub)


@app.get("/")
def index():
    f = FRONTEND / "index.html"
    return FileResponse(str(f)) if f.exists() else {"ok": True, "note": "frontend/index.html missing"}
