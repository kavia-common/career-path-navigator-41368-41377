# Career Navigator Database Schema

This folder contains the SQLite schema and helpers for the Career Path Navigator MVP.

Files:
- schema.sql: Authoritative schema (idempotent).
- init_db.py: Initializes myapp.db, applies schema, seeds minimal data, and writes sqlite.env for the visualizer.
- ingest_json.py: Ingests JSON data from the backend data folder and upserts into roles, competencies, role_competencies, role_adjacency, and resources.
- test_db.py: Smoke tests for schema, indices, and foreign key enforcement.

Quickstart:
1) Initialize DB
   python3 init_db.py

2) Ingest JSON from backend datasets (idempotent)
   # The script will default to the sibling backend workspace if present:
   # ../career-path-navigator-41368-41378/career_navigator_backend/data
   # You can also override explicitly:
   BACKEND_DATA_DIR=/home/kavia/workspace/code-generation/career-path-navigator-41368-41378/career_navigator_backend/data python3 ingest_json.py

   On completion, it prints SELECT count(*) for:
   - roles, competencies, role_competencies, role_adjacency, resources
   and writes ingestion_summary.txt with row counts.

3) Run smoke tests
   python3 test_db.py

Viewer:
- Source environment for the simple DB viewer:
  source db_visualizer/sqlite.env

Re-run ingestion later:
- If datasets change, simply run:
  BACKEND_DATA_DIR=/home/kavia/workspace/code-generation/career-path-navigator-41368-41378/career_navigator_backend/data python3 ingest_json.py
- Then refresh the SQLite visualizer and confirm counts match the printed summary.
