"""Referee: plays games between an Env (Red + world) and Blue (via SimAdapter), writing
games + events to Atlas live.

    python -m backend.runner --level 1 --games 3 --blue random
    python -m backend.runner --level 1 --games 3 --blue llm --reflect
    python -m backend.runner --demo            # a few random-Blue games per level, purpose=demo
    python -m backend.runner --env stub ...    # plumbing test without backend/sim.py
"""
from __future__ import annotations

import argparse
import importlib
import random
from datetime import datetime, timezone

from langsmith import traceable

from backend import db, harness as blue, store
from backend.adapter import SimAdapter

MAX_TURNS = 20


def now():
    return datetime.now(timezone.utc)


def env_factory(name: str = "auto"):
    """'sim' -> Blue-learner env, 'sim_red' -> Red-learner env, 'stub' -> content-free,
    'auto' -> sim if present."""
    if name == "sim_red":
        return importlib.import_module("backend.sim_red").make_env
    if name in ("sim", "auto"):
        try:
            return importlib.import_module("backend.sim").make_env
        except ModuleNotFoundError as e:
            if name == "sim" or e.name != "backend.sim":
                raise
            print("backend/sim.py not found; using the content-free stub env")
    return importlib.import_module("backend.stub_env").make_env


def upsert_network(env) -> None:
    net = env.network
    db.networks().update_one({"_id": db.NETWORK_ID},
                             {"$set": {"nodes": net["nodes"], "edges": net["edges"]}}, upsert=True)


@traceable(name="play_game")
def play_game(level: int, seed: int, blue_mode: str = "random", harness: dict | None = None,
              memory_enabled: bool = True, purpose: str = "train", do_reflect: bool = False,
              make_env=None, verbose: bool = False, learner: str = "blue") -> dict:
    make_env = make_env or env_factory()
    harness = harness or store.current_version(learner)
    env = make_env(level, seed)
    upsert_network(env)
    adapter = SimAdapter(env)
    rng = random.Random(seed)

    game = {"_id": db.next_id("games"), "network_id": db.NETWORK_ID, "level": level,
            "harness_version": harness["version"], "memory_enabled": memory_enabled, "seed": seed,
            "purpose": purpose, "winner": None, "win_condition": None, "turns": 0,
            "time_to_detect": None, "time_to_evict": None, "max_nodes_red": 0,
            "false_alarms": 0, "collateral_nodes": 0, "lessons_written": 0,
            "tokens_in": 0, "tokens_out": 0, "started_at": now(), "ended_at": None}
    db.games().insert_one(game)
    events, history, sample_prompt = [], [], None
    base = {"game_id": game["_id"], "level": level}

    def write(ev: dict) -> None:
        ev["ts"] = now()
        db.events().insert_one(ev)
        ev.pop("_id", None)
        events.append(ev)
        if verbose:
            print(f"  T{ev['turn']:>2} {ev['side']:<4} {ev['text']}")

    # The learner is one side; the scripted opponent is the other.
    opponent = "blue" if learner == "red" else "red"
    opponent_step = getattr(env, "opponent_step", None) or env.red_step

    result, turn = None, 0
    for turn in range(1, MAX_TURNS + 1):
        adapter.turn = turn
        opp = opponent_step(turn)
        write({**base, "turn": turn, "side": opponent, "harness_version": None,
               "action": opp.get("action"), "category": opp.get("category", "attack"),
               "mitre": opp.get("mitre"), "from": opp.get("from"), "target": opp.get("target"),
               "success": bool(opp.get("success")), "detected": bool(opp.get("detected")),
               "signals_seen": [], "recalled": [], "reason": opp.get("reason"),
               "guardrail_blocked": None, "outcome": opp.get("outcome"),
               "text": opp.get("text", ""), "node_states": opp.get("node_states", {})})
        result = env.result(turn)
        if result:
            break

        if blue_mode == "llm":
            choice = blue.choose_action(adapter, harness, level, memory_enabled, history, side=learner)
        else:
            choice = blue.choose_random(adapter, rng)
        sample_prompt = choice.get("prompt") or sample_prompt
        game["tokens_in"] += choice["tokens_in"]
        game["tokens_out"] += choice["tokens_out"]
        res = adapter.act(choice["action"], choice["target"])
        history.append({"action": choice["action"], "target": choice["target"]})
        write({**base, "turn": turn, "side": learner, "harness_version": harness["version"],
               "action": choice["action"], "category": res.get("category"),
               "mitre": res.get("mitre"), "from": res.get("from"), "target": choice["target"],
               "success": bool(res.get("success")), "detected": res.get("detected"),
               "signals_seen": choice["signals_seen"],
               "recalled": choice["recalled"], "reason": choice["reason"],
               "guardrail_blocked": choice["guardrail_blocked"], "outcome": res.get("outcome"),
               "text": res.get("text", ""), "node_states": res.get("node_states", {})})
        result = env.result(turn)
        if result:
            break

    result = result or {"winner": "blue", "win_condition": "survived_20_turns"}
    game.update(winner=result["winner"], win_condition=result["win_condition"], turns=turn,
                ended_at=now(), **(env.metrics() if hasattr(env, "metrics") else {}))

    if do_reflect and blue_mode == "llm":
        from backend.reflect import reflect
        ids, usage = reflect(game, events, learner=learner)
        game["lessons_written"] = len(ids)
        game["tokens_in"] += usage["tokens_in"]
        game["tokens_out"] += usage["tokens_out"]

    db.games().update_one({"_id": game["_id"]}, {"$set": {k: v for k, v in game.items() if k != "_id"}})
    game["_sample_prompt"] = sample_prompt  # not stored; for CLI inspection
    return game


def seeds_for(level: int, n: int, offset: int = 0) -> list[int]:
    """Fixed seeds per level so parent and candidate harnesses face the same games."""
    return [1000 * level + offset + i for i in range(n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--blue", choices=["random", "llm"], default="random")
    ap.add_argument("--purpose", choices=["train", "eval", "demo"], default="train")
    ap.add_argument("--no-memory", action="store_true")
    ap.add_argument("--reflect", action="store_true")
    ap.add_argument("--seed-offset", type=int, default=500)
    ap.add_argument("--env", choices=["auto", "sim", "sim_red", "stub"], default="auto")
    ap.add_argument("--learner", choices=["blue", "red"], default="blue")
    ap.add_argument("--demo", action="store_true", help="seed random demo games at levels 1-5")
    ap.add_argument("--show-prompt", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    db.ensure_indexes()
    make_env = env_factory(a.env)
    runs = ([(lvl, 3, "random", "demo") for lvl in range(1, 6)] if a.demo
            else [(a.level, a.games, a.blue, a.purpose)])
    for level, n, mode, purpose in runs:
        wins = 0
        for seed in seeds_for(level, n, a.seed_offset):
            g = play_game(level, seed, mode, memory_enabled=not a.no_memory, purpose=purpose,
                          do_reflect=a.reflect, make_env=make_env, verbose=a.verbose,
                          learner=a.learner)
            wins += g["winner"] == a.learner
            print(f"{g['_id']} L{level} seed={seed} winner={g['winner']} ({g['win_condition']}) "
                  f"turns={g['turns']} tokens={g['tokens_in']}/{g['tokens_out']} "
                  f"lessons={g['lessons_written']}")
        print(f"level {level}: {a.learner} win rate {wins}/{n}")
        if a.show_prompt and g.get("_sample_prompt"):
            p = g["_sample_prompt"]
            print("\n--- SYSTEM ---\n" + p["system"] + "\n--- USER ---\n" + p["user"])


if __name__ == "__main__":
    main()
