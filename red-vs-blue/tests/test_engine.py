"""Sanity tests for the engine + learning loop. Pure stdlib (uses assert)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.game import Game, GameConfig
from engine.state import Owner
from agents.red import ScriptedRed
from agents.blue import LearningBlue, RandomBlue


def test_game_always_terminates():
    for seed in range(200):
        g = Game(GameConfig(seed=seed))
        res = g.play(ScriptedRed(seed), RandomBlue(seed))
        assert res.winner in ("red", "blue")
        assert g.turn <= 20
        assert res is g.result


def test_snapshot_shape():
    g = Game(GameConfig(seed=1))
    g.play(ScriptedRed(1), RandomBlue(1))
    s = g.snapshot()
    assert set(["turn", "finished", "nodes", "edges", "blocked", "log", "result"]) <= set(s)
    for n in s["nodes"]:
        assert n["state"] in ("safe", "under_attack", "taken", "offline")


def test_partial_observability():
    # A freshly compromised node is hidden (amber) until Blue scans it.
    g = Game(GameConfig(seed=5))
    lap = g.net.nodes["laptop_a"]
    lap.owner = Owner.RED
    lap.under_attack = True
    assert lap.compromise_known is False
    assert lap.ui_state().value == "under_attack"  # hidden
    lap.compromise_known = True
    assert lap.ui_state().value == "taken"          # revealed


def test_blue_learns():
    # Trained Blue should clearly beat a random Blue against the same Red.
    blue = LearningBlue(gamma=0.92, epsilon=0.3, seed=1)
    import random
    N = 20000
    for ep in range(1, N + 1):
        # Anneal exploration, matching train.py's schedule.
        blue.epsilon = 0.02 + (0.3 - 0.02) * max(0.0, 1 - ep / (N * 0.8))
        seed = random.randint(0, 2**31)
        g = Game(GameConfig(seed=seed))
        res = g.play(ScriptedRed(seed), blue)
        blue.learn(res)
    # greedy eval
    blue.training = False; blue.epsilon = 0.0
    wins = sum(
        1 for i in range(1000)
        if Game(GameConfig(seed=10_000_000 + i)).play(
            ScriptedRed(10_000_000 + i), blue).winner == "blue"
    )
    rate = wins / 1000
    assert rate > 0.85, f"trained Blue win rate too low: {rate}"


if __name__ == "__main__":
    test_game_always_terminates(); print("ok: termination")
    test_snapshot_shape(); print("ok: snapshot shape")
    test_partial_observability(); print("ok: partial observability")
    test_blue_learns(); print("ok: blue learns")
    print("ALL TESTS PASSED")
