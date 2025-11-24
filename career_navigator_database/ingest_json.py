#!/usr/bin/env python3
"""Optional JSON ingestion for seeding SQLite from backend/data JSON files.

This script is safe to run multiple times. It will:
- Search for a sibling backend workspace default path:
  ../career-path-navigator-41368-41378/career_navigator_backend/data
- Load known JSON sets if found and insert rows without duplication.

Note:
- This is a best-effort helper; it skips files not present.
- It assumes schema.sql has been applied (run init_db.py first).

PySecure-4-Minimal-Standard:
- Validates inputs and handles file errors safely.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from typing import Any, Dict, Iterable, List

DB_NAME = "myapp.db"
DEFAULT_DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "career-path-navigator-41368-41378", "career_navigator_backend", "data")
)

def _safe_load_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: failed to load {path}: {e}")
        return None

def _ensure_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("PRAGMA foreign_keys = ON")
    return conn

def ingest_roles(roles_json: Iterable[Dict[str, Any]], conn: sqlite3.Connection) -> None:
    if not roles_json:
        return
    with conn:
        for r in roles_json:
            name = (r.get("name") or "").strip()
            abbr = (r.get("abbreviation") or None)
            if not name:
                continue
            conn.execute("INSERT OR IGNORE INTO roles(name, abbreviation) VALUES (?,?)", (name, abbr))

def ingest_competencies(defs_json: Iterable[Dict[str, Any]], conn: sqlite3.Connection) -> None:
    if not defs_json:
        return
    with conn:
        for c in defs_json:
            name = (c.get("competency") or "").strip()
            definition = c.get("definition") or None
            if not name:
                continue
            conn.execute("INSERT OR IGNORE INTO competencies(name, definition) VALUES (?,?)", (name, definition))

def ingest_resources(resources_json: Iterable[Dict[str, Any]], conn: sqlite3.Connection) -> None:
    if not resources_json:
        return
    with conn:
        for r in resources_json:
            title = (r.get("title") or "").strip()
            url = r.get("url") or None
            tags = ",".join(r.get("tags", [])) if isinstance(r.get("tags"), list) else (r.get("tags") or None)
            if not title:
                continue
            exists = conn.execute(
                "SELECT 1 FROM resources WHERE title=? AND ifnull(url,'')=ifnull(?,'')",
                (title, url),
            ).fetchone()
            if not exists:
                conn.execute("INSERT INTO resources(title, url, tags) VALUES (?,?,?)", (title, url, tags))

def main() -> None:
    data_dir = os.environ.get("BACKEND_DATA_DIR", DEFAULT_DATA_DIR)
    print(f"Using data directory: {data_dir}")
    if not os.path.isdir(data_dir):
        print("No data directory found. Skipping ingestion.")
        return

    with closing(_ensure_conn()) as conn:
        roles = _safe_load_json(os.path.join(data_dir, "roles.json"))
        comps = _safe_load_json(os.path.join(data_dir, "competencies_definitions.json"))
        resources = _safe_load_json(os.path.join(data_dir, "resources.json"))

        ingest_roles(roles if isinstance(roles, list) else [], conn)
        ingest_competencies(comps if isinstance(comps, list) else [], conn)
        ingest_resources(resources if isinstance(resources, list) else [], conn)

    print("Ingestion complete.")

if __name__ == "__main__":
    main()
