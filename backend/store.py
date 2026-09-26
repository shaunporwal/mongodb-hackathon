"""Loaders/savers for harness_versions and curriculum (shapes per CLAUDE.md data contract)."""
from datetime import datetime, timezone

from pymongo import DESCENDING

from backend import db

HARNESS_FIELDS = ("playbook", "signals", "thresholds", "memory_policy", "guardrails")

V0 = {
    "version": 0,
    "parent": None,
    "playbook": (
        "Look at the strongest signals first. Investigate before responding: confirm a "
        "suspicion with a detect action, then respond on that node. Harden nodes on the "
        "path to the database early. Protect the database above everything else."
    ),
    "signals": ["alert", "login_anomaly", "egress", "sched_task"],
    "thresholds": {"alert": 0.5, "login_anomaly": 0.5, "egress": 0.5, "sched_task": 0.5},
    "memory_policy": {"k": 3, "filter_by_level": True, "recency_weight": 0.0},
    "guardrails": ["never isolate database"],
    "diff_summary": "seed: generic playbook",
    "eval": None,
    "kept": True,
    "level_unlocked": None,
}


def now():
    return datetime.now(timezone.utc)


def seed_v0() -> dict:
    """Insert harness version 0 if missing. Returns it."""
    db.harness_versions().update_one({"version": 0}, {"$setOnInsert": {**V0, "created_at": now()}},
                                     upsert=True)
    return get_version(0)


def get_version(version: int) -> dict | None:
    return db.harness_versions().find_one({"version": version}, {"_id": 0})


def current_version() -> dict:
    """Latest kept version (seeds v0 on an empty DB)."""
    doc = db.harness_versions().find_one({"kept": True}, {"_id": 0}, sort=[("version", DESCENDING)])
    return doc or seed_v0()


def next_version_number() -> int:
    doc = db.harness_versions().find_one({}, {"version": 1}, sort=[("version", DESCENDING)])
    return (doc["version"] + 1) if doc else 0


def save_candidate(parent: dict, changes: dict, diff_summary: str) -> dict:
    """Write a new (not yet kept) version = parent with `changes` applied to harness fields."""
    doc = {f: changes.get(f, parent[f]) for f in HARNESS_FIELDS}
    doc.update(version=next_version_number(), parent=parent["version"],
               diff_summary=diff_summary, eval=None, kept=False, level_unlocked=None,
               created_at=now())
    db.harness_versions().insert_one(doc)
    doc.pop("_id", None)
    return doc


def record_eval(version: int, level: int, games: int, win_rate: float,
                parent_win_rate: float, kept: bool) -> None:
    db.harness_versions().update_one({"version": version}, {"$set": {
        "eval": {"level": level, "games": games, "win_rate": win_rate,
                 "parent_win_rate": parent_win_rate},
        "kept": kept,
    }})


def get_curriculum() -> dict:
    db.curriculum().update_one(
        {"_id": "blue"},
        {"$setOnInsert": {"current_level": 1, "pass_threshold": 0.7, "history": []}},
        upsert=True,
    )
    return db.curriculum().find_one({"_id": "blue"})


def maybe_advance(win_rate: float, version: int, max_level: int = 5) -> dict:
    """If win_rate clears the threshold at the current level, unlock the next one
    and stamp level_unlocked on that harness version."""
    cur = get_curriculum()
    if win_rate >= cur["pass_threshold"] and cur["current_level"] <= max_level:
        if cur["current_level"] < max_level:
            db.harness_versions().update_one({"version": version},
                                             {"$set": {"level_unlocked": cur["current_level"] + 1}})
        entry = {"level": cur["current_level"], "cleared_at_version": version, "cleared_at": now()}
        db.curriculum().update_one({"_id": "blue"}, {
            "$push": {"history": entry},
            "$set": {"current_level": min(cur["current_level"] + 1, max_level + 1)},
        })
    return get_curriculum()


if __name__ == "__main__":
    print("current harness:", current_version()["version"])
    print("curriculum:", {k: v for k, v in get_curriculum().items() if k != "history"})
