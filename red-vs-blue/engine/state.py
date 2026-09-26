"""Node and network state for the game."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Owner(str, Enum):
    BLUE = "blue"     # Blue controls the node (safe)
    RED = "red"       # Red has taken the node
    OFFLINE = "offline"  # isolated / unplugged


class NodeState(str, Enum):
    """UI color states from the design brief."""
    SAFE = "safe"            # blue
    UNDER_ATTACK = "under_attack"  # amber
    TAKEN = "taken"          # red
    OFFLINE = "offline"      # gray


@dataclass
class Node:
    id: str
    kind: str                 # laptop | router | server | printer | database | internet
    is_crown_jewel: bool = False
    is_edge: bool = False     # reachable from the internet (entry point)

    owner: Owner = Owner.BLUE
    patched: bool = False
    passwords_stolen: bool = False
    under_attack: bool = False   # Red has an active foothold attempt here
    # Blue's belief: has Blue *noticed* Red on this node? (partial observability)
    compromise_known: bool = False

    def ui_state(self) -> NodeState:
        if self.owner is Owner.OFFLINE:
            return NodeState.OFFLINE
        if self.owner is Owner.RED:
            # Hidden until Blue scans and spots it (design brief: hidden vs. seen)
            return NodeState.TAKEN if self.compromise_known else NodeState.UNDER_ATTACK
        if self.under_attack and self.compromise_known:
            return NodeState.UNDER_ATTACK
        return NodeState.SAFE


@dataclass
class Network:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: set[tuple[str, str]] = field(default_factory=set)   # undirected
    blocked: set[tuple[str, str]] = field(default_factory=set)  # firewall rules

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, a: str, b: str) -> None:
        self.edges.add(_key(a, b))

    def neighbors(self, node_id: str) -> list[str]:
        out = []
        for a, b in self.edges:
            if _key(a, b) in self.blocked:
                continue
            if a == node_id:
                out.append(b)
            elif b == node_id:
                out.append(a)
        return out

    def block(self, a: str, b: str) -> None:
        self.blocked.add(_key(a, b))

    def crown_jewel(self) -> Node:
        return next(n for n in self.nodes.values() if n.is_crown_jewel)

    def red_owned(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.owner is Owner.RED]

    def edge_nodes(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.is_edge]


def _key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)
