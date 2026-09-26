"""Lesson memory: Voyage embeddings stored in Atlas, recalled with $vectorSearch."""
import os
from datetime import datetime, timezone
from functools import lru_cache

import voyageai
from langsmith import traceable

from backend import db

EMBED_MODEL = "voyage-3.5"


@lru_cache(maxsize=1)
def voyage() -> voyageai.Client:
    key = os.environ.get("VOYAGE_API_KEY")
    if not key:
        raise RuntimeError("VOYAGE_API_KEY is not set (see .env.example)")
    return voyageai.Client(api_key=key)


def has_voyage() -> bool:
    return bool(os.environ.get("VOYAGE_API_KEY"))


def embed(texts: list[str], input_type: str) -> list[list[float]]:
    """input_type: 'document' when storing, 'query' when recalling."""
    return voyage().embed(texts, model=EMBED_MODEL, input_type=input_type,
                          output_dimension=db.EMBED_DIMS).embeddings


@traceable(name="memory_add_lessons")
def add_lessons(texts: list[str], level: int, game_id, harness_version: int,
                side: str = "blue") -> list:
    texts = [t.strip() for t in texts if t and t.strip()]
    if not texts:
        return []
    now = datetime.now(timezone.utc)
    # Without a Voyage key, lessons are stored un-embedded and recall falls back to recency.
    vectors = embed(texts, "document") if has_voyage() else [None] * len(texts)
    docs = []
    for t, e in zip(texts, vectors):
        doc = {"_id": db.next_id("lessons"), "side": side, "level": level, "game_id": game_id,
               "harness_version": harness_version, "text": t, "created_at": now}
        if e is not None:
            doc["embedding"] = e
        docs.append(doc)
    return db.lessons().insert_many(docs).inserted_ids


def add_lesson(text: str, level: int, game_id, harness_version: int, side: str = "blue"):
    ids = add_lessons([text], level, game_id, harness_version, side)
    return ids[0] if ids else None


DEFAULT_POLICY = {"k": 3, "filter_by_level": True, "recency_weight": 0.0}


@traceable(name="memory_recall")
def recall(situation_text: str, memory_policy: dict | None, level: int,
           side: str = "blue") -> list[dict]:
    """Top-k lessons for a situation. Returns [{_id, text, level, score}].

    memory_policy: {k, filter_by_level, recency_weight}. recency_weight in [0,1]
    blends vector score with a newest-first rank (0 = pure similarity).
    """
    policy = {**DEFAULT_POLICY, **(memory_policy or {})}
    k = int(policy["k"])
    if k <= 0:
        return []
    filt = {"side": side}
    if policy["filter_by_level"]:
        filt["level"] = level
    if not has_voyage():
        latest = db.lessons().find(filt, {"text": 1, "level": 1}).sort("created_at", -1).limit(k)
        return [{"_id": h["_id"], "text": h["text"], "level": h["level"], "score": None}
                for h in latest]
    pipeline = [
        {"$vectorSearch": {
            "index": db.VECTOR_INDEX, "path": "embedding",
            "queryVector": embed([situation_text], "query")[0],
            "numCandidates": max(50, k * 10), "limit": k * 3, "filter": filt,
        }},
        {"$project": {"text": 1, "level": 1, "created_at": 1,
                      "score": {"$meta": "vectorSearchScore"}}},
    ]
    hits = list(db.lessons().aggregate(pipeline))
    w = float(policy["recency_weight"])
    if w > 0 and hits:
        by_age = sorted(hits, key=lambda h: h["created_at"], reverse=True)
        n = len(by_age)
        recency = {h["_id"]: 1 - i / n for i, h in enumerate(by_age)}
        for h in hits:
            h["score"] = (1 - w) * h["score"] + w * recency[h["_id"]]
        hits.sort(key=lambda h: h["score"], reverse=True)
    return [{"_id": h["_id"], "text": h["text"], "level": h["level"], "score": h["score"]}
            for h in hits[:k]]


if __name__ == "__main__":
    db.ensure_indexes()
    lid = add_lesson("Smoke test lesson: check egress on the database when alerts spike.",
                     level=0, game_id=None, harness_version=-1)
    print("inserted", lid)
    print("recall (index may need ~1 min after creation):",
          [h["text"] for h in recall("database outbound spike", {"k": 2}, level=0)])
    db.lessons().delete_one({"_id": lid})
