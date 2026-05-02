-- =============================================================================
-- AI-QG: Supabase PostgreSQL Schema
-- Run this in the Supabase SQL Editor to create all required tables.
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- 1. users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email       TEXT UNIQUE,
    display_name TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 2. documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    filename        TEXT NOT NULL,
    file_type       TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'txt')),
    file_size       INTEGER NOT NULL DEFAULT 0,
    storage_path    TEXT,
    raw_text        TEXT,
    processed_text  TEXT,
    status          TEXT NOT NULL DEFAULT 'uploaded'
                        CHECK (status IN ('uploaded', 'processing', 'completed', 'failed')),
    error_message   TEXT,
    upload_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

-- ---------------------------------------------------------------------------
-- 3. generated_questions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS generated_questions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    question_text   TEXT NOT NULL,
    answer          TEXT NOT NULL,
    question_type   TEXT NOT NULL
                        CHECK (question_type IN ('fill_blank', 'wh', 'short_answer', 'mcq')),
    difficulty      TEXT NOT NULL DEFAULT 'medium'
                        CHECK (difficulty IN ('easy', 'medium', 'hard')),
    bloom_taxonomy  TEXT NOT NULL DEFAULT 'remember'
                        CHECK (bloom_taxonomy IN ('remember', 'understand', 'apply')),
    source_sentence TEXT,
    distractors     JSONB DEFAULT '[]'::jsonb,
    options         JSONB DEFAULT '[]'::jsonb,
    correct_index   INTEGER,
    metadata        JSONB DEFAULT '{}'::jsonb,
    is_edited       BOOLEAN NOT NULL DEFAULT FALSE,
    edited_text     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_questions_document_id ON generated_questions(document_id);
CREATE INDEX IF NOT EXISTS idx_questions_type ON generated_questions(question_type);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON generated_questions(difficulty);
CREATE INDEX IF NOT EXISTS idx_questions_bloom ON generated_questions(bloom_taxonomy);

-- ---------------------------------------------------------------------------
-- 4. analytics
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id             UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    total_questions         INTEGER NOT NULL DEFAULT 0,
    type_distribution       JSONB DEFAULT '{}'::jsonb,
    difficulty_distribution JSONB DEFAULT '{}'::jsonb,
    taxonomy_distribution   JSONB DEFAULT '{}'::jsonb,
    processing_time_seconds FLOAT DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_document_id ON analytics(document_id);

-- ---------------------------------------------------------------------------
-- 5. exports
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exports (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    export_type   TEXT NOT NULL CHECK (export_type IN ('pdf', 'csv')),
    file_path     TEXT,
    storage_path  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exports_document_id ON exports(document_id);

-- ---------------------------------------------------------------------------
-- Row Level Security (RLS) — basic open policy for development
-- Tighten these in production with proper auth checks.
-- ---------------------------------------------------------------------------
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE exports ENABLE ROW LEVEL SECURITY;

-- Allow all operations for now (development mode)
CREATE POLICY "Allow all on users" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on documents" ON documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on generated_questions" ON generated_questions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on analytics" ON analytics FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on exports" ON exports FOR ALL USING (true) WITH CHECK (true);
