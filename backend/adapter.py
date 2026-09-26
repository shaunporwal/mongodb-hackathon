"""The boundary between Blue and the world.

Blue code (harness.py) may ONLY use an Adapter: observe(), legal_actions(), act().
Today the adapter wraps a simulator Env; later it can wrap real systems
(logs, firewall, Tailscale API) in shadow mode.

Env interface the simulator (backend/sim.py, `make_env(level, seed) -> Env`) must provide.
Only the runner (the referee) touches the Env directly:

    network: dict                      # {"nodes": [{id, type, label, crown}], "edges": [[a, b], ...]}
    red_step(turn) -> dict             # red event fields: action, category="attack", mitre, from,
                                       #   target, success, detected, text, node_states
    observe(turn) -> dict              # Blue-visible only. Must include "signals": [str], e.g.
                                       #   "alert:credential_access@laptopA". Anything else is free-form.
    legal_actions() -> list[dict]      # [{"action": "scan", "target": "server"}, ...]
    blue_act(turn, action, target) -> dict
                                       # blue event fields: category, success, outcome, text, node_states
    result(turn) -> dict | None        # None while running, else {"winner": "red"|"blue",
                                       #   "win_condition": "crown_jewel_stolen"|"half_network_taken"|
                                       #   "survived_20_turns"|"red_evicted"}
    metrics() -> dict                  # optional extras for the games doc: time_to_detect,
                                       #   time_to_evict, max_nodes_red, false_alarms, collateral_nodes
"""
from __future__ import annotations

from typing import Protocol


class Adapter(Protocol):
    def observe(self) -> dict: ...
    def legal_actions(self) -> list[dict]: ...
    def act(self, action: str, target: str) -> dict: ...


class SimAdapter:
    """Adapter over a simulator Env. The runner advances `turn`; Blue never sees the Env."""

    def __init__(self, env):
        self._env = env
        self.turn = 0

    def observe(self) -> dict:
        return self._env.observe(self.turn)

    def legal_actions(self) -> list[dict]:
        return self._env.legal_actions()

    def act(self, action: str, target: str) -> dict:
        return self._env.blue_act(self.turn, action, target)
