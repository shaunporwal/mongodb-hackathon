"""Single source of truth for the network board, labels, colors, MITRE ids and mappings.
Loaded from shared/board.json so backend and frontend never drift. Import from here instead
of re-declaring literals in sim.py / sim_red.py / api.py.
"""
import json
from functools import lru_cache
from pathlib import Path

BOARD_PATH = Path(__file__).resolve().parent.parent / "shared" / "board.json"


@lru_cache(maxsize=1)
def board() -> dict:
    return json.loads(BOARD_PATH.read_text())


NETWORK_ID = board()["network_id"]
MAX_TURNS = board()["max_turns"]
LABEL = {n["id"]: n["label"] for n in board()["nodes"]}
POS = {n["id"]: n["pos"] for n in board()["nodes"]}
EDGES = board()["edges"]
COLORS = board()["colors"]
STATE_ALIAS = board()["state_alias"]
MITRE = board()["mitre"]
ID_MAP = board()["id_map"]                       # engine id -> our id
ID_MAP_REV = {v: k for k, v in ID_MAP.items()}   # our id -> engine id
WIN_CONDITION = board()["win_condition"]


def ours(nid):
    return ID_MAP.get(nid, nid) if nid else nid


def to_engine(nid):
    return ID_MAP_REV.get(nid, nid) if nid else nid

TO_ENGINE = ID_MAP_REV  # alias

VULNS = board().get("vulnerabilities", {})
