"""Blue's harness: turn a harness version + observation + recalled lessons into one legal,
guardrail-respecting action. Touches the world only through an Adapter.
"""
from __future__ import annotations

import json
import random
import re

from langsmith import traceable

from backend import llm, memory

from backend.prompts import BLUE_SYSTEM as SYSTEM  # noqa: F401  default (Blue) system prompt

USER = """TURN {turn} (level {level})
SIGNALS: {signals}
OBSERVATION: {obs}
YOUR LAST ACTIONS: {history}
LESSONS FROM PAST GAMES:
{lessons}
LEGAL ACTIONS (action: targets): {legal}{error}"""


# ---------- signals ----------

def _signal_type(sig: str) -> str:
    return sig.split(":", 1)[0]


def _signal_score(sig: str) -> float | None:
    """Signals may carry a trailing ':<score>'; returns it or None."""
    tail = sig.rsplit(":", 1)[-1]
    try:
        return float(tail)
    except ValueError:
        return None


def filter_signals(signals: list[str], harness: dict) -> list[str]:
    """Drop scored signals under the harness threshold, then order by signal priority."""
    thresholds = harness.get("thresholds") or {}
    priority = harness.get("signals") or []
    kept = []
    for s in signals:
        score, t = _signal_score(s), _signal_type(s)
        if score is not None and score < thresholds.get(t, 0):
            continue
        kept.append(s)
    rank = {t: i for i, t in enumerate(priority)}
    return sorted(kept, key=lambda s: rank.get(_signal_type(s), len(rank)))


# ---------- guardrails ----------

NEVER_RE = re.compile(r"^never (\w+)(?: (\w+))?", re.I)
AFTER_RE = re.compile(r"^after (\w+)\b.*?\balso (\w+)", re.I)


def guardrail_violation(action: str, target: str, guardrails: list[str],
                        history: list[dict]) -> str | None:
    """Return the violated guardrail text, or None. Supported machine-checkable forms:
    'never <action> [<target>]' and 'after <action_a> ..., also <action_b>' (next turn, same
    target). Other guardrail text is advisory and only goes into the prompt."""
    last = history[-1] if history else None
    for g in guardrails or []:
        m = NEVER_RE.match(g.strip())
        if m and m.group(1) == action and (m.group(2) is None or m.group(2) == target):
            return g
        m = AFTER_RE.match(g.strip())
        if m and last and last["action"] == m.group(1):
            if (action, target) != (m.group(2), last["target"]):
                return g
    return None


def legal_map(legal: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for la in legal:
        out.setdefault(la["action"], []).append(la["target"])
    return out


def is_legal(action: str, target: str, legal: list[dict]) -> bool:
    return any(la["action"] == action and la["target"] == target for la in legal)


def fallback(legal: list[dict], guardrails: list[str], history: list[dict],
             signals: list[str]) -> dict:
    """Safe default: scan the node named in the strongest signal, else any allowed scan,
    else the first allowed action."""
    ok = [la for la in legal if not guardrail_violation(la["action"], la["target"], guardrails, history)]
    for s in signals:
        node = s.split("@", 1)[-1].split(":", 1)[0] if "@" in s else None
        for la in ok:
            if la["action"] == "scan" and la["target"] == node:
                return la
    scans = [la for la in ok if la["action"] == "scan"]
    return (scans or ok or legal)[0]


# ---------- prompt + choice ----------

def build_prompt(harness: dict, obs: dict, signals: list[str], lessons: list[dict],
                 legal: list[dict], history: list[dict], level: int, error: str = "",
                 action_help: dict | None = None, system_template: str = SYSTEM) -> tuple[str, str]:
    system = system_template.format(
        actions="\n".join(f"- {a}: {d}" for a, d in (action_help or {}).items()) or "- see legal actions",
        playbook=harness["playbook"],
        guardrails="\n".join(f"- {g}" for g in harness.get("guardrails") or []) or "- none",
        signals=", ".join(harness.get("signals") or []),
        thresholds=json.dumps(harness.get("thresholds") or {}),
    )
    extra = {k: v for k, v in obs.items() if k not in ("signals", "turn")}
    user = USER.format(
        turn=obs.get("turn"), level=level,
        signals=", ".join(signals) or "none",
        obs=json.dumps(extra, separators=(",", ":")) if extra else "none",
        history=", ".join(f"{h['action']}({h['target']})" for h in history[-3:]) or "none",
        lessons="\n".join(f"- {l['text']}" for l in lessons) or "- none",
        legal=json.dumps(legal_map(legal), separators=(",", ":")),
        error=f"\nYOUR PREVIOUS ANSWER WAS REJECTED: {error}. Pick again." if error else "",
    )
    return system, user


def situation_text(signals: list[str], level: int) -> str:
    return f"level {level}; signals: " + ("; ".join(signals) if signals else "quiet turn, no signals")


@traceable(name="choose_action")
def choose_action(adapter, harness: dict, level: int, memory_enabled: bool,
                  history: list[dict], side: str = "blue") -> dict:
    """One learner decision (Blue by default; pass side='red' for the attacker learner).
    Returns {action, target, reason, recalled, guardrail_blocked, signals_seen,
    tokens_in, tokens_out, prompt}."""
    from backend.prompts import system_for
    system_template = system_for(side)
    obs = adapter.observe()
    legal = adapter.legal_actions()
    action_help = adapter.describe_actions()
    signals = filter_signals(obs.get("signals") or [], harness)
    guardrails = harness.get("guardrails") or []
    lessons = memory.recall(situation_text(signals, level), harness.get("memory_policy"),
                            level, side=side) if memory_enabled else []

    tokens_in = tokens_out = 0
    blocked, error, prompt = None, "", None
    for _ in range(2):  # first try + one retry
        system, user = build_prompt(harness, obs, signals, lessons, legal, history, level, error,
                                    action_help, system_template)
        prompt = {"system": system, "user": user}
        try:
            out, usage = llm.chat_json(system, user, kind="move", max_tokens=150)
        except ValueError as e:
            error = str(e)[:120]
            continue
        tokens_in += usage["tokens_in"]
        tokens_out += usage["tokens_out"]
        action, target = str(out.get("action", "")), str(out.get("target", ""))
        if not is_legal(action, target, legal):
            error = f"{action}({target}) is not a legal action"
            continue
        rule = guardrail_violation(action, target, guardrails, history)
        if rule:
            blocked = f"{action}({target}) blocked: guardrail '{rule}'"
            error = blocked
            continue
        return {"action": action, "target": target, "reason": out.get("reason"),
                "recalled": [l["_id"] for l in lessons], "guardrail_blocked": blocked,
                "signals_seen": signals, "tokens_in": tokens_in, "tokens_out": tokens_out,
                "prompt": prompt}

    fb = fallback(legal, guardrails, history, signals)
    return {"action": fb["action"], "target": fb["target"],
            "reason": f"fallback after rejected answers ({error})",
            "recalled": [l["_id"] for l in lessons], "guardrail_blocked": blocked,
            "signals_seen": signals, "tokens_in": tokens_in, "tokens_out": tokens_out,
            "prompt": prompt}


def choose_random(adapter, rng: random.Random) -> dict:
    obs = adapter.observe()
    la = rng.choice(adapter.legal_actions())
    return {"action": la["action"], "target": la["target"], "reason": "random baseline",
            "recalled": [], "guardrail_blocked": None, "signals_seen": obs.get("signals") or [],
            "tokens_in": 0, "tokens_out": 0, "prompt": None}
