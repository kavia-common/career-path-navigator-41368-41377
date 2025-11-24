-- Career Navigator Database Schema (SQLite)
-- Idempotent: use IF NOT EXISTS and separate index creation

PRAGMA foreign_keys = ON;

-- Users and authentication (basic MVP, no passwords stored here)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Roles catalog (e.g., CA, CTO, CIO...)
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    abbreviation TEXT UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Competencies taxonomy
CREATE TABLE IF NOT EXISTS competencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    definition TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Role to Competency matrix with expected level (e.g., "P", "A", "Au")
CREATE TABLE IF NOT EXISTS role_competencies (
    role_id INTEGER NOT NULL,
    competency_id INTEGER NOT NULL,
    expected_level TEXT NOT NULL,
    PRIMARY KEY (role_id, competency_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (competency_id) REFERENCES competencies(id) ON DELETE CASCADE
);

-- Role adjacency; overlap percentage between roles (0-100)
CREATE TABLE IF NOT EXISTS role_adjacency (
    from_role_id INTEGER NOT NULL,
    to_role_id INTEGER NOT NULL,
    overlap_pct REAL NOT NULL CHECK (overlap_pct >= 0 AND overlap_pct <= 100),
    PRIMARY KEY (from_role_id, to_role_id),
    FOREIGN KEY (from_role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (to_role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- Resources library (learning/reference items)
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT,
    tags TEXT, -- comma-separated tags/competencies for MVP
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Job applications per user
CREATE TABLE IF NOT EXISTS job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User progress in competencies
CREATE TABLE IF NOT EXISTS user_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    competency_id INTEGER NOT NULL,
    level TEXT NOT NULL,
    evidence_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (competency_id) REFERENCES competencies(id) ON DELETE CASCADE
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);
CREATE INDEX IF NOT EXISTS idx_competencies_name ON competencies(name);
CREATE INDEX IF NOT EXISTS idx_role_comp_role ON role_competencies(role_id);
CREATE INDEX IF NOT EXISTS idx_role_comp_comp ON role_competencies(competency_id);
CREATE INDEX IF NOT EXISTS idx_role_adj_from ON role_adjacency(from_role_id);
CREATE INDEX IF NOT EXISTS idx_role_adj_to ON role_adjacency(to_role_id);
CREATE INDEX IF NOT EXISTS idx_resources_title ON resources(title);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON job_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_user ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_comp ON user_progress(competency_id);
