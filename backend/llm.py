"""OpenRouter chat wrapper: one JSON-mode call, returns parsed dict + token usage."""
import json
import os
from functools import lru_cache

from langsmith import traceable
from openai import OpenAI

from backend import db  # noqa: F401  (loads .env)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MOVE_MODEL = "anthropic/claude-haiku-4.5"
DEFAULT_EVOLVE_MODEL = "anthropic/claude-sonnet-5"


@lru_cache(maxsize=1)
def client() -> OpenAI:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set (see .env.example)")
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)


def model(kind: str) -> str:
    """kind: 'move' (cheap/fast) or 'evolve' (stronger)."""
    if kind == "move":
        return os.environ.get("MOVE_MODEL") or DEFAULT_MOVE_MODEL
    return os.environ.get("EVOLVE_MODEL") or DEFAULT_EVOLVE_MODEL


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


@traceable(name="llm_json_call")
def chat_json(system: str, user: str, kind: str = "move", max_tokens: int = 400,
              temperature: float = 0.3) -> tuple[dict, dict]:
    """Returns (parsed_json, {"tokens_in", "tokens_out"}). Raises ValueError on unparseable output."""
    resp = client().chat.completions.create(
        model=model(kind),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        temperature=temperature,
    )
    usage = {
        "tokens_in": getattr(resp.usage, "prompt_tokens", 0) or 0,
        "tokens_out": getattr(resp.usage, "completion_tokens", 0) or 0,
    }
    content = resp.choices[0].message.content or ""
    try:
        return _parse_json(content), usage
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"model returned non-JSON: {content[:200]!r}") from e


if __name__ == "__main__":
    out, usage = chat_json("Reply with JSON only.", 'Return {"ok": true}.', max_tokens=20)
    print(out, usage)
