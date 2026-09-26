"""Content-free stand-in Env for testing the plumbing (runner, harness, evolve, Mongo writes)
before backend/sim.py exists. Red does nothing; Blue survives 20 turns. Not a game.
Implements the Env interface documented in backend/adapter.py.
"""
import random

NODES = [
    {"id": "internet", "type": "external", "label": "Internet", "crown": False},
    {"id": "router", "type": "router", "label": "Router", "crown": False},
    {"id": "laptopA", "type": "laptop", "label": "Laptop A", "crown": False},
    {"id": "laptopB", "type": "laptop", "label": "Laptop B", "crown": False},
    {"id": "server", "type": "server", "label": "Server", "crown": False},
    {"id": "printer", "type": "printer", "label": "Printer", "crown": False},
    {"id": "database", "type": "database", "label": "Database", "crown": True},
]
EDGES = [
    ["internet", "router"], ["router", "laptopA"], ["router", "laptopB"],
    ["laptopA", "laptopB"], ["laptopA", "server"], ["laptopB", "printer"],
    ["server", "database"], ["printer", "database"],
]
BLUE_ACTIONS = ["scan", "review_logins", "patch", "enable_mfa"]
MAX_TURNS = 20


class StubEnv:
    network = {"nodes": NODES, "edges": EDGES}

    def __init__(self, level: int, seed: int):
        self.level, self.rng = level, random.Random(seed)
        self.board = {n["id"]: ("gray" if n["id"] == "internet" else "blue") for n in NODES}

    def red_step(self, turn):
        return {"action": "noop", "category": "attack", "mitre": None, "from": "internet",
                "target": "internet", "success": False, "detected": False,
                "text": "Stub: Red does nothing", "node_states": dict(self.board)}

    def observe(self, turn):
        return {"turn": turn, "signals": []}

    def legal_actions(self):
        return [{"action": a, "target": n["id"]} for a in BLUE_ACTIONS
                for n in NODES if n["id"] != "internet"]

    def blue_act(self, turn, action, target):
        return {"category": "detect" if action in ("scan", "review_logins") else "harden",
                "success": True, "outcome": "no_finding",
                "text": f"Blue: {action} {target}", "node_states": dict(self.board)}

    def result(self, turn):
        return {"winner": "blue", "win_condition": "survived_20_turns"} if turn >= MAX_TURNS else None

    def metrics(self):
        return {"time_to_detect": None, "time_to_evict": None, "max_nodes_red": 0,
                "false_alarms": 0, "collateral_nodes": 0}


def make_env(level: int, seed: int) -> StubEnv:
    return StubEnv(level, seed)
