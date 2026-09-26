"""MongoDB Atlas store — the harness memory for Red vs. Blue.

Collections
-----------
episodes         one document per game: seed, final snapshot, result, timestamp
metrics          rolling win rate sampled during training (drives the live chart)
policy_snapshots versioned Blue Q-table over time (the learned artifact)
configs          network topology + rules (so the harness can evolve its rules)

The rest of the codebase never imports pymongo directly; it goes through this
class. If MONGODB_URI is unset we fail loudly with a helpful message, because
Atlas is a required core component for the hackathon.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional


def _load_env() -> None:
    # Lightweight .env loader so we don't hard-depend on python-dotenv.
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
        return
    except Exception:
        pass
    path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class AtlasStore:
    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        _load_env()
        self.uri = uri or os.environ.get("MONGODB_URI")
        self.db_name = db_name or os.environ.get("MONGODB_DB", "redblue")
        if not self.uri:
            raise RuntimeError(
                "MONGODB_URI is not set. Copy .env.example to .env and paste your "
                "Atlas connection string (Atlas > Connect > Drivers > Python)."
            )
        try:
            from pymongo import MongoClient  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "pymongo is not installed. Run: pip install -r requirements.txt"
            ) from e

        self.client = MongoClient(self.uri, appname="red-vs-blue")
        self.db = self.client[self.db_name]
        self.episodes = self.db["episodes"]
        self.metrics = self.db["metrics"]
        self.policies = self.db["policy_snapshots"]
        self.configs = self.db["configs"]
        # Identify a training run so multiple runs don't collide on charts.
        self.run_id = time.strftime("run-%Y%m%d-%H%M%S")

    # ---- setup ------------------------------------------------------------

    def create_indexes(self) -> None:
        self.episodes.create_index([("run_id", 1), ("episode", 1)])
        self.episodes.create_index([("result.winner", 1)])
        self.metrics.create_index([("run_id", 1), ("episode", 1)])
        self.policies.create_index([("run_id", 1), ("episode", 1)])
        self.configs.create_index([("name", 1)], unique=True)

    def ensure_config(self) -> None:
        from engine.topology import default_config
        cfg = default_config()
        self.configs.update_one({"name": cfg["name"]}, {"$set": cfg}, upsert=True)

    # ---- writes -----------------------------------------------------------

    def record_episode(self, episode: int, seed: int, snapshot: dict, result) -> None:
        self.episodes.insert_one({
            "run_id": self.run_id,
            "episode": episode,
            "seed": seed,
            "result": vars(result),
            "final": snapshot,
            "ts": time.time(),
        })

    def record_metric(self, episode: int, win_rate: float, states: int) -> None:
        self.metrics.insert_one({
            "run_id": self.run_id,
            "episode": episode,
            "win_rate": win_rate,
            "states": states,
            "ts": time.time(),
        })

    def save_policy(self, episode: int, snapshot: dict) -> None:
        self.policies.insert_one({
            "run_id": self.run_id,
            "episode": episode,
            "policy": snapshot,
            "ts": time.time(),
        })

    # ---- reads (used by the API) -----------------------------------------

    def latest_policy(self) -> Optional[dict]:
        doc = self.policies.find_one(sort=[("ts", -1)])
        return doc["policy"] if doc else None

    def win_rate_curve(self, run_id: Optional[str] = None, limit: int = 2000) -> list[dict]:
        q: dict[str, Any] = {}
        if run_id:
            q["run_id"] = run_id
        cur = self.metrics.find(q, {"_id": 0, "episode": 1, "win_rate": 1}) \
            .sort("episode", 1).limit(limit)
        return list(cur)

    def recent_episodes(self, limit: int = 20) -> list[dict]:
        cur = self.episodes.find({}, {"_id": 0, "episode": 1, "result": 1}) \
            .sort("ts", -1).limit(limit)
        return list(cur)

    def stats(self) -> dict:
        return {
            "episodes": self.episodes.estimated_document_count(),
            "metrics": self.metrics.estimated_document_count(),
            "policies": self.policies.estimated_document_count(),
        }

    def ping(self) -> bool:
        self.client.admin.command("ping")
        return True
