-- =============================================================================
-- AI-Assisted Behavioral Job-Fit Assessment
-- Supabase PostgreSQL Schema  --  Phase 1
--
-- Apply this via: Supabase Dashboard > SQL Editor > paste and run
-- Or via Supabase CLI: supabase db push
--
-- Tables created in dependency order.
-- All tables have RLS enabled; policies are at the bottom of this file.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- EXTENSIONS
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ---------------------------------------------------------------------------
-- PROFILES
-- Linked 1:1 with Supabase auth.users
-- Created automatically by a trigger on auth.users INSERT
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'recruiter'
                    CHECK (role IN ('recruiter', 'admin')),
    full_name   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE profiles IS 'One row per Supabase Auth user. Auto-created by trigger.';


-- ---------------------------------------------------------------------------
-- Trigger: auto-create profile row when a new auth user signs up
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, role)
    VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'role', 'recruiter'))
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ---------------------------------------------------------------------------
-- BEHAVIORAL DIMENSIONS
-- Seeded once; not user-created.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS behavioral_dimensions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE behavioral_dimensions IS 'The six core behavioral dimensions. Seeded; not user-editable.';


-- ---------------------------------------------------------------------------
-- BEHAVIORAL INDICATORS
-- Child rows of behavioral_dimensions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS behavioral_indicators (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dimension_id      UUID NOT NULL REFERENCES behavioral_dimensions(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    description       TEXT,
    example_behaviors TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (dimension_id, name)
);

COMMENT ON TABLE behavioral_indicators IS 'Observable indicators within each behavioral dimension.';


-- ---------------------------------------------------------------------------
-- JOBS
-- Created by recruiters
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recruiter_id     UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    title            TEXT NOT NULL CHECK (char_length(title) BETWEEN 2 AND 200),
    description      TEXT,
    responsibilities TEXT,
    requirements     TEXT,
    status           TEXT NOT NULL DEFAULT 'draft'
                         CHECK (status IN ('draft', 'analyzed', 'active', 'closed')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_recruiter_id ON jobs(recruiter_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status       ON jobs(status);

COMMENT ON TABLE jobs IS 'Job listings created by recruiters. Status flows: draft -> analyzed -> active -> closed.';


-- Auto-update updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ---------------------------------------------------------------------------
-- JOB REQUIREMENTS
-- AI-extracted behavioral requirements, reviewed/confirmed by recruiter
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_requirements (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id       UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    dimension_id UUID NOT NULL REFERENCES behavioral_dimensions(id),
    importance   INT  NOT NULL CHECK (importance BETWEEN 0 AND 100),
    reason       TEXT,
    confirmed    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (job_id, dimension_id)
);

CREATE INDEX IF NOT EXISTS idx_job_requirements_job_id ON job_requirements(job_id);

COMMENT ON TABLE job_requirements IS 'Per-dimension importance weights extracted by Groq, confirmed by recruiter.';


-- ---------------------------------------------------------------------------
-- QUESTIONS
-- Generated by Groq; editable by recruiter
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id        UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    dimension_id  UUID REFERENCES behavioral_dimensions(id),
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL DEFAULT 'behavioral'
                      CHECK (question_type IN ('behavioral', 'situational', 'scenario')),
    difficulty    TEXT NOT NULL DEFAULT 'medium'
                      CHECK (difficulty IN ('easy', 'medium', 'hard')),
    indicators    JSONB,       -- array of indicator names this question targets
    source        TEXT NOT NULL DEFAULT 'ai' CHECK (source IN ('ai', 'manual')),
    status        TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'archived')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_questions_job_id ON questions(job_id);

COMMENT ON TABLE questions IS 'Interview questions generated by Groq or added manually. Recruiter approves before use.';


-- ---------------------------------------------------------------------------
-- ASSESSMENTS
-- Sent to candidates via a unique token link
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id       UUID NOT NULL REFERENCES jobs(id),
    recruiter_id UUID NOT NULL REFERENCES profiles(id),
    token        TEXT NOT NULL UNIQUE DEFAULT gen_random_uuid()::TEXT,
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'in_progress', 'submitted', 'processed', 'reviewed')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_assessments_job_id       ON assessments(job_id);
CREATE INDEX IF NOT EXISTS idx_assessments_recruiter_id ON assessments(recruiter_id);
CREATE INDEX IF NOT EXISTS idx_assessments_token        ON assessments(token);

COMMENT ON TABLE assessments IS 'One assessment per candidate invite. Accessed by candidates via token (no login).';


-- ---------------------------------------------------------------------------
-- ASSESSMENT_QUESTIONS
-- Junction: which questions are in an assessment
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessment_questions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    question_id   UUID NOT NULL REFERENCES questions(id),
    order_index   INT NOT NULL DEFAULT 0,

    UNIQUE (assessment_id, question_id)
);

COMMENT ON TABLE assessment_questions IS 'Ordered list of questions included in each assessment.';


-- ---------------------------------------------------------------------------
-- CANDIDATES
-- Minimal PII: only name + email
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidates (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    name          TEXT,
    email         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_candidates_assessment_id ON candidates(assessment_id);

COMMENT ON TABLE candidates IS 'Candidate contact info. Linked to a single assessment.';


-- ---------------------------------------------------------------------------
-- RESPONSES
-- Raw candidate answers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS responses (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    question_id   UUID NOT NULL REFERENCES questions(id),
    candidate_id  UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    response_text TEXT NOT NULL,
    word_count    INT,
    submitted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (assessment_id, question_id, candidate_id)
);

CREATE INDEX IF NOT EXISTS idx_responses_assessment_id ON responses(assessment_id);

COMMENT ON TABLE responses IS 'Raw text responses submitted by candidates.';


-- ---------------------------------------------------------------------------
-- RESPONSE_ANALYSIS
-- NLP + Groq analysis output for each response (Phase 7+)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS response_analysis (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id          UUID NOT NULL REFERENCES responses(id) ON DELETE CASCADE,
    dimension_id         UUID REFERENCES behavioral_dimensions(id),
    groq_evidence        JSONB,
    positive_indicators  JSONB,
    missing_indicators   JSONB,
    similarity_scores    JSONB,
    confidence           FLOAT CHECK (confidence BETWEEN 0 AND 1),
    analyzed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_response_analysis_response_id ON response_analysis(response_id);


-- ---------------------------------------------------------------------------
-- BEHAVIORAL_SCORES
-- Dimension-level scores per candidate/assessment (Phase 8+)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS behavioral_scores (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id    UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    dimension_id     UUID NOT NULL REFERENCES behavioral_dimensions(id),
    raw_score        FLOAT CHECK (raw_score BETWEEN 0 AND 100),
    normalized_score FLOAT CHECK (normalized_score BETWEEN 0 AND 100),
    evidence_count   INT DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (assessment_id, dimension_id)
);


-- ---------------------------------------------------------------------------
-- EVIDENCE
-- Individual evidence items linked to responses and indicators
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id        UUID NOT NULL REFERENCES responses(id) ON DELETE CASCADE,
    dimension_id       UUID REFERENCES behavioral_dimensions(id),
    indicator_id       UUID REFERENCES behavioral_indicators(id),
    evidence_text      TEXT,
    score_contribution FLOAT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_response_id ON evidence(response_id);


-- ---------------------------------------------------------------------------
-- ASSESSMENT_REPORTS
-- Final explainable report per assessment (Phase 8+)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assessment_reports (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id     UUID UNIQUE NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    overall_alignment FLOAT CHECK (overall_alignment BETWEEN 0 AND 100),
    dimension_scores  JSONB,
    strengths         JSONB,
    areas_for_review  JSONB,
    narrative         TEXT,
    generated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ---------------------------------------------------------------------------
-- RECRUITER_NOTES
-- Notes and final decision added by the recruiter
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recruiter_notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id   UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    recruiter_id    UUID NOT NULL REFERENCES profiles(id),
    note_text       TEXT,
    final_decision  TEXT CHECK (final_decision IN ('proceed', 'reject', 'hold')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recruiter_notes_assessment_id ON recruiter_notes(assessment_id);


-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE profiles           ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs               ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_requirements   ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions          ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments        ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidates         ENABLE ROW LEVEL SECURITY;
ALTER TABLE responses          ENABLE ROW LEVEL SECURITY;
ALTER TABLE response_analysis  ENABLE ROW LEVEL SECURITY;
ALTER TABLE behavioral_scores  ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence           ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE recruiter_notes    ENABLE ROW LEVEL SECURITY;

-- behavioral_dimensions and behavioral_indicators are read-only public seed data
ALTER TABLE behavioral_dimensions ENABLE ROW LEVEL SECURITY;
ALTER TABLE behavioral_indicators ENABLE ROW LEVEL SECURITY;


-- ── profiles ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "profiles: own row only" ON profiles;
CREATE POLICY "profiles: own row only" ON profiles
    FOR ALL USING (auth.uid() = id);


-- ── behavioral_dimensions (public read; no user writes) ────────────────────────
DROP POLICY IF EXISTS "dimensions: public read" ON behavioral_dimensions;
CREATE POLICY "dimensions: public read" ON behavioral_dimensions
    FOR SELECT USING (TRUE);

DROP POLICY IF EXISTS "indicators: public read" ON behavioral_indicators;
CREATE POLICY "indicators: public read" ON behavioral_indicators
    FOR SELECT USING (TRUE);


-- ── jobs ──────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "jobs: recruiter owns" ON jobs;
CREATE POLICY "jobs: recruiter owns" ON jobs
    FOR ALL USING (auth.uid() = recruiter_id);


-- ── job_requirements ──────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "job_requirements: via own jobs" ON job_requirements;
CREATE POLICY "job_requirements: via own jobs" ON job_requirements
    FOR ALL USING (
        job_id IN (SELECT id FROM jobs WHERE recruiter_id = auth.uid())
    );


-- ── questions ─────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "questions: via own jobs" ON questions;
CREATE POLICY "questions: via own jobs" ON questions
    FOR ALL USING (
        job_id IN (SELECT id FROM jobs WHERE recruiter_id = auth.uid())
    );


-- ── assessments ───────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "assessments: recruiter owns" ON assessments;
CREATE POLICY "assessments: recruiter owns" ON assessments
    FOR ALL USING (auth.uid() = recruiter_id);

-- Candidates access via token — handled in application layer (service role key)


-- ── assessment_questions ──────────────────────────────────────────────────────
DROP POLICY IF EXISTS "assessment_questions: via own assessments" ON assessment_questions;
CREATE POLICY "assessment_questions: via own assessments" ON assessment_questions
    FOR ALL USING (
        assessment_id IN (SELECT id FROM assessments WHERE recruiter_id = auth.uid())
    );


-- ── candidates ────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "candidates: via own assessments" ON candidates;
CREATE POLICY "candidates: via own assessments" ON candidates
    FOR ALL USING (
        assessment_id IN (SELECT id FROM assessments WHERE recruiter_id = auth.uid())
    );


-- ── responses ─────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "responses: via own assessments" ON responses;
CREATE POLICY "responses: via own assessments" ON responses
    FOR ALL USING (
        assessment_id IN (SELECT id FROM assessments WHERE recruiter_id = auth.uid())
    );


-- ── response_analysis ─────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "response_analysis: via own responses" ON response_analysis;
CREATE POLICY "response_analysis: via own responses" ON response_analysis
    FOR ALL USING (
        response_id IN (
            SELECT r.id FROM responses r
            JOIN assessments a ON a.id = r.assessment_id
            WHERE a.recruiter_id = auth.uid()
        )
    );


-- ── behavioral_scores ─────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "behavioral_scores: via own assessments" ON behavioral_scores;
CREATE POLICY "behavioral_scores: via own assessments" ON behavioral_scores
    FOR ALL USING (
        assessment_id IN (SELECT id FROM assessments WHERE recruiter_id = auth.uid())
    );


-- ── evidence ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "evidence: via own responses" ON evidence;
CREATE POLICY "evidence: via own responses" ON evidence
    FOR ALL USING (
        response_id IN (
            SELECT r.id FROM responses r
            JOIN assessments a ON a.id = r.assessment_id
            WHERE a.recruiter_id = auth.uid()
        )
    );


-- ── assessment_reports ────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "reports: via own assessments" ON assessment_reports;
CREATE POLICY "reports: via own assessments" ON assessment_reports
    FOR ALL USING (
        assessment_id IN (SELECT id FROM assessments WHERE recruiter_id = auth.uid())
    );


-- ── recruiter_notes ───────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "notes: own recruiter only" ON recruiter_notes;
CREATE POLICY "notes: own recruiter only" ON recruiter_notes
    FOR ALL USING (auth.uid() = recruiter_id);


-- =============================================================================
-- SEED DATA — Behavioral Dimensions + Indicators
-- =============================================================================

INSERT INTO behavioral_dimensions (name, description) VALUES
    ('communication',     'Ability to clearly convey information and actively listen'),
    ('teamwork',          'Capacity to collaborate effectively and support team goals'),
    ('adaptability',      'Flexibility in handling change and learning new processes'),
    ('decision_making',   'Ability to evaluate information and make sound decisions'),
    ('leadership',        'Capacity to guide, delegate, and motivate others'),
    ('stress_management', 'Job-related ability to manage competing demands and work pressure')
ON CONFLICT (name) DO NOTHING;


-- Communication indicators
WITH dim AS (SELECT id FROM behavioral_dimensions WHERE name = 'communication')
INSERT INTO behavioral_indicators (dimension_id, name, description) VALUES
    ((SELECT id FROM dim), 'clarity',               'Expresses ideas clearly and concisely'),
    ((SELECT id FROM dim), 'active_listening',      'Demonstrates attentiveness and understanding'),
    ((SELECT id FROM dim), 'information_sharing',   'Proactively shares relevant information'),
    ((SELECT id FROM dim), 'conflict_communication','Addresses disagreements constructively')
ON CONFLICT (dimension_id, name) DO NOTHING;

-- Teamwork indicators
WITH dim AS (SELECT id FROM behavioral_dimensions WHERE name = 'teamwork')
INSERT INTO behavioral_indicators (dimension_id, name, description) VALUES
    ((SELECT id FROM dim), 'collaboration',      'Works cooperatively toward shared goals'),
    ((SELECT id FROM dim), 'responsibility',     'Takes ownership of team tasks'),
    ((SELECT id FROM dim), 'conflict_resolution','Resolves team conflicts constructively'),
    ((SELECT id FROM dim), 'supportiveness',     'Helps teammates and shares workload')
ON CONFLICT (dimension_id, name) DO NOTHING;

-- Adaptability indicators
WITH dim AS (SELECT id FROM behavioral_dimensions WHERE name = 'adaptability')
INSERT INTO behavioral_indicators (dimension_id, name, description) VALUES
    ((SELECT id FROM dim), 'flexibility',         'Adjusts approach when circumstances change'),
    ((SELECT id FROM dim), 'handling_change',     'Responds positively to organisational change'),
    ((SELECT id FROM dim), 'alternative_planning','Develops backup plans when needed'),
    ((SELECT id FROM dim), 'learning_new_processes','Quickly adopts new tools or workflows')
ON CONFLICT (dimension_id, name) DO NOTHING;

-- Decision Making indicators
WITH dim AS (SELECT id FROM behavioral_dimensions WHERE name = 'decision_making')
INSERT INTO behavioral_indicators (dimension_id, name, description) VALUES
    ((SELECT id FROM dim), 'information_evaluation','Gathers and evaluates relevant data'),
    ((SELECT id FROM dim), 'risk_consideration',    'Considers risks before deciding'),
    ((SELECT id FROM dim), 'prioritization',        'Identifies and focuses on high-impact tasks'),
    ((SELECT id FROM dim), 'action_taking',         'Acts decisively when needed')
ON CONFLICT (dimension_id, name) DO NOTHING;

-- Leadership indicators
WITH dim AS (SELECT id FROM behavioral_dimensions WHERE name = 'leadership')
INSERT INTO behavioral_indicators (dimension_id, name, description) VALUES
    ((SELECT id FROM dim), 'responsibility',  'Takes responsibility for team outcomes'),
    ((SELECT id FROM dim), 'delegation',      'Effectively assigns tasks to the right people'),
    ((SELECT id FROM dim), 'accountability',  'Holds self and others accountable'),
    ((SELECT id FROM dim), 'coordination',    'Aligns team efforts toward shared goals'),
    ((SELECT id FROM dim), 'motivation',      'Inspires and motivates team members')
ON CONFLICT (dimension_id, name) DO NOTHING;

-- Stress Management indicators (job-related only — no psychological inference)
WITH dim AS (SELECT id FROM behavioral_dimensions WHERE name = 'stress_management')
INSERT INTO behavioral_indicators (dimension_id, name, description) VALUES
    ((SELECT id FROM dim), 'prioritization',        'Identifies urgent vs important tasks under pressure'),
    ((SELECT id FROM dim), 'competing_demands',     'Manages multiple competing deadlines'),
    ((SELECT id FROM dim), 'task_focus',            'Maintains quality output under time pressure'),
    ((SELECT id FROM dim), 'organizing_urgent_work','Organises and executes urgent tasks effectively')
ON CONFLICT (dimension_id, name) DO NOTHING;


-- =============================================================================
-- PHASE 4 -- INTERVIEW QUESTIONS
-- =============================================================================

-- ---------------------------------------------------------------------------
-- INTERVIEW QUESTIONS
-- Generated by Groq from confirmed behavioral requirements.
-- Recruiters can approve, edit, or delete individual questions.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_questions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    dimension_id    UUID NOT NULL REFERENCES behavioral_dimensions(id),
    question        TEXT NOT NULL,
    type            TEXT NOT NULL DEFAULT 'behavioral'
                        CHECK (type IN ('behavioral', 'situational', 'competency')),
    difficulty      TEXT NOT NULL DEFAULT 'medium'
                        CHECK (difficulty IN ('easy', 'medium', 'hard')),
    indicators      JSONB NOT NULL DEFAULT '[]',
    approved        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE interview_questions IS
    'AI-generated behavioral interview questions. Recruiters approve/edit before use.';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_interview_questions_job_id
    ON interview_questions(job_id);

CREATE INDEX IF NOT EXISTS idx_interview_questions_dimension_id
    ON interview_questions(dimension_id);

CREATE INDEX IF NOT EXISTS idx_interview_questions_approved
    ON interview_questions(approved);


-- ---------------------------------------------------------------------------
-- RLS for interview_questions
-- ---------------------------------------------------------------------------
ALTER TABLE interview_questions ENABLE ROW LEVEL SECURITY;

-- Recruiters can see questions for their own jobs
CREATE POLICY "Recruiter can view own job questions"
    ON interview_questions FOR SELECT
    USING (
        job_id IN (
            SELECT id FROM jobs WHERE recruiter_id = auth.uid()
        )
    );

-- Recruiters can insert questions for their own jobs
CREATE POLICY "Recruiter can insert own job questions"
    ON interview_questions FOR INSERT
    WITH CHECK (
        job_id IN (
            SELECT id FROM jobs WHERE recruiter_id = auth.uid()
        )
    );

-- Recruiters can update questions for their own jobs
CREATE POLICY "Recruiter can update own job questions"
    ON interview_questions FOR UPDATE
    USING (
        job_id IN (
            SELECT id FROM jobs WHERE recruiter_id = auth.uid()
        )
    );

-- Recruiters can delete questions for their own jobs
CREATE POLICY "Recruiter can delete own job questions"
    ON interview_questions FOR DELETE
    USING (
        job_id IN (
            SELECT id FROM jobs WHERE recruiter_id = auth.uid()
        )
    );


-- =============================================================================
-- PHASE 5 -- Candidate Portal
-- =============================================================================

-- ---------------------------------------------------------------------------
-- INTERVIEW_SESSIONS
-- UUID-token access for candidates -- no Supabase Auth required for candidates
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interview_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    token           UUID NOT NULL UNIQUE DEFAULT uuid_generate_v4(),
    candidate_name  TEXT NOT NULL,
    candidate_email TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed')),
    email_status    TEXT NOT NULL DEFAULT 'pending'
                        CHECK (email_status IN ('pending', 'sent', 'failed')),
    expires_at      TIMESTAMPTZ,
    submitted_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Idempotent column addition for existing databases
ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS email_status TEXT NOT NULL DEFAULT 'pending' CHECK (email_status IN ('pending', 'sent', 'failed'));

CREATE INDEX IF NOT EXISTS idx_interview_sessions_job_id ON interview_sessions(job_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_token  ON interview_sessions(token);

COMMENT ON TABLE interview_sessions IS
    'One row per candidate invited to an interview. Token is the public access key.';

ALTER TABLE interview_sessions ENABLE ROW LEVEL SECURITY;

-- Recruiters can read/insert sessions for their own jobs
CREATE POLICY "Recruiter can read own job sessions"
    ON interview_sessions FOR SELECT
    USING (
        job_id IN (
            SELECT id FROM jobs WHERE recruiter_id = auth.uid()
        )
    );

CREATE POLICY "Recruiter can create sessions for own jobs"
    ON interview_sessions FOR INSERT
    WITH CHECK (
        job_id IN (
            SELECT id FROM jobs WHERE recruiter_id = auth.uid()
        )
    );

-- Service-role (backend) can do everything (covers public candidate endpoints)
-- No anon policy: backend uses service-role key for public candidate reads/writes.


-- ---------------------------------------------------------------------------
-- CANDIDATE_RESPONSES
-- Candidate's free-text STAR answers; one row per question answered
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidate_responses (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES interview_questions(id) ON DELETE CASCADE,
    answer      TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (session_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_candidate_responses_session_id  ON candidate_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_candidate_responses_question_id ON candidate_responses(question_id);

COMMENT ON TABLE candidate_responses IS
    'Candidate free-text answers. One row per question per session.';

ALTER TABLE candidate_responses ENABLE ROW LEVEL SECURITY;

-- Recruiters can read responses for sessions belonging to their jobs
CREATE POLICY "Recruiter can read responses for own jobs"
    ON candidate_responses FOR SELECT
    USING (
        session_id IN (
            SELECT s.id FROM interview_sessions s
            JOIN jobs j ON j.id = s.job_id
            WHERE j.recruiter_id = auth.uid()
        )
    );

-- Service-role covers candidate INSERT (no Supabase Auth on candidate side)


-- =============================================================================
-- PHASE 6 -- Response Analysis & Scoring
-- =============================================================================

-- ---------------------------------------------------------------------------
-- RESPONSE_SCORES
-- One row per candidate response (question), storing NLP analysis results.
-- Scored deterministically by Python; Groq is not used for scoring.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS response_scores (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id          UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    question_id         UUID NOT NULL REFERENCES interview_questions(id) ON DELETE CASCADE,
    response_id         UUID NOT NULL REFERENCES candidate_responses(id) ON DELETE CASCADE,
    dimension_name      TEXT NOT NULL,
    normalized_score    INTEGER NOT NULL DEFAULT 0
                            CHECK (normalized_score BETWEEN 0 AND 100),
    raw_score           FLOAT NOT NULL DEFAULT 0.0
                            CHECK (raw_score BETWEEN 0.0 AND 1.0),
    confidence          FLOAT NOT NULL DEFAULT 0.0
                            CHECK (confidence BETWEEN 0.0 AND 1.0),
    indicators_matched  INTEGER NOT NULL DEFAULT 0,
    total_indicators    INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'scored',
    evidence            JSONB NOT NULL DEFAULT '[]',
    scored_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (response_id)
);

CREATE INDEX IF NOT EXISTS idx_response_scores_session_id  ON response_scores(session_id);
CREATE INDEX IF NOT EXISTS idx_response_scores_response_id ON response_scores(response_id);

COMMENT ON TABLE response_scores IS
    'NLP-generated behavioral scores per candidate response. One row per response. '
    'Evidence field contains per-indicator similarity scores as JSONB array.';

ALTER TABLE response_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Recruiter can read scores for own jobs"
    ON response_scores FOR SELECT
    USING (
        session_id IN (
            SELECT s.id FROM interview_sessions s
            JOIN jobs j ON j.id = s.job_id
            WHERE j.recruiter_id = auth.uid()
        )
    );

-- Service-role handles all inserts/updates (backend scoring pipeline).
-- No anon/candidate policy needed.


-- =============================================================================
-- PHASE 7 -- Job-Candidate Alignment
-- =============================================================================

-- ---------------------------------------------------------------------------
-- SESSION_ALIGNMENTS
-- Deterministic job-candidate behavioral alignment results.
-- Stores weighted overall alignment score, dimension breakdown, strengths,
-- and areas for recruiter review.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS session_alignments (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id              UUID NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    job_id                  UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    overall_score           FLOAT NOT NULL DEFAULT 0.0
                                CHECK (overall_score BETWEEN 0.0 AND 100.0),
    dimension_alignments    JSONB NOT NULL DEFAULT '[]',
    strengths               JSONB NOT NULL DEFAULT '[]',
    areas_for_review        JSONB NOT NULL DEFAULT '[]',
    metadata                JSONB NOT NULL DEFAULT '{}',
    calculated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (session_id)
);

CREATE INDEX IF NOT EXISTS idx_session_alignments_session_id ON session_alignments(session_id);
CREATE INDEX IF NOT EXISTS idx_session_alignments_job_id     ON session_alignments(job_id);

COMMENT ON TABLE session_alignments IS
    'Deterministic weighted job-candidate behavioral alignment results. '
    'Calculated via formula sum(candidate_score * job_weight) / sum(job_weight).';

ALTER TABLE session_alignments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Recruiter can read alignments for own jobs"
    ON session_alignments FOR SELECT
    USING (
        job_id IN (
            SELECT id FROM jobs WHERE recruiter_id = auth.uid()
        )
    );

-- Service-role handles all inserts/updates for the backend alignment pipeline.

