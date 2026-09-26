"""Red-learner Env: the LLM plays RED (the learner), a SCRIPTED BLUE defends at levels 1-5.

Mirror of backend/sim.py. Everything symbolic, reusing the teammate engine's existing
mechanics (engine.game._apply_red / _apply_blue) — no new game rules are authored here.
The learner only ever emits one of the fixed symbolic actions against fake nodes; the Red
strategy comes entirely from the harness prompt (backend/prompts.py RED_*), not from here.

Metrics are Red-centric (what the demo cares about): turns-to-crown-jewel,
time-to-discovery, time-to-exploitation, vulns_reached, wasted_actions.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "red-vs-blue"))

from engine.actions import BlueAction, RedAction  # noqa: E402
from engine.game import Game, GameConfig  # noqa: E402
from engine.state import Owner  # noqa: E402

from backend.vuln import DEFENSE_MITIGATION, Flaw  # noqa: E402

MAX_TURNS = 20
TO_OURS = {"laptop_a": "laptopA", "laptop_b": "laptopB"}
TO_ENGINE = {v: k for k, v in TO_OURS.items()}
LABEL = {"internet": "Internet", "router": "Router", "laptopA": "Laptop A", "laptopB": "Laptop B",
         "server": "Server", "printer": "Printer", "database": "Database"}
MITRE = {"phishing": "T1566", "password_guess": "T1110", "exploit": "T1190",
         "steal_passwords": "T1003", "move_sideways": "T1021", "steal_data": "T1041"}

# Red's symbolic action set (the learner picks one of these each turn) -> engine action.
RED = {
    "phishing": RedAction.PHISHING,
    "exploit": RedAction.EXPLOIT,
    "steal_passwords": RedAction.STEAL_PASSWORDS,
    "move_sideways": RedAction.MOVE_SIDEWAYS,
    "steal_data": RedAction.STEAL_DATA,
    "probe": None,  # reveals a hidden flaw on a reachable node (a "discovery" action; costs a turn)
}
ACTION_HELP = {
    "phishing": "try to get an initial foothold on a reachable node",
    "exploit": "attack a reachable node's flaw to take it over (better if the flaw is discovered)",
    "steal_passwords": "on a node you already hold, take credentials to ease the next hop",
    "move_sideways": "hop from a node you hold to a connected node",
    "steal_data": "on a node you hold, exfiltrate; on the crown-jewel database this wins",
    "probe": "scan a reachable node to discover a hidden flaw (does not take the node)",
}
WIN_CONDITION = {
    "Red stole the crown jewel": "crown_jewel_stolen",
    "Red controls most of the network": "half_network_taken",
    "Blue evicted Red from the network": "red_evicted",
    "Blue survived all turns": "survived_20_turns",
}


def ours(nid): return TO_OURS.get(nid, nid) if nid else nid


class RedLearnerEnv:
    """`level` sets how hard the SCRIPTED BLUE defends (1 easy .. 5 hard)."""

    def __init__(self, level: int, seed: int):
        self.level = level
        self.game = Game(GameConfig(max_turns=MAX_TURNS, seed=seed))
        self.rng = random.Random(seed)
        self.mitigation = DEFENSE_MITIGATION.get(level, 0.0)
        # One abstract flaw per non-edge internal node; discovery is hidden until probed.
        self.flaws = {n.id: Flaw(prob=0.6, discovered=False)
                      for n in self.game.net.nodes.values() if n.kind not in ("internet",)}
        self._first_foothold = None   # time-to-discovery proxy: first node Red holds
        self._first_crown = None      # time-to-exploitation: first turn Red holds the crown
        self._discovered_turn = None  # first turn a probe reveals any flaw
        self._max_red = 0
        self._wasted = 0
        self._reached: set[str] = set()
        net = self.game.net
        self.network = {
            "nodes": [{"id": ours(n.id), "type": n.kind, "label": LABEL[ours(n.id)],
                       "crown": n.is_crown_jewel} for n in net.nodes.values()],
            "edges": [[ours(a), ours(b)] for a, b in sorted(net.edges)],
        }

    # ----- board rendering -----
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

    def _track(self, turn: int) -> None:
        red = self.game.net.red_owned()
        self._max_red = max(self._max_red, len(red))
        for n in red:
            self._reached.add(n.id)
        if red and self._first_foothold is None:
            self._first_foothold = turn
        if self._first_crown is None and self.game.net.crown_jewel().owner is Owner.RED:
            self._first_crown = turn

    # ----- SCRIPTED BLUE DEFENDER (the opponent; harder at higher levels) -----
    def opponent_step(self, turn: int) -> dict:
        g = self.game
        g.turn = turn
        net = g.net
        known = [n for n in net.nodes.values() if n.compromise_known]
        action, target = None, None
        # L3+ hunt proactively; everyone reacts to known compromise.
        if known:
            n = known[0]
            action, target = (BlueAction.RESTORE, n.id) if self.level >= 2 else (BlueAction.RESET_PASSWORDS, n.id)
        elif self.level >= 3 and turn % 2 == 0:
            cand = [n for n in net.nodes.values() if n.kind != "internet" and n.owner is Owner.BLUE]
            if cand:
                action, target = BlueAction.SCAN, self.rng.choice(cand).id
        elif self.level >= 4:
            unp = [n for n in net.nodes.values() if not n.patched and n.kind != "internet"]
            if unp:
                action, target = BlueAction.PATCH, unp[0].id
        if action is None:
            crown = net.crown_jewel()
            action, target = BlueAction.SCAN, crown.id
        n_log = len(g.log)
        g._apply_blue(action, target)
        g._check_end()
        entry = next((e for e in g.log[n_log:] if e.side == "blue"), None)
        self._track(turn)
        return {"action": action.value, "category": "defend", "mitre": None, "from": None,
                "target": ours(target), "success": bool(entry and entry.success), "detected": None,
                "outcome": None, "text": "Blue " + (entry.text if entry else f"{action.value} {target}"),
                "node_states": self._node_states()}

    # ----- RED learner interface -----
    def describe_actions(self) -> dict:
        return ACTION_HELP

    def observe(self, turn: int) -> dict:
        net = self.game.net
        owned = [ours(n.id) for n in net.red_owned()]
        reachable = [ours(t) for t in self.game.red_targets()]
        discovered = [ours(nid) for nid, f in self.flaws.items() if f.discovered]
        # Red sees its own footprint clearly; defenders' internals stay hidden.
        return {"turn": turn, "signals": [], "footholds": owned, "reachable": reachable,
                "flaws_discovered": discovered,
                "crown": ours(net.crown_jewel().id),
                "crown_owned": net.crown_jewel().owner is Owner.RED}

    def legal_actions(self) -> list[dict]:
        net = self.game.net
        owned = {n.id for n in net.red_owned()}
        reachable = set(self.game.red_targets())
        out = []
        for name in RED:
            if name in ("steal_passwords", "steal_data"):
                targets = owned
            elif name == "move_sideways":
                targets = reachable - owned
            else:  # phishing, exploit, probe
                targets = reachable
            for t in targets:
                if net.nodes[t].kind != "internet":
                    out.append({"action": name, "target": ours(t)})
        return out or [{"action": "probe", "target": ours(next(iter(reachable), "router"))}]

    def blue_act(self, turn: int, action: str, target: str) -> dict:
        """Named blue_act for the runner/adapter, but this applies the RED learner's move."""
        g = self.game
        g.turn = turn
        eng_target = TO_ENGINE.get(target, target)
        node = g.net.nodes.get(eng_target)
        if node is None or node.owner is Owner.OFFLINE:
            self._wasted += 1
            return {"category": "attack", "success": False, "outcome": "wasted",
                    "mitre": None, "from": None, "text": f"Red {action} on {target}: no effect",
                    "node_states": self._node_states()}

        if action == "probe":
            flaw = self.flaws.get(eng_target)
            first = flaw.reveal() if flaw else False
            if first and self._discovered_turn is None:
                self._discovered_turn = turn
            self._track(turn)
            return {"category": "attack", "success": bool(flaw), "outcome": "discovery",
                    "mitre": None, "from": None,
                    "text": f"Red probed {LABEL[ours(eng_target)]}: "
                            + ("flaw discovered" if flaw else "nothing found"),
                    "node_states": self._node_states()}

        # exploit odds are lowered by the defense level if the flaw is undiscovered/patched
        eng_action = RED[action]
        source = None
        if action == "move_sideways":
            src = next((n.id for n in g.net.red_owned() if eng_target in g.net.neighbors(n.id)), None)
            source = src
        n_log = len(g.log)
        g._apply_red(eng_action, eng_target, source)
        g._check_end()
        entry = next((e for e in g.log[n_log:] if e.side == "red"), None)
        if entry is None or not entry.success:
            self._wasted += 1 if entry and not entry.success else 0
        self._track(turn)
        mitre = MITRE.get(action)
        text = ("Red " + entry.text) if entry else f"Red {action} on {target}"
        return {"category": "attack", "success": bool(entry and entry.success),
                "outcome": "success" if (entry and entry.success) else "failed",
                "mitre": mitre, "from": ours(source), "text": text + (f" ({mitre})" if mitre else ""),
                "node_states": self._node_states()}

    def result(self, turn: int) -> dict | None:
        r = self.game.result
        if r is None and turn >= MAX_TURNS:
            self.game._finish("blue", "Blue survived all turns")
            r = self.game.result
        if r is None:
            return None
        return {"winner": r.winner, "win_condition": WIN_CONDITION.get(r.reason, r.reason)}

    def metrics(self) -> dict:
        return {"time_to_detect": self._discovered_turn, "time_to_evict": None,
                "max_nodes_red": self._max_red, "false_alarms": 0,
                "collateral_nodes": 0,
                # Red-centric extras (also stored on the game doc):
                "time_to_discovery": self._first_foothold, "time_to_exploitation": self._first_crown,
                "vulns_reached": len(self._reached), "wasted_actions": self._wasted}


def make_env(level: int, seed: int) -> RedLearnerEnv:
    return RedLearnerEnv(level, seed)


if __name__ == "__main__":
    # smoke test: RANDOM Red (no LLM, no attacker prompt) vs scripted Blue, per level.
    for level in range(1, 6):
        red_wins, ttc = 0, []
        for seed in range(40):
            env, rng = make_env(level, seed), random.Random(seed)
            for t in range(1, MAX_TURNS + 1):
                env.opponent_step(t)
                if env.result(t):
                    break
                la = rng.choice(env.legal_actions())
                env.blue_act(t, la["action"], la["target"])
                if env.result(t):
                    break
            res = env.result(MAX_TURNS)
            if res["winner"] == "red":
                red_wins += 1
                if env._first_crown:
                    ttc.append(env._first_crown)
        avg = f"{sum(ttc)/len(ttc):.1f}" if ttc else "-"
        print(f"defense L{level}: random Red wins {red_wins}/40, avg turns-to-crown {avg}")
