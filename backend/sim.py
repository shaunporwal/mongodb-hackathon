"""Env for the runner, wrapping the teammate's engine in red-vs-blue/ (engine/ + agents/red.py).

Pure translation layer: node ids (laptop_a -> laptopA), action names, event/result shapes
per the data contract, and a noisy signal feed for Blue. All game rules and Red behavior
live in red-vs-blue/engine and red-vs-blue/agents/red.py.

Known gap: the engine has ONE scripted Red, so `level` is recorded but doesn't change Red yet.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "red-vs-blue"))

from agents.red import ScriptedRed  # noqa: E402
from engine.actions import BlueAction  # noqa: E402
from engine.game import Game, GameConfig  # noqa: E402
from engine.state import Owner  # noqa: E402

MAX_TURNS = 20
TO_OURS = {"laptop_a": "laptopA", "laptop_b": "laptopB"}
TO_ENGINE = {v: k for k, v in TO_OURS.items()}
LABEL = {"internet": "Internet", "router": "Router", "laptopA": "Laptop A", "laptopB": "Laptop B",
         "server": "Server", "printer": "Printer", "database": "Database"}

# engine red action -> MITRE ATT&CK id (labels for the UI)
MITRE = {"phishing": "T1566", "password_guess": "T1110", "exploit": "T1190",
         "steal_passwords": "T1003", "move_sideways": "T1021", "steal_data": "T1041"}

# our blue action name -> (engine action, category)
BLUE = {
    "scan": (BlueAction.SCAN, "detect"),
    "patch": (BlueAction.PATCH, "harden"),
    "firewall_block": (BlueAction.FIREWALL, "harden"),
    "reset_creds": (BlueAction.RESET_PASSWORDS, "respond"),
    "isolate": (BlueAction.ISOLATE, "respond"),
    "restore": (BlueAction.RESTORE, "respond"),
}

# What each Blue action does in the engine (shown to Blue like tool descriptions).
ACTION_HELP = {
    "scan": "check a node; confirms or clears suspicion (turns suspicious_activity into confirmed_intruder)",
    "patch": "harden a node against exploits; does NOT remove an intruder already there",
    "firewall_block": "block one link out of this node; does NOT remove an intruder",
    "reset_creds": "make stolen passwords on this node useless; does NOT remove an intruder",
    "isolate": "take a node offline: stops spread through it, but the node is lost to Blue (not allowed on database)",
    "restore": "wipe an intruder-held node back to Blue control; fails on a clean node",
}

WIN_CONDITION = {
    "Red stole the crown jewel": "crown_jewel_stolen",
    "Red controls most of the network": "half_network_taken",
    "Blue evicted Red from the network": "red_evicted",
    "Blue survived all turns": "survived_20_turns",
}

# Blue's sensor model (not engine rules): how often activity on a node shows up as a signal.
SIGNAL_P = 0.6
FALSE_ALARM_P = 0.05


def ours(nid: str | None) -> str | None:
    return TO_OURS.get(nid, nid) if nid else nid


class EngineEnv:
    def __init__(self, level: int, seed: int):
        self.level = level
        self.game = Game(GameConfig(max_turns=MAX_TURNS, seed=seed))
        self.red = ScriptedRed(seed)
        self.noise = random.Random(seed * 7919 + 1)
        self.visible: set[str] = set()  # nodes whose activity Blue sees this turn
        self._first_detect = None
        self._evicted_at = None
        self._max_red = 0
        self._false_alarms = 0
        self._collateral: set[str] = set()
        net = self.game.net
        self.network = {
            "nodes": [{"id": ours(n.id), "type": n.kind, "label": LABEL[ours(n.id)],
                       "crown": n.is_crown_jewel} for n in net.nodes.values()],
            "edges": [[ours(a), ours(b)] for a, b in sorted(net.edges)],
        }

    # ----- helpers -----
    def _node_states(self) -> dict:
        out = {}
        for n in self.game.net.nodes.values():
            if n.kind == "internet" or n.owner is Owner.OFFLINE:
                c = "gray"
            elif n.owner is Owner.RED:
                c = "red"
            elif n.under_attack or n.passwords_stolen:
                c = "amber"
            else:
                c = "blue"
            out[ours(n.id)] = c
        return out

    def _roll_signals(self) -> None:
        self.visible = set()
        for n in self.game.net.nodes.values():
            if n.kind == "internet" or n.owner is Owner.OFFLINE:
                continue
            p = SIGNAL_P if (n.under_attack or n.owner is Owner.RED) else FALSE_ALARM_P
            if self.noise.random() < p:
                self.visible.add(n.id)

    def _track(self, turn: int) -> None:
        red = len(self.game.net.red_owned())
        self._max_red = max(self._max_red, red)
        if self._first_detect is None and self.game.blue_visible_threats():
            self._first_detect = turn

    # ----- Env interface -----
    def red_step(self, turn: int) -> dict:
        g = self.game
        g.turn = turn
        action, target, source = self.red(g, "red")
        n_log = len(g.log)
        g._apply_red(action, target, source)
        g._check_end()
        entry = next(e for e in g.log[n_log:] if e.side == "red")
        self._roll_signals()
        self._track(turn)
        return {
            "action": entry.action, "category": "attack", "mitre": MITRE.get(entry.action),
            "from": ours(entry.source) or ("internet" if entry.action in ("phishing", "password_guess") else None),
            "target": ours(entry.target), "success": entry.success,
            "detected": target in self.visible or g.net.nodes[target].compromise_known,
            "text": entry.text[0].upper() + entry.text[1:] + (f" ({MITRE[entry.action]})" if entry.action in MITRE else ""),
            "node_states": self._node_states(),
        }

    def observe(self, turn: int) -> dict:
        net = self.game.net
        signals = []
        for nid in sorted(self.visible):
            n = net.nodes[nid]
            kind = "confirmed_intruder" if n.compromise_known else "suspicious_activity"
            signals.append(f"alert:{kind}@{ours(nid)}")
        return {
            "turn": turn,
            "signals": signals,
            "known_compromised": [ours(n) for n in self.game.blue_visible_threats()],
            "patched": [ours(n.id) for n in net.nodes.values() if n.patched],
            "offline": [ours(n.id) for n in net.nodes.values() if n.owner is Owner.OFFLINE],
            "blocked_links": [[ours(a), ours(b)] for a, b in sorted(net.blocked)],
        }

    def describe_actions(self) -> dict:
        return ACTION_HELP

    def legal_actions(self) -> list[dict]:
        out = []
        for n in self.game.net.nodes.values():
            if n.kind == "internet":
                continue
            for name in BLUE:
                if name == "isolate" and (n.is_crown_jewel or n.owner is Owner.OFFLINE):
                    continue
                out.append({"action": name, "target": ours(n.id)})
        return out

    def blue_act(self, turn: int, action: str, target: str) -> dict:
        g = self.game
        g.turn = turn
        eng_action, category = BLUE[action]
        eng_target = TO_ENGINE.get(target, target)
        node = g.net.nodes[eng_target]
        was_red = node.owner is Owner.RED
        was_known = node.compromise_known
        n_log = len(g.log)
        g._apply_blue(eng_action, eng_target)
        g._check_end()
        entry = next(e for e in g.log[n_log:] if e.side == "blue")

        if action == "scan":
            outcome = "true_catch" if entry.success else "no_finding"
        elif action in ("isolate", "restore", "reset_creds"):
            if was_red:
                outcome = "recovery" if action == "restore" else "true_catch"
            else:
                outcome = "false_alarm"
                self._false_alarms += 1
                if action == "isolate":
                    self._collateral.add(eng_target)
        else:
            outcome = None
        if was_red and not was_known and node.compromise_known and self._first_detect is None:
            self._first_detect = turn
        self._track(turn)
        if self._evicted_at is None and g.result and g.result.reason.startswith("Blue evicted"):
            self._evicted_at = turn
        return {"category": category, "success": entry.success, "outcome": outcome,
                "text": "Blue " + entry.text, "node_states": self._node_states()}

    def result(self, turn: int) -> dict | None:
        r = self.game.result
        if r is None and turn >= MAX_TURNS:
            self.game._finish("blue", "Blue survived all turns")
            r = self.game.result
        if r is None:
            return None
        return {"winner": r.winner, "win_condition": WIN_CONDITION.get(r.reason, r.reason)}

    def metrics(self) -> dict:
        return {"time_to_detect": self._first_detect, "time_to_evict": self._evicted_at,
                "max_nodes_red": self._max_red, "false_alarms": self._false_alarms,
                "collateral_nodes": len(self._collateral)}


def make_env(level: int, seed: int) -> EngineEnv:
    return EngineEnv(level, seed)


if __name__ == "__main__":
    # smoke test: random Blue vs the engine, per level
    for level in range(1, 6):
        wins = 0
        for seed in range(50):
            env, rng = make_env(level, seed), random.Random(seed)
            for t in range(1, MAX_TURNS + 1):
                env.red_step(t)
                if env.result(t):
                    break
                la = rng.choice(env.legal_actions())
                env.blue_act(t, la["action"], la["target"])
                if env.result(t):
                    break
            wins += env.result(MAX_TURNS)["winner"] == "blue"
        print(f"level {level}: random Blue wins {wins}/50")
