-- =============================================================================
-- PHASE C MIGRATION — Demographic Fairness Evaluation
-- File: docs/migrations/phase_c_fairness_evaluation.sql
-- Safe to run multiple times (idempotent).
-- =============================================================================

-- FA-1 / FA-4: Isolated demographic fairness evaluation storage.
-- Demographic evaluation data is stored exclusively in these dedicated tables
-- and is NEVER joined with candidate assessment scores or recruiter views.

-- 1. FAIRNESS_DATASETS table
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


-- 2. FAIRNESS_AUDITS table
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


-- 3. ROW LEVEL SECURITY (RLS)
ALTER TABLE fairness_datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE fairness_audits   ENABLE ROW LEVEL SECURITY;

-- Only platform administrators may read or create fairness evaluation records
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
-- END PHASE C MIGRATION
-- =============================================================================
