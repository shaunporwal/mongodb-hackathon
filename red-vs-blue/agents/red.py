"""Red (attacker) policy.

A competent but not omniscient scripted attacker: get in at the edge, steal
passwords to grease lateral movement, then push toward the crown jewel and
exfiltrate. This gives Blue a consistent, strong adversary to learn against so
that a rising Blue win rate is meaningful.
"""
from __future__ import annotations

import random

from engine.actions import RedAction
from engine.state import Owner


class ScriptedRed:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def __call__(self, game, side):
        net = game.net
        owned = net.red_owned()

        # No foothold yet -> break in at an edge laptop (phishing is best there).
        if not owned:
            edges = [n for n in net.edge_nodes() if n.owner is Owner.BLUE]
            if edges:
                target = self.rng.choice(edges)
                return RedAction.PHISHING, target.id, None
            return RedAction.PHISHING, net.edge_nodes()[0].id, None

        # If we own a node adjacent to the crown jewel, try to exfiltrate it.
        cj = net.crown_jewel()
        if cj.owner is Owner.RED:
            return RedAction.STEAL_DATA, cj.id, None

        # Grab passwords on a held node we haven't looted yet (enables lateral).
        unlootedd = [n for n in owned if not n.passwords_stolen]
        if unlootedd and self.rng.random() < 0.5:
            return RedAction.STEAL_PASSWORDS, self.rng.choice(unlootedd).id, None

        # Otherwise move laterally toward new ground, preferring the crown path.
        for src in owned:
            neighbors = net.neighbors(src.id)
            # Prefer a neighbor that is the crown jewel or leads deeper.
            neighbors.sort(key=lambda nid: (not net.nodes[nid].is_crown_jewel))
            for nid in neighbors:
                node = net.nodes[nid]
                if node.owner is Owner.BLUE:
                    # Exploit unpatched, else move sideways (uses stolen creds).
                    if not node.patched and self.rng.random() < 0.5:
                        return RedAction.EXPLOIT, nid, src.id
                    return RedAction.MOVE_SIDEWAYS, nid, src.id

        # Nothing to expand to: try password guessing on any reachable target.
        targets = game.red_targets()
        if targets:
            return RedAction.PASSWORD_GUESS, self.rng.choice(targets), None
        # Fallback: loot what we have.
        return RedAction.STEAL_PASSWORDS, owned[0].id, None
