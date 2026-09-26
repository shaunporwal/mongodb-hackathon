"""Arena: orchestrates live games and background self-play for the API.

Pure stdlib so it is fully unit-testable in any environment (including this
sandbox). The FastAPI layer in main.py is a thin wrapper over this class.

- A single "live" game can be stepped turn-by-turn for the 1x viewer.
- `train_batch` advances self-play in chunks so the win-rate chart moves while
  the server keeps responding.
- Blue's learned policy is shared between training and the live game, so the
  live game visibly reflects whatever Blue has learned so far.
"""
from __future__ import annotations

import random
from collections import deque
from typing import Optional

from engine.game import Game, GameConfig
from agents.red import ScriptedRed
from agents.blue import LearningBlue


class Arena:
    def __init__(self, store=None):
        self.store = store  # optional AtlasStore
        self.blue = LearningBlue(alpha=0.2, gamma=0.92, epsilon=0.3, seed=1)
        self.episode = 0
        self.window = deque(maxlen=200)
        self.curve: list[dict] = []          # [{episode, win_rate}]
        self.live: Optional[Game] = None
        self.live_red: Optional[ScriptedRed] = None
        self.live_seed = 0
        if self.store:
            self._maybe_resume()
        self.new_live_game()

    # ---- persistence resume ----------------------------------------------

    def _maybe_resume(self):
        try:
            pol = self.store.latest_policy()
            if pol and pol.get("q"):
                self.blue.q = pol["q"]
            self.curve = [
                {"episode": m["episode"], "win_rate": m["win_rate"]}
                for m in self.store.win_rate_curve()
            ]
        except Exception:
            pass

    # ---- live game (1x viewer) -------------------------------------------

    def new_live_game(self) -> dict:
        self.live_seed = random.randint(0, 2**31)
        self.live = Game(GameConfig(seed=self.live_seed))
        self.live_red = ScriptedRed(seed=self.live_seed)
        # Live game uses the current policy greedily (show what Blue knows).
        self.blue.training = False
        self.blue.epsilon = 0.0
        return self.live.snapshot()

    def step_live(self) -> dict:
        assert self.live and self.live_red
        if self.live.finished:
            return self.live.snapshot()
        self.live.step(self.live_red, self.blue)
        return self.live.snapshot()

    def live_snapshot(self) -> dict:
        assert self.live
        return self.live.snapshot()

    # ---- background self-play (drives the learning curve) ----------------

    def train_batch(self, n: int = 200) -> dict:
        """Run n training episodes with a learning, exploring Blue."""
        self.blue.training = True
        for _ in range(n):
            self.episode += 1
            self.blue.epsilon = max(0.05, 0.3 * (1 - self.episode / 40000))
            seed = random.randint(0, 2**31)
            g = Game(GameConfig(seed=seed))
            res = g.play(ScriptedRed(seed=seed), self.blue)
            self.blue.learn(res)
            self.window.append(1 if res.winner == "blue" else 0)
            if self.episode % 50 == 0:
                rate = sum(self.window) / len(self.window)
                point = {"episode": self.episode, "win_rate": round(rate, 3)}
                self.curve.append(point)
                if self.store:
                    self.store.record_metric(self.episode, rate, len(self.blue.q))
            if self.store and self.episode % 100 == 0:
                self.store.record_episode(self.episode, seed, g.snapshot(), res)
            if self.store and self.episode % 500 == 0:
                self.store.save_policy(self.episode, self.blue.snapshot())
        # Restore greedy mode for the live viewer.
        self.blue.training = False
        self.blue.epsilon = 0.0
        return self.status()

    def status(self) -> dict:
        rate = sum(self.window) / len(self.window) if self.window else 0.0
        return {
            "episode": self.episode,
            "win_rate": round(rate, 3),
            "states_learned": len(self.blue.q),
            "curve_points": len(self.curve),
        }
