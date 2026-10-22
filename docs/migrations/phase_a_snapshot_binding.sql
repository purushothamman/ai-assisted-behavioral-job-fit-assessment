-- =============================================================================
-- PHASE A MIGRATION — Framework Snapshot Binding
-- File: docs/migrations/phase_a_snapshot_binding.sql
-- Safe to run multiple times (idempotent).
-- =============================================================================

-- FS-2: Add framework_version_id to interview_sessions
--       so each assessment session is anchored to the exact frozen
--       behavioral framework that was active when the session was created.
--       Historical reports and scoring will evaluate against this snapshot
--       rather than mutated live dimension/indicator tables.

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
-- END PHASE A MIGRATION
-- =============================================================================
