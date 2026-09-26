"""One-shot Atlas setup: verify the connection, create indexes, seed the config.

    python -m persistence.bootstrap_atlas

Run this once on your laptop after filling in .env. Safe to re-run.
"""
from __future__ import annotations

from .store import AtlasStore


def main() -> None:
    print("Connecting to MongoDB Atlas...")
    store = AtlasStore()
    store.ping()
    print(f"  connected. database = {store.db_name!r}")

    print("Creating indexes...")
    store.create_indexes()

    print("Seeding default network config...")
    store.ensure_config()

    stats = store.stats()
    print("Done. Current document counts:")
    for k, v in stats.items():
        print(f"  {k:12} {v}")
    print("\nAtlas is ready. Train with:  python train.py --episodes 5000 --atlas")


if __name__ == "__main__":
    main()
