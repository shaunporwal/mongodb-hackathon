"""Ablations for the UI charts, written as games with purpose="eval":
memory on vs. off (latest harness) and harness v0 vs. latest (memory on), per level.
The UI groups eval games by (level, harness_version, memory_enabled).

    python -m backend.compare --levels 1 2 3 4 5 --games 4
"""
import argparse

from backend import db, store
from backend.evolve import win_rate
from backend.runner import env_factory, seeds_for


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    ap.add_argument("--games", type=int, default=4)
    ap.add_argument("--env", choices=["auto", "sim", "stub"], default="auto")
    ap.add_argument("--learner", choices=["blue", "red"], default="blue")
    a = ap.parse_args()
    db.ensure_indexes()
    make_env = env_factory(a.env)
    v0, latest = store.seed_v0(a.learner), store.current_version(a.learner)
    arms = [("latest+memory", latest, True), ("latest-no-memory", latest, False)]
    if latest["version"] != 0:
        arms.append(("v0+memory", v0, True))

    print(f"learner={a.learner}  latest = v{latest['version']}")
    print("level  " + "  ".join(f"{name:>16}" for name, _, _ in arms))
    for level in a.levels:
        seeds = seeds_for(level, a.games, offset=800)
        rates = [win_rate(h, level, seeds, make_env, memory_enabled=m, learner=a.learner)
                 for _, h, m in arms]
        print(f"L{level:<5} " + "  ".join(f"{r:>16.2f}" for r in rates))


if __name__ == "__main__":
    main()
