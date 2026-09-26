r"""Default network topology, matching the design brief's example board.

    Internet - Router - Laptop A - Server
                 |  \                |
              Laptop B - Printer   Database (crown jewel)
"""
from __future__ import annotations

from .state import Network, Node


def default_network() -> Network:
    net = Network()
    net.add_node(Node("internet", "internet", is_edge=False))
    net.add_node(Node("router", "router"))
    net.add_node(Node("laptop_a", "laptop", is_edge=True))
    net.add_node(Node("laptop_b", "laptop", is_edge=True))
    net.add_node(Node("printer", "printer"))
    net.add_node(Node("server", "server"))
    net.add_node(Node("database", "database", is_crown_jewel=True))

    net.add_edge("internet", "router")
    net.add_edge("router", "laptop_a")
    net.add_edge("router", "laptop_b")
    net.add_edge("laptop_a", "server")
    net.add_edge("laptop_b", "printer")
    net.add_edge("printer", "database")
    net.add_edge("server", "database")
    return net


# Config dict form so the topology can live in Atlas `configs` and be evolved.
def default_config() -> dict:
    return {
        "name": "default",
        "nodes": [
            {"id": "internet", "kind": "internet", "edge": False, "crown": False},
            {"id": "router", "kind": "router", "edge": False, "crown": False},
            {"id": "laptop_a", "kind": "laptop", "edge": True, "crown": False},
            {"id": "laptop_b", "kind": "laptop", "edge": True, "crown": False},
            {"id": "printer", "kind": "printer", "edge": False, "crown": False},
            {"id": "server", "kind": "server", "edge": False, "crown": False},
            {"id": "database", "kind": "database", "edge": False, "crown": True},
        ],
        "edges": [
            ["internet", "router"], ["router", "laptop_a"], ["router", "laptop_b"],
            ["laptop_a", "server"], ["laptop_b", "printer"],
            ["printer", "database"], ["server", "database"],
        ],
    }


def network_from_config(cfg: dict) -> Network:
    net = Network()
    for n in cfg["nodes"]:
        net.add_node(Node(n["id"], n["kind"], is_crown_jewel=n.get("crown", False),
                          is_edge=n.get("edge", False)))
    for a, b in cfg["edges"]:
        net.add_edge(a, b)
    return net
