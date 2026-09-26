"""Post-game reflection: 1-3 short, reusable lessons for the learner side, written to memory."""
from langsmith import traceable

from backend import llm, memory
from backend.prompts import BLUE_REFLECT_SYSTEM as SYSTEM, REFLECT_SYSTEM_FOR


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
            system: str | None = None) -> tuple[list, dict]:
    """Write 1-3 lessons from the learner's side. `system` defaults to that side's
    reflection prompt in backend/prompts.py. Returns (lesson_ids, usage)."""
    system = system or REFLECT_SYSTEM_FOR.get(learner) or SYSTEM
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
