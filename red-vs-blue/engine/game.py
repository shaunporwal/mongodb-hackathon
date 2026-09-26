"""The Red vs. Blue game state machine.

One Game == one episode (~20 turns). Each turn: Red moves, then Blue moves,
then win conditions are checked. Everything is driven by a seeded RNG so games
are reproducible and can be replayed from a stored seed.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from .actions import (
    RedAction, BlueAction, RED_TEXT, BLUE_TEXT,
)
from .state import Network, Node, Owner, NodeState
from .topology import default_network


@dataclass
class GameConfig:
    max_turns: int = 20
    half_network_win: bool = True   # Red wins by taking half the (online) network
    seed: Optional[int] = None


@dataclass
class LogEntry:
    turn: int
    side: str            # "red" | "blue" | "result"
    action: Optional[str]
    text: str
    target: Optional[str] = None
    source: Optional[str] = None
    success: bool = True


@dataclass
class GameResult:
    winner: str                 # "blue" | "red"
    turns: int
    reason: str
    red_nodes_held: int


# An agent is a callable: (game, "red"/"blue") -> (Action, target_id, source_id|None)
Agent = Callable[["Game", str], tuple]


class Game:
    def __init__(self, config: GameConfig | None = None, network: Network | None = None):
        self.config = config or GameConfig()
        self.rng = random.Random(self.config.seed)
        self.net = network or default_network()
        self.turn = 0
        self.log: list[LogEntry] = []
        self.finished = False
        self.result: Optional[GameResult] = None
        # Red always starts with a beachhead ambition on an edge node.
        self._red_active = False   # has Red gotten a foothold anywhere yet

    # ---- observation helpers used by agents ------------------------------

    def red_targets(self) -> list[str]:
        """Nodes Red can currently attack: edge nodes (to get in) + neighbors
        of nodes Red already owns."""
        owned = [n.id for n in self.net.red_owned()]
        if not owned:
            return [n.id for n in self.net.edge_nodes()]
        frontier = set()
        for nid in owned:
            for nb in self.net.neighbors(nid):
                node = self.net.nodes[nb]
                if node.owner is not Owner.RED and node.owner is not Owner.OFFLINE:
                    frontier.add(nb)
        # Red can also keep operating on nodes it owns (steal data/passwords)
        return list(frontier) + owned

    def blue_visible_threats(self) -> list[str]:
        """Nodes Blue *knows* are compromised or under attack."""
        return [n.id for n in self.net.nodes.values() if n.compromise_known]

    # ---- turn loop --------------------------------------------------------

    def step(self, red_agent: Agent, blue_agent: Agent) -> None:
        if self.finished:
            return
        self.turn += 1

        # 1. Red moves
        r_action, r_target, r_source = red_agent(self, "red")
        self._apply_red(r_action, r_target, r_source)
        if self._check_end():
            return

        # 2. Blue moves
        b_action, b_target, _ = blue_agent(self, "blue")
        self._apply_blue(b_action, b_target)
        self._check_end()

    def play(self, red_agent: Agent, blue_agent: Agent) -> GameResult:
        while not self.finished and self.turn < self.config.max_turns:
            self.step(red_agent, blue_agent)
        if not self.finished:
            self._finish("blue", "Blue survived all turns")
        return self.result  # type: ignore

    # ---- Red mechanics ----------------------------------------------------

    def _apply_red(self, action: RedAction, target: str, source: Optional[str]) -> None:
        node = self.net.nodes.get(target)
        if node is None or node.owner is Owner.OFFLINE:
            self._log("red", action, "attack fizzled (no valid target)", target, success=False)
            return

        success = False
        if action in (RedAction.PHISHING, RedAction.PASSWORD_GUESS, RedAction.EXPLOIT):
            success = self._attempt_compromise(node, action)
        elif action is RedAction.STEAL_PASSWORDS:
            if node.owner is Owner.RED:
                node.passwords_stolen = True
                success = True
        elif action is RedAction.MOVE_SIDEWAYS:
            success = self._attempt_lateral(node, source)
        elif action is RedAction.STEAL_DATA:
            if node.owner is Owner.RED:
                success = True
                if node.is_crown_jewel:
                    self._log("red", action, RED_TEXT[action].format(target=self._name(target)),
                              target, success=True)
                    self._finish("red", "Red stole the crown jewel")
                    return

        text = RED_TEXT[action].format(
            target=self._name(target), source=self._name(source or ""))
        if not success:
            text += " — failed"
        self._log("red", action, text, target, source, success)

    def _attempt_compromise(self, node: Node, action: RedAction) -> bool:
        # Base chance depends on attack vs. node hardening. Tuned so that a
        # passive defender loses most games but an attentive one has a real
        # chance — this keeps self-play learning meaningful.
        p = {
            RedAction.PHISHING: 0.55 if node.kind == "laptop" else 0.12,
            RedAction.PASSWORD_GUESS: 0.25,
            RedAction.EXPLOIT: 0.60 if not node.patched else 0.0,
        }[action]
        # Only edge nodes are reachable from outside if Red has no foothold yet.
        if not self._red_active and not node.is_edge:
            return False
        if self.rng.random() < p:
            node.owner = Owner.RED
            node.under_attack = True
            self._red_active = True
            return True
        # A failed attempt still raises the node's noise (Blue can scan to find it).
        node.under_attack = True
        return False

    def _attempt_lateral(self, node: Node, source: Optional[str]) -> bool:
        if source is None:
            return False
        src = self.net.nodes.get(source)
        if not src or src.owner is not Owner.RED:
            return False
        if node.id not in self.net.neighbors(source):
            return False  # firewall or not connected
        # Stolen passwords make lateral movement much easier. Patched targets
        # resist lateral exploitation too.
        base = 0.70 if src.passwords_stolen else 0.40
        p = base * (0.5 if node.patched else 1.0)
        if self.rng.random() < p:
            node.owner = Owner.RED
            node.under_attack = True
            return True
        node.under_attack = True
        return False

    # ---- Blue mechanics ---------------------------------------------------

    def _apply_blue(self, action: BlueAction, target: str) -> None:
        node = self.net.nodes.get(target)
        if node is None:
            self._log("blue", action, "no valid target", target, success=False)
            return

        success = True
        if action is BlueAction.SCAN:
            # Reveal Red on this node (and, cheaply, obvious noise on neighbors).
            found = node.owner is Owner.RED or node.under_attack
            if node.owner is Owner.RED or node.under_attack:
                node.compromise_known = True
            for nb in self.net.neighbors(target):
                nn = self.net.nodes[nb]
                if nn.owner is Owner.RED and self.rng.random() < 0.5:
                    nn.compromise_known = True
            text = BLUE_TEXT[action].format(target=self._name(target))
            text += ": intruder found!" if found else ": all clear"
            self._log("blue", action, text, target, success=found)
            return
        elif action is BlueAction.PATCH:
            node.patched = True
        elif action is BlueAction.RESET_PASSWORDS:
            node.passwords_stolen = False
        elif action is BlueAction.FIREWALL:
            # Block the riskiest edge from this node (toward the crown jewel path).
            nbs = self.net.neighbors(target)
            if nbs:
                self.net.block(target, nbs[0])
            else:
                success = False
        elif action is BlueAction.ISOLATE:
            if node.is_crown_jewel:
                success = False  # can't unplug the thing you're protecting
            else:
                node.owner = Owner.OFFLINE
        elif action is BlueAction.RESTORE:
            if node.owner is Owner.RED:
                node.owner = Owner.BLUE
                node.under_attack = False
                node.passwords_stolen = False
                node.compromise_known = False
            else:
                success = False

        self._log("blue", action, BLUE_TEXT[action].format(target=self._name(target)),
                  target, success=success)

    # ---- win conditions ---------------------------------------------------

    def _check_end(self) -> bool:
        if self.finished:
            return True
        # Red wins by controlling a majority of the *total* non-internet
        # network (fixed denominator so isolating nodes doesn't hand Red a win).
        total = [n for n in self.net.nodes.values() if n.kind != "internet"]
        red = [n for n in total if n.owner is Owner.RED]
        threshold = (len(total) + 1) // 2 + 1  # a clear majority of the network
        if self.config.half_network_win and total and len(red) >= threshold:
            self._finish("red", "Red controls most of the network")
            return True
        # Blue wins by evicting Red entirely (only if Red ever got in).
        if self._red_active and not red:
            self._finish("blue", "Blue evicted Red from the network")
            return True
        return False

    def _finish(self, winner: str, reason: str) -> None:
        self.finished = True
        held = len(self.net.red_owned())
        self.result = GameResult(winner, self.turn, reason, held)
        self._log("result", None,
                  f"{winner.upper()} wins — {reason}. Red held {held} node(s).")

    # ---- utilities --------------------------------------------------------

    def _name(self, node_id: str) -> str:
        pretty = {
            "laptop_a": "Laptop A", "laptop_b": "Laptop B", "router": "Router",
            "server": "Server", "printer": "Printer", "database": "Database",
            "internet": "Internet",
        }
        return pretty.get(node_id, node_id)

    def _log(self, side, action, text, target=None, source=None, success=True):
        self.log.append(LogEntry(
            turn=self.turn, side=side,
            action=action.value if action else None,
            text=text, target=target, source=source, success=success))

    def snapshot(self) -> dict:
        """Serializable view for the API / MongoDB."""
        return {
            "turn": self.turn,
            "finished": self.finished,
            "nodes": [
                {
                    "id": n.id, "kind": n.kind, "crown": n.is_crown_jewel,
                    "owner": n.owner.value, "state": n.ui_state().value,
                    "patched": n.patched, "known": n.compromise_known,
                }
                for n in self.net.nodes.values()
            ],
            "edges": [list(e) for e in self.net.edges],
            "blocked": [list(b) for b in self.net.blocked],
            "log": [vars(e) for e in self.log],
            "result": vars(self.result) if self.result else None,
        }
