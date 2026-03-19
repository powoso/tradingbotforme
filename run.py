#!/usr/bin/env python3
"""CounterTrade Bot - Start script.

Initializes the database (with optional seed data) and starts the FastAPI server.
"""

import argparse
import os
import sqlite3
import sys
import uvicorn


def seed_database(db_path: str, seed_path: str) -> None:
    """Load seed data into the database."""
    if not os.path.exists(seed_path):
        print(f"Seed file not found: {seed_path}")
        return
    conn = sqlite3.connect(db_path)
    with open(seed_path, "r") as f:
        sql = f.read()
    try:
        conn.executescript(sql)
        conn.commit()
        print("Seed data loaded successfully.")
    except sqlite3.Error as e:
        print(f"Warning: Could not load seed data: {e}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="CounterTrade Bot")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--seed", action="store_true", help="Load seed data")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    # Ensure we're in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    # Initialize DB by importing the module
    sys.path.insert(0, project_root)
    from backend.database import init_db
    init_db()

    if args.seed:
        db_path = os.path.join(project_root, "data", "countertrade.db")
        seed_path = os.path.join(project_root, "data", "seed.sql")
        seed_database(db_path, seed_path)

    print(f"\n  CounterTrade Bot starting on http://{args.host}:{args.port}")
    print("  Frontend dev server: http://localhost:3000\n")

    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
