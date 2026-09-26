"""Headless self-play trainer.

Runs many episodes of ScriptedRed vs. LearningBlue, tracks a rolling win rate,
and (optionally) persists episodes / metrics / policy snapshots to MongoDB
Atlas. Uses ONLY the standard library unless --atlas is passed.

    python train.py --episodes 5000            # zero deps, prints rising win rate
    python train.py --episodes 5000 --atlas    # also writes to Atlas
"""
from __future__ import annotations

import argparse
import random
from collections import deque

from engine.game import Game, GameConfig
from agents.red import ScriptedRed
from agents.blue import LearningBlue, RandomBlue


def moving_rate(window: deque) -> float:
    return sum(window) / len(window) if window else 0.0


def evaluate(blue, episodes=500, seed0=10_000_000) -> float:
    """Greedy evaluation (epsilon=0, no learning) to measure true skill."""
    was_training, blue.training = blue.training, False
    eps, blue.epsilon = blue.epsilon, 0.0
    wins = 0
    for i in range(episodes):
        g = Game(GameConfig(seed=seed0 + i))
        red = ScriptedRed(seed=seed0 + i)
        res = g.play(red, blue)
        wins += 1 if res.winner == "blue" else 0
    blue.training, blue.epsilon = was_training, eps
    return wins / episodes


def train(episodes: int, use_atlas: bool, quiet: bool = False):
    blue = LearningBlue(alpha=0.2, gamma=0.92, epsilon=0.3, seed=1)
    eps_start, eps_end = 0.3, 0.02
    window = deque(maxlen=200)
    curve = []  # (episode, rolling_win_rate)

    store = None
    if use_atlas:
        from persistence.store import AtlasStore
        store = AtlasStore()
        store.ensure_config()

    for ep in range(1, episodes + 1):
        # Anneal exploration from eps_start down to eps_end over training.
        blue.epsilon = eps_end + (eps_start - eps_end) * max(0.0, 1 - ep / (episodes * 0.8))
        seed = random.randint(0, 2**31)
        g = Game(GameConfig(seed=seed))
        red = ScriptedRed(seed=seed)
        result = g.play(red, blue)
        blue.learn(result)

        window.append(1 if result.winner == "blue" else 0)
        rate = moving_rate(window)

        if ep % 50 == 0:
            curve.append((ep, round(rate, 3)))
        if store:
            store.record_episode(ep, seed, g.snapshot(), result)
            if ep % 50 == 0:
                store.record_metric(ep, rate, blue.snapshot()["states"])
            if ep % 500 == 0:
                store.save_policy(ep, blue.snapshot())
        if not quiet and ep % max(1, episodes // 20) == 0:
            print(f"  ep {ep:>6}  rolling win rate {rate:6.1%}  "
                  f"(states learned: {len(blue.q)})")

    return blue, curve


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=5000)
    ap.add_argument("--atlas", action="store_true", help="persist to MongoDB Atlas")
    args = ap.parse_args()

    # Baseline: an untrained random defender, for the "before" number.
    print("Baseline (random defender):")
    base = RandomBlue(seed=7)
    base_wins = 0
    N = 1000
    for i in range(N):
        g = Game(GameConfig(seed=i))
        base_wins += 1 if g.play(ScriptedRed(seed=i), base).winner == "blue" else 0
    print(f"  random Blue win rate over {N} games: {base_wins / N:.1%}\n")

    print(f"Training LearningBlue for {args.episodes} episodes"
          f"{' (writing to Atlas)' if args.atlas else ''}:")
    blue, curve = train(args.episodes, args.atlas)

    print("\nGreedy evaluation of the trained policy:")
    skill = evaluate(blue, episodes=1000)
    print(f"  trained Blue win rate over 1000 games: {skill:.1%}")
    print(f"  learned states: {len(blue.q)}")


if __name__ == "__main__":
    main()
