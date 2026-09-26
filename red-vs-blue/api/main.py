"""FastAPI backend for the Red vs. Blue arena.

Endpoints
---------
GET  /api/health          liveness + Atlas connectivity
GET  /api/state           current live-game snapshot (map + log)
POST /api/live/new        start a fresh live game
POST /api/live/step       advance the live game one turn
POST /api/train?n=200     run N self-play episodes (Blue learns)
GET  /api/curve           win-rate-over-episodes series (the "wow" chart)
GET  /api/status          episode count, current win rate, states learned

The live game plays Blue's *current* learned policy greedily, so as you train,
the same board visibly gets harder for Red to win.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .arena import Arena

app = FastAPI(title="Red vs. Blue Arena")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Atlas if configured; otherwise run in-memory (still fully playable).
_store = None
if os.environ.get("MONGODB_URI"):
    try:
        from persistence.store import AtlasStore
        _store = AtlasStore()
        _store.create_indexes()
        _store.ensure_config()
    except Exception as e:  # pragma: no cover
        print(f"[warn] Atlas unavailable, running in-memory: {e}")

arena = Arena(store=_store)


@app.get("/api/health")
def health():
    atlas_ok = False
    if _store:
        try:
            atlas_ok = _store.ping()
        except Exception:
            atlas_ok = False
    return {"ok": True, "atlas_connected": atlas_ok}


@app.get("/api/state")
def state():
    return arena.live_snapshot()


@app.post("/api/live/new")
def live_new():
    return arena.new_live_game()


@app.post("/api/live/step")
def live_step():
    return arena.step_live()


@app.post("/api/train")
def train(n: int = 200):
    return arena.train_batch(n)


@app.get("/api/curve")
def curve():
    return {"curve": arena.curve}


@app.get("/api/status")
def status():
    return arena.status()
