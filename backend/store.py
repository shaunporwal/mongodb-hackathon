"""Loaders/savers for harness_versions and curriculum (shapes per CLAUDE.md data contract).

Blue and Red learners keep separate lineages in the same collections, tagged by `side`.
"""
from datetime import datetime, timezone

from pymongo import DESCENDING

from backend import db
from backend.prompts import PLAYBOOK_V0_FOR

HARNESS_FIELDS = ("playbook", "signals", "thresholds", "memory_policy", "guardrails")


def v0_for(side: str = "blue") -> dict:
    """Seed harness v0 for a learner side. Red's playbook text comes from prompts.py."""
    return {
        "version": 0,
        "side": side,
        "parent": None,
        "playbook": PLAYBOOK_V0_FOR.get(side, ""),
        "signals": ["alert", "login_anomaly", "egress", "sched_task"],
        "thresholds": {"alert": 0.5, "login_anomaly": 0.5, "egress": 0.5, "sched_task": 0.5},
        "memory_policy": {"k": 3, "filter_by_level": True, "recency_weight": 0.0},
        "guardrails": ["never isolate database"] if side == "blue" else [],
        "diff_summary": "seed: generic playbook",
        "eval": None,
        "kept": True,
        "level_unlocked": None,
    }


def now():
    return datetime.now(timezone.utc)


def seed_v0(side: str = "blue") -> dict:
    """Insert this side's harness version 0 if missing. Returns it."""
    db.harness_versions().update_one({"version": 0, "side": side},
                                     {"$setOnInsert": {**v0_for(side), "created_at": now()}},
                                     upsert=True)
    return get_version(0, side)


def get_version(version: int, side: str = "blue") -> dict | None:
    return db.harness_versions().find_one({"version": version, "side": side}, {"_id": 0})


def current_version(side: str = "blue") -> dict:
    """Latest kept version for this side (seeds v0 if none)."""
    doc = db.harness_versions().find_one({"kept": True, "side": side}, {"_id": 0},
                                         sort=[("version", DESCENDING)])
    return doc or seed_v0(side)


def next_version_number(side: str = "blue") -> int:
    doc = db.harness_versions().find_one({"side": side}, {"version": 1}, sort=[("version", DESCENDING)])
    return (doc["version"] + 1) if doc else 0


def save_candidate(parent: dict, changes: dict, diff_summary: str) -> dict:
    """Write a new (not yet kept) version = parent with `changes` applied to harness fields."""
    side = parent.get("side", "blue")
    doc = {f: changes.get(f, parent[f]) for f in HARNESS_FIELDS}
    doc.update(version=next_version_number(side), side=side, parent=parent["version"],
               diff_summary=diff_summary, eval=None, kept=False, level_unlocked=None,
               created_at=now())
    db.harness_versions().insert_one(doc)
    doc.pop("_id", None)
    return doc


def record_eval(version: int, level: int, games: int, win_rate: float,
                parent_win_rate: float, kept: bool, side: str = "blue") -> None:
    db.harness_versions().update_one({"version": version, "side": side}, {"$set": {
        "eval": {"level": level, "games": games, "win_rate": win_rate,
                 "parent_win_rate": parent_win_rate},
        "kept": kept,
    }})


def get_curriculum(side: str = "blue") -> dict:
    db.curriculum().update_one(
        {"_id": side},
        {"$setOnInsert": {"current_level": 1, "pass_threshold": 0.7, "history": []}},
        upsert=True,
    )
    return db.curriculum().find_one({"_id": side})


def maybe_advance(win_rate: float, version: int, max_level: int = 5, side: str = "blue") -> dict:
    """If win_rate clears the threshold at the current level, unlock the next one
    and stamp level_unlocked on that harness version."""
    cur = get_curriculum(side)
    if win_rate >= cur["pass_threshold"] and cur["current_level"] <= max_level:
        if cur["current_level"] < max_level:
            db.harness_versions().update_one({"version": version, "side": side},
                                             {"$set": {"level_unlocked": cur["current_level"] + 1}})
        entry = {"level": cur["current_level"], "cleared_at_version": version, "cleared_at": now()}
        db.curriculum().update_one({"_id": side}, {
            "$push": {"history": entry},
            "$set": {"current_level": min(cur["current_level"] + 1, max_level + 1)},
        })
    return get_curriculum(side)


if __name__ == "__main__":
    print("current harness:", current_version()["version"])
    print("curriculum:", {k: v for k, v in get_curriculum().items() if k != "history"})
