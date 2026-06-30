CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ─── Users ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT UNIQUE NOT NULL,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  xp            INTEGER DEFAULT 0,
  level         INTEGER DEFAULT 1,
  streak_days   INTEGER DEFAULT 0,
  last_active   DATE,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- ─── Problems ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS problems (
  slug                     TEXT PRIMARY KEY,
  title                    TEXT NOT NULL,
  difficulty               TEXT NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
  tags                     TEXT[],
  platform                 TEXT NOT NULL DEFAULT 'leetcode',
  optimal_time_complexity  TEXT,
  optimal_space_complexity TEXT
);

-- ─── Solves ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS solves (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
  problem_slug        TEXT REFERENCES problems(slug),
  time_taken_seconds  INTEGER DEFAULT 0,
  language            TEXT DEFAULT 'unknown',
  earned_xp           INTEGER DEFAULT 0,
  solved_at           TIMESTAMPTZ DEFAULT now()
);

-- ─── Review Queue (SM-2 spaced repetition) ───────────────────────────
CREATE TABLE IF NOT EXISTS review_queue (
  user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
  problem_slug     TEXT REFERENCES problems(slug),
  ef               FLOAT DEFAULT 2.5,         -- ease factor
  interval_days    INTEGER DEFAULT 1,
  repetitions      INTEGER DEFAULT 0,
  next_review_date DATE DEFAULT CURRENT_DATE,
  updated_at       TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, problem_slug)
);

-- ─── Daily Activity (heatmap source) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_activity (
  user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
  date             DATE NOT NULL,
  problems_solved  INTEGER DEFAULT 0,
  xp_earned        INTEGER DEFAULT 0,
  PRIMARY KEY (user_id, date)
);

-- ─── Journal Entries (RAG-backed notes) ──────────────────────────────
CREATE TABLE IF NOT EXISTS journal_entries (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
  problem_slug TEXT,
  title        TEXT NOT NULL DEFAULT 'Untitled Note',
  reflection   TEXT,
  embedding    VECTOR(1536),
  created_at   TIMESTAMPTZ DEFAULT now()
);

-- ─── Sessions (for auth-service refresh tokens) ──────────────────────
CREATE TABLE IF NOT EXISTS sessions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
  refresh_token TEXT UNIQUE NOT NULL,
  expires_at    TIMESTAMPTZ NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- ─── Indexes ─────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_solves_user_time ON solves(user_id, solved_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_due        ON review_queue(next_review_date, user_id);
CREATE INDEX IF NOT EXISTS idx_activity_user     ON daily_activity(user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_journal_user      ON journal_entries(user_id, created_at DESC);
