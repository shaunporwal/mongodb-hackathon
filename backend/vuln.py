"""Abstract 'vulnerability' model for the simulated game. This is pure board-game math,
NOT security tooling: a node carries a hidden boolean flag and a fixed success
probability. Nothing here maps to any real software, CVE, or technique.

    flaw = Flaw(prob=0.6)         # a made-up weak spot on a node
    flaw.discovered               # False until a probe reveals it (costs a turn)
    flaw.roll(rng, defended=...)  # True/False outcome of a symbolic 'exploit' action

Defense levels raise `mitigation`, which lowers the effective odds; that is the only
lever the game exposes. The learner never changes these numbers — it only chooses which
symbolic action to take, so 'getting better' means better sequencing, not real exploits.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Flaw:
    prob: float = 0.6          # base success chance of the symbolic exploit action
    discovered: bool = False   # has a probe action revealed the flag yet?
    patched: bool = False      # a Blue harden action removes it entirely

    def reveal(self) -> bool:
        """A probe/scan action flips the hidden flag to visible. Returns True the first time."""
        first = not self.discovered
        self.discovered = True
        return first

    def effective_prob(self, mitigation: float = 0.0) -> float:
        """Odds after Blue's defense level. patched -> 0. mitigation in [0,1] scales it down."""
        if self.patched:
            return 0.0
        return max(0.0, self.prob * (1.0 - min(1.0, max(0.0, mitigation))))

    def roll(self, rng, mitigation: float = 0.0) -> bool:
        """Resolve one symbolic 'exploit' attempt against this flaw."""
        return rng.random() < self.effective_prob(mitigation)


# Blue defense levels 1-5 -> how much they blunt a flaw (mirror of the Red curriculum).
# The attacker curriculum climbs against these. Tune freely; these are just game dials.
DEFENSE_MITIGATION = {1: 0.0, 2: 0.15, 3: 0.35, 4: 0.55, 5: 0.75}
