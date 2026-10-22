-- =============================================================================
-- CONSOLIDATED SQL MIGRATION FOR PHASES A, B, AND C
-- File: docs/migrations/all_phases_a_b_c_consolidated.sql
-- 
-- Instructions:
-- 1. Open your Supabase Dashboard: https://supabase.com/dashboard
-- 2. Select your project and navigate to the "SQL Editor" on the left menu.
-- 3. Click "New Query", paste this entire script, and click "Run".
-- 
-- Idempotent: Safe to run multiple times without causing errors or data loss.
-- =============================================================================

-- =============================================================================
-- PHASE A: Framework Snapshot Binding (FS-1 to FS-4)
-- Pins assessment sessions to the frozen behavioral framework version active
-- at creation time for historic reproducibility.
-- =============================================================================

ALTER TABLE interview_sessions
    ADD COLUMN IF NOT EXISTS framework_version_id UUID
        REFERENCES framework_versions(id)
        ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_interview_sessions_framework_version_id
    ON interview_sessions(framework_version_id);

COMMENT ON COLUMN interview_sessions.framework_version_id IS
    'FK to framework_versions.id — pinned at session creation time (Phase A). '
    'NULL for sessions created before Phase A migration or when no active '
    'framework version existed at creation time. Scoring service uses this '
    'to load the frozen dimensions_snapshot for historical reproducibility.';


-- =============================================================================
-- PHASE B: Evidence-Based Scoring Explanations (ES-1 to ES-3)
-- Note: Zero DDL changes required.
-- Phase B stores per-sentence evidence strings inside the existing JSONB column:
--   response_scores.evidence -> array of {"indicator_name", "similarity", "score", "evidence_text"}
-- PostgreSQL / Supabase JSONB natively accommodates this additive attribute.
-- =============================================================================


-- =============================================================================
-- PHASE C: Demographic Fairness Evaluation (FA-1 to FA-5)
-- Creates dedicated, quarantined evaluation storage for demographic parity difference (DPD),
-- equal opportunity difference (EOD), and subgroup recall audits.
-- Strictly isolated from candidate scoring and recruiter decision flows.
-- =============================================================================

-- 1. FAIRNESS_DATASETS Table
CREATE TABLE IF NOT EXISTS fairness_datasets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    description         TEXT,
    sensitive_attribute TEXT NOT NULL,
    reference_group     TEXT,
    score_threshold     FLOAT NOT NULL DEFAULT 70.0,
    record_count        INT NOT NULL DEFAULT 0,
    groups              JSONB NOT NULL DEFAULT '[]',
    has_ground_truth    BOOLEAN NOT NULL DEFAULT FALSE,
    records             JSONB NOT NULL DEFAULT '[]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          UUID REFERENCES profiles(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_fairness_datasets_created_at 
    ON fairness_datasets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fairness_datasets_sensitive_attr 
    ON fairness_datasets(sensitive_attribute);

COMMENT ON TABLE fairness_datasets IS
    'Controlled demographic evaluation datasets for algorithmic bias audits (Phase C). '
    'Quarantined for administrator evaluation only. Contains no live candidate identity joins.';


-- 2. FAIRNESS_AUDITS Table
CREATE TABLE IF NOT EXISTS fairness_audits (
    id                            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id                    UUID REFERENCES fairness_datasets(id) ON DELETE SET NULL,
    dataset_name                  TEXT NOT NULL,
    sensitive_attribute           TEXT NOT NULL,
    reference_group               TEXT NOT NULL,
    total_samples                 INT NOT NULL,
    evaluated_threshold           FLOAT NOT NULL,
    has_ground_truth              BOOLEAN NOT NULL,
    demographic_parity_difference FLOAT,
    equal_opportunity_difference  FLOAT,
    subgroup_metrics              JSONB NOT NULL DEFAULT '[]',
    warnings                      JSONB NOT NULL DEFAULT '[]',
    limitations                   JSONB NOT NULL DEFAULT '[]',
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by                    UUID REFERENCES profiles(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_fairness_audits_dataset_id 
    ON fairness_audits(dataset_id);
CREATE INDEX IF NOT EXISTS idx_fairness_audits_created_at 
    ON fairness_audits(created_at DESC);

COMMENT ON TABLE fairness_audits IS
    'Demographic fairness audit reports containing DPD, EOD, Subgroup Recall, '
    'small-sample warnings, and statistical limitation notes (Phase C).';


-- 3. Row Level Security (RLS) Policies
ALTER TABLE fairness_datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE fairness_audits   ENABLE ROW LEVEL SECURITY;

-- Restrict access to authenticated platform administrators only
DROP POLICY IF EXISTS "Admins can manage fairness_datasets" ON fairness_datasets;
CREATE POLICY "Admins can manage fairness_datasets"
    ON fairness_datasets
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid() AND profiles.role = 'admin'
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid() AND profiles.role = 'admin'
        )
    );

DROP POLICY IF EXISTS "Admins can manage fairness_audits" ON fairness_audits;
CREATE POLICY "Admins can manage fairness_audits"
    ON fairness_audits
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid() AND profiles.role = 'admin'
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid() AND profiles.role = 'admin'
        )
    );

-- =============================================================================
-- END CONSOLIDATED MIGRATION
-- =============================================================================
