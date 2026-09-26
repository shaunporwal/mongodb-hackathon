"""Recursive harnessing: each generation proposes ONE mutation to Blue's harness, evaluates it
against the current version on the same seeds, keeps it only if it wins more, and advances the
curriculum when the kept version clears the level.

    python -m backend.evolve --generations 10 --eval-games 6
"""
from __future__ import annotations

import argparse
import json
import os

from langsmith import traceable

from backend import db, llm, store
from backend.runner import env_factory, play_game, seeds_for

MAX_LEVEL = 5

SYSTEM = """You improve the HARNESS of BLUE, an LLM defender in a turn-based SIMULATED
network-defense game. A harness has these fields:
- playbook: str, the strategy text Blue reads every turn
- signals: list[str], signal types in priority order
- thresholds: {signal_type: float 0..1}, weaker scored signals are hidden from Blue
- memory_policy: {"k": int 0..8, "filter_by_level": bool, "recency_weight": float 0..1}
- guardrails: list[str]; machine-checked forms are "never <action> [<target>]" and
  "after <action_a> ..., also <action_b>" (next turn, same target); others are advisory.
Propose exactly ONE focused mutation to ONE field that should raise Blue's win rate,
based on the recent losses and lessons. Keep the playbook under 120 words.
Reply with JSON only:
{"field": "<field>", "new_value": <full new value for that field>,
 "diff_summary": "<one short plain-English sentence, e.g. 'After a credential alert: reset passwords, then isolate'>"}"""


def _context(level: int, learner: str = "blue") -> str:
    opponent = "blue" if learner == "red" else "red"  # a learner "loss" = the opponent won
    losses = list(db.games().find({"level": level, "winner": opponent},
                                  {"win_condition": 1, "turns": 1, "harness_version": 1})
                  .sort("started_at", -1).limit(5))
    loss_lines = []
    for g in losses:
        tail = list(db.events().find({"game_id": g["_id"]}, {"turn": 1, "side": 1, "text": 1})
                    .sort([("turn", -1), ("ts", -1)]).limit(6))
        steps = "; ".join(f"T{e['turn']} {e['side']}: {e['text']}" for e in reversed(tail))
        loss_lines.append(f"- {g['_id']} v{g['harness_version']} lost by {g['win_condition']} "
                          f"in {g['turns']} turns. Last moves: {steps}")
    lessons = [l["text"] for l in db.lessons().find({"level": level, "side": learner}, {"text": 1})
               .sort("created_at", -1).limit(8)]
    rejected = [h["diff_summary"] for h in db.harness_versions().find(
        {"kept": False, "eval.level": level, "side": learner}, {"diff_summary": 1})
        .sort("version", -1).limit(5)]
    return (f"LEVEL {level}\nRECENT LOSSES:\n" + ("\n".join(loss_lines) or "- none") +
            "\nLESSONS:\n" + ("\n".join(f"- {t}" for t in lessons) or "- none") +
            "\nALREADY TRIED AND REJECTED (don't repeat):\n" +
            ("\n".join(f"- {t}" for t in rejected) or "- none"))


def _valid(field: str, value, parent: dict):
    """Coerce/validate a proposed value; returns the cleaned value or raises ValueError."""
    if field not in store.HARNESS_FIELDS:
        raise ValueError(f"unknown field {field}")
    if field == "playbook":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("playbook must be non-empty text")
        return value.strip()
    if field in ("signals", "guardrails"):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError(f"{field} must be a list of strings")
        return value
    if field == "thresholds":
        return {str(k): min(1.0, max(0.0, float(v))) for k, v in dict(value).items()}
    mp = {**parent["memory_policy"], **dict(value)}
    return {"k": min(8, max(0, int(mp["k"]))), "filter_by_level": bool(mp["filter_by_level"]),
            "recency_weight": min(1.0, max(0.0, float(mp["recency_weight"])))}


@traceable(name="evolve_propose")
def propose(parent: dict, level: int, learner: str = "blue") -> tuple[dict, str]:
    current = {f: parent[f] for f in store.HARNESS_FIELDS}
    user = f"CURRENT HARNESS (v{parent['version']}):\n{json.dumps(current, indent=1)}\n\n{_context(level, learner)}"
    err = ""
    for _ in range(2):
        out, _usage = llm.chat_json(SYSTEM, user + err, kind="evolve", max_tokens=700, temperature=0.7)
        try:
            field = out["field"]
            return {field: _valid(field, out["new_value"], parent)}, str(out["diff_summary"])[:200]
        except (KeyError, ValueError, TypeError) as e:
            err = f"\n\nYour last proposal was invalid ({e}). Try again."
    raise RuntimeError("no valid mutation proposed")


# Which side the harness is optimizing for. Override with env LEARNER=red for the attacker demo.
LEARNER = os.environ.get("LEARNER", "blue")


def win_rate(harness: dict, level: int, seeds: list[int], make_env, memory_enabled=True,
             learner: str = LEARNER) -> float:
    """Fraction of games the learner's side wins."""
    wins = sum(play_game(level, s, "llm", harness=harness, memory_enabled=memory_enabled,
                         purpose="eval", make_env=make_env, learner=learner)["winner"] == learner
               for s in seeds)
    return wins / len(seeds)


@traceable(name="evolve_generation")
def generation(eval_games: int, train_games: int, make_env, learner: str = LEARNER) -> dict | None:
    cur = store.get_curriculum(learner)
    level = cur["current_level"]
    if level > MAX_LEVEL:
        print("curriculum complete: all levels cleared")
        return None
    parent = store.current_version(learner)

    # 1) train: play + reflect so memory and loss history grow
    for s in seeds_for(level, train_games, offset=100 + parent["version"] * 10):
        play_game(level, s, "llm", harness=parent, purpose="train", do_reflect=True,
                  make_env=make_env, learner=learner)

    # 2) propose one mutation
    changes, summary = propose(parent, level, learner)
    child = store.save_candidate(parent, changes, summary)

    # 3) evaluate both on the same fixed seeds
    seeds = seeds_for(level, eval_games)
    parent_wr = win_rate(parent, level, seeds, make_env, learner=learner)
    child_wr = win_rate(child, level, seeds, make_env, learner=learner)
    kept = child_wr > parent_wr
    store.record_eval(child["version"], level, eval_games, child_wr, parent_wr, kept, side=learner)

    # 4) curriculum: the surviving version's score decides if the level is cleared
    best_version, best_wr = (child["version"], child_wr) if kept else (parent["version"], parent_wr)
    cur_after = store.maybe_advance(best_wr, best_version, MAX_LEVEL, side=learner)
    print(f"v{child['version']} (parent v{parent['version']}) L{level}: "
          f"{'KEPT' if kept else 'rolled back'}  win {child_wr:.2f} vs {parent_wr:.2f}  "
          f"| {summary}" + (f"  >> level {cur_after['current_level']} unlocked"
                            if cur_after["current_level"] > level else ""))
    return {"version": child["version"], "kept": kept, "level": level,
            "win_rate": child_wr, "parent_win_rate": parent_wr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=10)
    ap.add_argument("--eval-games", type=int, default=6)
    ap.add_argument("--train-games", type=int, default=2)
    ap.add_argument("--env", choices=["auto", "sim", "sim_red", "stub"], default="auto")
    ap.add_argument("--learner", choices=["blue", "red"], default=LEARNER)
    a = ap.parse_args()
    db.ensure_indexes()
    make_env = env_factory(a.env)
    store.seed_v0(a.learner)
    for _ in range(a.generations):
        if generation(a.eval_games, a.train_games, make_env, learner=a.learner) is None:
            break


if __name__ == "__main__":
    main()
