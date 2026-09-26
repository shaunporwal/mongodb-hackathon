"""Blue (defender) policies.

`LearningBlue` is a tabular Q-learning agent. The state is a compact, hashable
feature tuple describing what Blue can *see* (partial observability), and the
action is (defense_type, target_selector). Rewards come at episode end
(+1 win / -1 loss) with small shaping for evicting Red, so the policy provably
improves its win rate against the scripted Red over many self-play episodes.

The Q-table is a plain dict[str, dict[str, float]] so it serializes straight to
MongoDB as a `policy_snapshot`.
"""
from __future__ import annotations

import random

from engine.actions import BlueAction
from engine.state import Owner


# Blue chooses a defense TYPE; a target selector maps type -> concrete node,
# using only information Blue is allowed to see.
DEFENSE_TYPES = [
    BlueAction.SCAN,
    BlueAction.PATCH,
    BlueAction.RESET_PASSWORDS,
    BlueAction.FIREWALL,
    BlueAction.ISOLATE,
    BlueAction.RESTORE,
]


class RandomBlue:
    """Baseline: pick a random legal-ish move. Used to show the learning delta."""
    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def __call__(self, game, side):
        action = self.rng.choice(DEFENSE_TYPES)
        target = _select_target(game, action, self.rng)
        return action, target, None


class LearningBlue:
    def __init__(self, alpha=0.3, gamma=0.9, epsilon=0.2, seed=None, q=None, counts=None):
        self.alpha = alpha        # kept for API compatibility (unused by MC-average)
        self.gamma = gamma
        self.epsilon = epsilon
        self.rng = random.Random(seed)
        self.q: dict[str, dict[str, float]] = q or {}
        # Visit counts enable stable running-average returns (proper MC control),
        # which converges far more reliably than a fixed step size against a
        # noisy adversary.
        self.counts: dict[str, dict[str, int]] = counts or {}
        # Per-episode trajectory for end-of-game learning.
        self._traj: list[tuple[str, str]] = []
        self.training = True

    # ---- feature encoding (what Blue can see) ----------------------------

    def state_key(self, game) -> str:
        net = game.net
        known = game.blue_visible_threats()
        n_known = min(len(known), 2)          # 0, 1, 2+
        cj = net.crown_jewel()
        # Is a *known* threat adjacent to the crown jewel? (imminent danger)
        cj_adj = any(cj.id in net.neighbors(nid) for nid in known)
        cj_taken = cj.owner is Owner.RED
        # Is there unexplained noise Blue hasn't confirmed? (should scan)
        unknown_noise = any(
            n.under_attack and not n.compromise_known and n.owner is not Owner.OFFLINE
            for n in net.nodes.values()
        )
        # Are Blue's important nodes patched? (server/database/router)
        key_unpatched = any(
            not n.patched and n.owner is Owner.BLUE
            and n.kind in ("server", "database", "router")
            for n in net.nodes.values()
        )
        phase = 0 if game.turn <= 6 else (1 if game.turn <= 13 else 2)
        return (f"k{n_known}|adj{int(cj_adj)}|cj{int(cj_taken)}"
                f"|noise{int(unknown_noise)}|unp{int(key_unpatched)}|p{phase}")

    # ---- action selection -------------------------------------------------

    def __call__(self, game, side):
        s = self.state_key(game)
        row = self.q.setdefault(s, {a.value: 0.0 for a in DEFENSE_TYPES})

        if self.training and self.rng.random() < self.epsilon:
            action = self.rng.choice(DEFENSE_TYPES)
        else:
            best = max(row.values())
            best_actions = [a for a, v in row.items() if v == best]
            action = BlueAction(self.rng.choice(best_actions))

        self._traj.append((s, action.value))
        target = _select_target(game, action, self.rng)
        return action, target, None

    # ---- learning ---------------------------------------------------------

    def learn(self, result) -> None:
        """Monte-Carlo style update over the episode trajectory."""
        if not self.training:
            self._traj.clear()
            return
        reward = 1.0 if result.winner == "blue" else -1.0
        # Shaping: winning while holding Red to fewer nodes is better; a fast
        # loss (Red overran quickly) is penalised more.
        if result.winner == "blue":
            reward += 0.1 * (0 if result.red_nodes_held == 0 else -result.red_nodes_held * 0.1)
        else:
            reward -= 0.3 * (1.0 - result.turns / 20.0)  # earlier loss = worse
        # Reward is terminal-only, so the discounted return at a step that is
        # k moves from the end is reward * gamma**k. Walk backwards, discounting
        # as we go, and use every-visit running-average returns per (s, a).
        g = reward
        for s, a in reversed(self._traj):
            row = self.q.setdefault(s, {act.value: 0.0 for act in DEFENSE_TYPES})
            crow = self.counts.setdefault(s, {act.value: 0 for act in DEFENSE_TYPES})
            crow[a] += 1
            row[a] += (g - row[a]) / crow[a]   # incremental mean: Q += (G - Q)/N
            g *= self.gamma
        self._traj.clear()

    def snapshot(self) -> dict:
        return {"gamma": self.gamma, "epsilon": self.epsilon,
                "q": self.q, "counts": self.counts, "states": len(self.q)}


def _select_target(game, action: BlueAction, rng: random.Random) -> str:
    """Map a defense type to a concrete node using only visible info."""
    net = game.net
    known = game.blue_visible_threats()
    cj = net.crown_jewel()

    if action is BlueAction.SCAN:
        # Scan somewhere we suspect but don't yet confirm: prefer nodes near the
        # crown jewel, else a random online node.
        candidates = [n.id for n in net.nodes.values()
                      if n.owner is not Owner.OFFLINE and n.kind != "internet"]
        near_cj = [nid for nid in net.neighbors(cj.id)
                   if net.nodes[nid].owner is not Owner.OFFLINE]
        pool = near_cj or candidates
        return rng.choice(pool) if pool else cj.id

    if action is BlueAction.RESTORE:
        # Restore a known-compromised node (prefer one adjacent to crown jewel).
        if known:
            known.sort(key=lambda nid: (cj.id not in net.neighbors(nid)))
            return known[0]
        # Nothing known to restore -> harmless fallback.
        return cj.id

    if action is BlueAction.ISOLATE:
        # Isolate a known-compromised, non-crown node to stop spread.
        cands = [nid for nid in known if not net.nodes[nid].is_crown_jewel]
        if cands:
            return cands[0]
        return _defensive_node(net, rng)

    if action is BlueAction.FIREWALL:
        # Protect the crown jewel: block one of its links.
        nbs = net.neighbors(cj.id)
        return cj.id if nbs else _defensive_node(net, rng)

    if action is BlueAction.PATCH:
        # Patch a valuable, unpatched, online node (server/database first).
        cands = [n for n in net.nodes.values()
                 if not n.patched and n.owner is Owner.BLUE and n.kind in ("server", "database", "router")]
        if cands:
            return cands[0].id
        return _defensive_node(net, rng)

    if action is BlueAction.RESET_PASSWORDS:
        cands = [n.id for n in net.nodes.values() if n.owner is Owner.BLUE]
        return rng.choice(cands) if cands else cj.id

    return _defensive_node(net, rng)


def _defensive_node(net, rng) -> str:
    cands = [n.id for n in net.nodes.values()
             if n.owner is Owner.BLUE and n.kind != "internet"]
    return rng.choice(cands) if cands else net.crown_jewel().id
