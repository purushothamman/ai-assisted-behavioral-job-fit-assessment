-- =============================================================================
-- PHASE D MIGRATION — Recruiter Oversight & Audit Trails
-- File: docs/migrations/phase_d_recruiter_oversight.sql
-- Safe to run multiple times (idempotent).
-- =============================================================================

-- OV-3 / OV-4: Add recruiter oversight columns to session_alignments
-- Preserves all existing alignment data, scores, and historical snapshots.
ALTER TABLE session_alignments
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reviewed_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS review_action TEXT,
    ADD COLUMN IF NOT EXISTS recruiter_notes TEXT,
    ADD COLUMN IF NOT EXISTS override_score FLOAT;

CREATE INDEX IF NOT EXISTS idx_session_alignments_reviewed_at
    ON session_alignments(reviewed_at);

CREATE INDEX IF NOT EXISTS idx_session_alignments_reviewed_by
    ON session_alignments(reviewed_by);

COMMENT ON COLUMN session_alignments.reviewed_at IS
    'Timestamp when recruiter oversight review was recorded.';
COMMENT ON COLUMN session_alignments.reviewed_by IS
    'FK to profiles.id of the recruiter who conducted the review.';
COMMENT ON COLUMN session_alignments.review_action IS
    'Oversight decision: reviewed, flagged_for_interview, request_reassessment, overridden, completed.';
COMMENT ON COLUMN session_alignments.recruiter_notes IS
    'Qualitative recruiter notes and behavioral observations.';
COMMENT ON COLUMN session_alignments.override_score IS
    'Human oversight override score (optional, preserving original overall_score).';


-- OV-2: Persistent audit_logs table
-- Records assessment reviews, report views, fairness audits, and framework events.
-- Strictly excludes passwords, tokens, API keys, or raw confidential credentials.
CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id    UUID REFERENCES profiles(id) ON DELETE SET NULL,
    actor_role  TEXT NOT NULL DEFAULT 'recruiter',
    action      TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    details     JSONB NOT NULL DEFAULT '{}',
    ip_address  TEXT,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id   ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action     ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_target     ON audit_logs(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);

COMMENT ON TABLE audit_logs IS
    'Immutable audit log tracking recruiter oversight actions, report accesses, '
    'and administrative governance events. Excludes passwords, tokens, and PII.';


-- Row Level Security (RLS) for audit_logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Recruiters and admins can read audit_logs" ON audit_logs;
CREATE POLICY "Recruiters and admins can read audit_logs"
    ON audit_logs FOR SELECT
    TO authenticated
    USING (
        actor_id = auth.uid() OR
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid() AND profiles.role = 'admin'
        )
    );

DROP POLICY IF EXISTS "Authenticated users can insert audit_logs" ON audit_logs;
CREATE POLICY "Authenticated users can insert audit_logs"
    ON audit_logs FOR INSERT
    TO authenticated
    WITH CHECK (
        actor_id = auth.uid() OR
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid() AND profiles.role = 'admin'
        )
    );

-- =============================================================================
-- END PHASE D MIGRATION
-- =============================================================================
