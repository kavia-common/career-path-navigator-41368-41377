# Career Navigator Database Schema

This folder contains the SQLite schema and helpers for the Career Path Navigator MVP.

Files:
- schema.sql: Authoritative schema (idempotent).
- init_db.py: Initializes myapp.db, applies schema, seeds minimal data, and writes sqlite.env for the visualizer.
- ingest_json.py: Optional helper to ingest JSON data from the backend data folder if available.
- test_db.py: Smoke tests for schema, indices, and foreign key enforcement.

Quickstart:
1) Initialize DB
   python3 init_db.py

2) Optional: Ingest JSON from backend
   # env var can override path to data dir; default tries a sibling backend workspace
   BACKEND_DATA_DIR=/path/to/career_navigator_backend/data python3 ingest_json.py

3) Run smoke tests
   python3 test_db.py

Viewer:
- Source environment for the simple DB viewer:
  source db_visualizer/sqlite.env
