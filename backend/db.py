"""MongoDB Atlas client, collection handles, ping, and index creation."""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.operations import SearchIndexModel

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
# Tracing is optional: without a LangSmith key, @traceable is a no-op.
if not os.environ.get("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_TRACING"] = "false"

DB_NAME = "redblue"
VECTOR_INDEX = "lessons_vec"
EMBED_DIMS = 1024

VECTOR_INDEX_DEF = {
    "fields": [
        {"type": "vector", "path": "embedding", "numDimensions": EMBED_DIMS, "similarity": "cosine"},
        {"type": "filter", "path": "side"},
        {"type": "filter", "path": "level"},
    ]
}


@lru_cache(maxsize=1)
def client() -> MongoClient:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI is not set (see .env.example)")
    return MongoClient(uri, appname="redblue-harness", serverSelectionTimeoutMS=10000)


def db():
    return client()[DB_NAME]


def networks():
    return db()["networks"]


def games():
    return db()["games"]


def events():
    return db()["events"]


def lessons():
    return db()["lessons"]


def harness_versions():
    return db()["harness_versions"]


def curriculum():
    return db()["curriculum"]


def counters():
    return db()["counters"]


NETWORK_ID = "net1"
ID_PREFIX = {"games": "g_", "lessons": "L_"}


def next_id(kind: str) -> str:
    """Readable sequential id, e.g. next_id("games") -> "g_0042"."""
    doc = counters().find_one_and_update({"_id": kind}, {"$inc": {"seq": 1}},
                                         upsert=True, return_document=ReturnDocument.AFTER)
    return f"{ID_PREFIX[kind]}{doc['seq']:04d}"


def ping() -> bool:
    client().admin.command("ping")
    return True


def ensure_indexes() -> None:
    """Regular indexes plus the Atlas vector search index. Safe to call repeatedly."""
    events().create_index([("game_id", ASCENDING), ("turn", ASCENDING)])
    events().create_index([("ts", DESCENDING)])
    games().create_index([("started_at", DESCENDING)])
    games().create_index([("level", ASCENDING), ("purpose", ASCENDING)])
    harness_versions().create_index([("side", ASCENDING), ("version", ASCENDING)], unique=True)
    lessons().create_index([("level", ASCENDING), ("created_at", DESCENDING)])

    # The collection must exist before a search index can be created on it.
    if "lessons" not in db().list_collection_names():
        db().create_collection("lessons")
    existing = {ix["name"] for ix in lessons().list_search_indexes()}
    if VECTOR_INDEX not in existing:
        lessons().create_search_index(
            SearchIndexModel(definition=VECTOR_INDEX_DEF, name=VECTOR_INDEX, type="vectorSearch")
        )
        print(f"created vector index {VECTOR_INDEX} (takes ~1 min to become queryable)")


if __name__ == "__main__":
    ping()
    print(f"Atlas ping ok; db={DB_NAME}")
    ensure_indexes()
    print("indexes ok:", [ix["name"] for ix in lessons().list_search_indexes()])
