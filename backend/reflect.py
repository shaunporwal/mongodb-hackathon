"""Post-game reflection: 1-3 short, reusable lessons for Blue, written to memory."""
from langsmith import traceable

from backend import llm, memory

SYSTEM = """You review a finished turn-based SIMULATED network-defense game from BLUE's side.
Write 1-3 short lessons (max 25 words each) that would help Blue win future games at this level.
Lessons must be concrete and reusable: name signals, actions, nodes, or timing. No generic advice.
Reply with JSON only: {"lessons": ["...", "..."]}"""


def _log_lines(events: list[dict], limit: int = 40) -> str:
    lines = []
    for e in events[-limit:]:
        seen = "" if e["side"] == "blue" or e.get("detected") else " [unseen by Blue]"
        why = f" | why: {e['reason']}" if e.get("reason") else ""
        lines.append(f"T{e['turn']} {e['side']}: {e['text']}{seen}{why}")
    return "\n".join(lines)


@traceable(name="reflect_game")
def reflect(game: dict, events: list[dict]) -> tuple[list, dict]:
    """Returns (lesson_ids, usage)."""
    user = (f"Level {game['level']}. Winner: {game['winner']} ({game.get('win_condition')}) "
            f"after {game['turns']} turns.\nEVENT LOG:\n{_log_lines(events)}")
    try:
        out, usage = llm.chat_json(SYSTEM, user, kind="move", max_tokens=250)
    except ValueError:
        return [], {"tokens_in": 0, "tokens_out": 0}
    texts = [str(t) for t in (out.get("lessons") or [])][:3]
    ids = memory.add_lessons(texts, game["level"], game["_id"], game["harness_version"])
    return ids, usage
