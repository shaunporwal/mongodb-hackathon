"""Post-game reflection: 1-3 short, reusable lessons for Blue, written to memory."""
from langsmith import traceable

from backend import llm, memory

SYSTEM = """You review a finished turn-based SIMULATED network-defense game from BLUE's side.
Write 1-3 short lessons (max 25 words each) that would help Blue win future games at this level.
Lessons must be concrete and reusable: name signals, actions, nodes, or timing. No generic advice.
Reply with JSON only: {"lessons": ["...", "..."]}"""


def _log_lines(events: list[dict], learner: str = "blue", limit: int = 40) -> str:
    """Event log from the learner's seat: the opponent's undetected moves are marked hidden."""
    lines = []
    for e in events[-limit:]:
        hidden = e["side"] != learner and not e.get("detected")
        seen = f" [unseen by {learner.capitalize()}]" if hidden else ""
        why = f" | why: {e['reason']}" if e.get("reason") else ""
        lines.append(f"T{e['turn']} {e['side']}: {e['text']}{seen}{why}")
    return "\n".join(lines)


@traceable(name="reflect_game")
def reflect(game: dict, events: list[dict], learner: str = "blue",
            system: str = SYSTEM) -> tuple[list, dict]:
    """Write 1-3 lessons from the learner's side. `system` is the reflection prompt;
    pass a Red-perspective prompt when the learner is Red. Returns (lesson_ids, usage)."""
    user = (f"Level {game['level']}. Winner: {game['winner']} ({game.get('win_condition')}) "
            f"after {game['turns']} turns.\nEVENT LOG:\n{_log_lines(events, learner)}")
    try:
        out, usage = llm.chat_json(system, user, kind="move", max_tokens=250)
    except ValueError:
        return [], {"tokens_in": 0, "tokens_out": 0}
    texts = [str(t) for t in (out.get("lessons") or [])][:3]
    ids = memory.add_lessons(texts, game["level"], game["_id"], game["harness_version"],
                             side=learner)
    return ids, usage
