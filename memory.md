# Project Memory

## Current Phase
Phase 12 (Fairness Features) — Phase D: Recruiter Oversight and Audit Trails — COMPLETE

## Completed
### Phase 0
- [x] Project structure, README.md, architecture.md, .gitignore, .env.example

### Phase 1
- [x] Backend: Python venv (.venv) with all dependencies (Python 3.14.2)
- [x] Backend: requirements.txt + groq>=1.7.0 added
- [x] Backend: pyproject.toml with pytest config + env var injection for tests
- [x] Backend: app/core/config.py (pydantic-settings, all env vars incl. GROQ_*)
- [x] Backend: app/core/security.py (Supabase JWT validation, require_recruiter dep)
- [x] Backend: app/db/client.py (anon + admin Supabase client singletons)
- [x] Backend: app/schemas/common.py, jobs.py, profiles.py
- [x] Backend: app/services/job_service.py (full CRUD)
- [x] Backend: app/services/profile_service.py (get, upsert, update)
- [x] Backend: app/api/health.py, auth.py, jobs.py
- [x] Backend: app/main.py (lifespan, CORS, all routers)
- [x] Backend: tests/conftest.py, test_health.py (3), test_jobs.py (11), test_schemas.py (8)
- [x] Backend: 22/22 tests passing
- [x] Database: docs/supabase_schema.sql (14 tables, RLS, seed data, triggers)
- [x] Frontend: Vite 8 + React 19 + Tailwind v4 + React Router v7
- [x] Frontend: Auth context, Navbar, ProtectedRoute
- [x] Frontend: LoginPage, DashboardPage, JobsPage, CreateJobPage, JobDetailPage
- [x] Frontend: Clean production build (77 modules)

### Phase 2
- [x] Backend: app/schemas/dimensions.py (IndicatorRead, DimensionRead, DimensionDetail)
- [x] Backend: app/services/dimension_service.py (list, get, get_by_name, list_indicators)
- [x] Backend: app/api/dimensions.py (GET /api/dimensions, GET /api/dimensions/{id})
- [x] Backend: tests/test_dimensions.py (10 tests)
- [x] Frontend: DimensionsPage.jsx (accordion card grid, per-dimension colors + icons)
- [x] Frontend: Navbar + App.jsx updated (/dimensions route)
- [x] Frontend: Clean build (78 modules)

### Phase 3
- [x] Backend: app/ai/groq_client.py (shared client, retry, GroqError, call_groq_json)
- [x] Backend: app/ai/schemas.py (DimensionRequirement, JobAnalysisOutput -- Pydantic-validated)
- [x] Backend: app/ai/job_analyzer.py (analyze_job -- prompt engineering + validation)
- [x] Backend: app/schemas/requirements.py (RequirementRead, RequirementConfirm)
- [x] Backend: app/services/job_requirement_service.py (save, list, update with ownership)
- [x] Backend: app/api/analysis.py (POST analyze, GET requirements, PATCH requirement)
- [x] Backend: app/main.py updated -- analysis router registered
- [x] Backend: requirements.txt -- groq>=1.7.0 added
- [x] Backend: tests/test_analysis.py (13 tests)
- [x] Backend: ALL 45 TESTS PASSING (0 new warnings)
- [x] Frontend: services/api.js -- analysisApi added
- [x] Frontend: JobDetailPage.jsx -- full Behavioral Requirements panel
- [x] Frontend: Clean production build (78 modules, 0 errors)

### Phase 4
- [x] Backend: app/ai/question_schemas.py (GeneratedQuestion, QuestionGeneratorOutput -- Pydantic-validated)
- [x] Backend: app/ai/question_generator.py (generate_questions -- STAR prompt, 2-3 questions/dim)
- [x] Backend: app/schemas/questions.py (QuestionRead, QuestionUpdate)
- [x] Backend: app/services/question_service.py (save w/ delete-then-insert, list, update, delete)
- [x] Backend: app/api/questions.py (4 endpoints: generate, list, PATCH, DELETE)
- [x] Backend: app/main.py updated -- questions router registered
- [x] Backend: tests/test_questions.py (19 tests)
- [x] Backend: ALL 64 TESTS PASSING (0 errors)
- [x] Database: docs/supabase_schema.sql -- interview_questions table added (Phase 4 section)
- [x] Frontend: services/api.js -- questionsApi added (generate, list, update, delete)
- [x] Frontend: JobDetailPage.jsx -- full Interview Questions panel
- [x] Frontend: Clean production build (78 modules, 0 errors)

### Phase 5 -- Candidate Portal -- COMPLETE
- [x] Backend: app/schemas/sessions.py (SessionCreate, SessionRead, PublicQuestion,
      PublicSessionRead, ResponseCreate, ResponseRead, SubmitResponsesPayload)
- [x] Backend: app/services/session_service.py (create_session, list_sessions,
      get_session_by_token, get_approved_questions, get_job_public,
      submit_responses, mark_in_progress)
- [x] Backend: app/api/sessions.py (4 endpoints:
      POST /jobs/{id}/sessions, GET /jobs/{id}/sessions,
      GET /sessions/{token}, POST /sessions/{token}/responses)
- [x] Backend: app/main.py updated -- sessions router registered
- [x] Backend: tests/test_sessions.py (19 tests -- all passing)
- [x] Database: docs/supabase_schema.sql -- Phase 5 tables added (lines 622-706)
- [x] Frontend: services/api.js -- sessionsApi added (create, list, getByToken, submitResponses)
- [x] Frontend: JobDetailPage.jsx -- Candidate Sessions panel (recruiter-side)
- [x] Frontend: pages/CandidatePage.jsx -- CREATED (public candidate STAR answer form)
- [x] Frontend: App.jsx -- /assess/:token public Route added
- [x] Frontend: Clean production build (79 modules, 0 errors)

### Phase 6 -- Response Analysis & Scoring -- COMPLETE
- [x] Backend: requirements.txt -- sentence-transformers>=3.0.0 added
- [x] Backend: app/nlp/preprocessor.py -- text cleaning, quality gate (min chars/words, garbled detection)
- [x] Backend: app/nlp/embedder.py -- singleton SentenceTransformer (all-MiniLM-L6-v2), embeddings, cosine similarity
- [x] Backend: app/scoring/rubric.py -- deterministic rubric:
  - Strong match (>=0.65 sim -> 2 pts), Partial match (>=0.40 sim -> 1 pt), None (<0.40 -> 0 pts)
  - Normalized 0-100 scores: round((raw / max) * 100)
  - Confidence calculation: mean positive similarity
  - Evidence extraction: snippet with highest similarity
- [x] Backend: app/scoring/analyzer.py -- safe pipeline orchestrator (never raises, catches quality gate failures)
- [x] Backend: app/schemas/scoring.py -- EvidenceItem, ResponseScoreRead, SessionScoreSummary, ScoreTrigger
- [x] Backend: app/services/scoring_service.py -- fetches candidate responses, question indicators, executes analysis, upserts response_scores
- [x] Backend: app/api/scoring.py -- 2 endpoints:
  - POST /api/sessions/{session_id}/score (recruiter-triggered, requires completed status)
  - GET  /api/sessions/{session_id}/scores (returns full summary, scores, and explainable evidence)
- [x] Backend: app/main.py updated -- scoring router registered
- [x] Backend: tests/test_scoring.py -- 55 comprehensive tests (11 preprocessor, 18 rubric, 10 analyzer, 10 API, 6 service helpers)
- [x] Database: docs/supabase_schema.sql -- response_scores table + indexes + RLS (lines 708-759)
- [x] Frontend: services/api.js -- scoringApi added (scoreSession, getScores)
- [x] Frontend: components/ScoreModal.jsx -- CREATED
- [x] Frontend: pages/JobDetailPage.jsx -- updated with Score / Re-Score and View Scores actions
- [x] Frontend: Clean production build (80 modules, 0 errors)

### Phase 7 -- Job-Candidate Behavioral Alignment -- COMPLETE
- [x] Backend: app/alignment/calculator.py -- pure deterministic alignment calculation engine:
  - Formula: sum(candidate_score * job_weight) / sum(job_weight)
  - Per-dimension point contribution: candidate_score * (job_weight / total_weight)
  - Dimension priority weighting: job_weight / total_weight * 100
  - Safe handling of missing dimensions, unweighted dimensions, invalid weights, and zero-weight divisions
  - Objective explainable strengths and review areas generation
  - Strict compliance: NO automated hire/reject recommendations or employment decisions
- [x] Backend: app/schemas/alignment.py -- DimensionAlignmentItem, SessionAlignmentRead, AlignmentTriggerPayload
- [x] Backend: app/services/alignment_service.py -- orchestrates data fetching, calculation, and upserting into session_alignments
- [x] Backend: app/api/alignment.py -- 3 endpoints:
  - POST /api/sessions/{session_id}/alignment (calculate & save alignment)
  - GET  /api/sessions/{session_id}/alignment (fetch single session alignment)
  - GET  /api/jobs/{job_id}/alignments (list alignments for all candidate sessions under a job)
- [x] Backend: app/main.py updated -- alignment router registered
- [x] Backend: tests/test_alignment.py -- 23 comprehensive tests (13 calculator unit tests, 2 service helper tests, 8 API integration tests)
- [x] Backend: ALL 161 TESTS PASSING (0 errors, 1 upstream warning)
- [x] Database: docs/supabase_schema.sql -- session_alignments table + indexes + recruiter RLS (lines 760-805)
- [x] Frontend: services/api.js -- alignmentApi added (calculate, get, listForJob)
- [x] Frontend: components/AlignmentModal.jsx -- CREATED:
  - Overall Alignment Score (0-100) with color-coded gauge and mathematical formula explainer
  - Requirements assessed summary & evaluation confidence
  - Dimension-by-dimension breakdown table with side-by-side comparison bars, job weight priority %, candidate score, and point contributions
  - Key Behavioral Strengths panel
  - Areas for Recruiter Review panel with objective interview inquiry guidance
  - Compliance notice explicitly stating no automated employment decisions
  - Recalculate trigger button
- [x] Frontend: pages/JobDetailPage.jsx -- updated:
  - Added "🎯 Alignment" button on completed candidate sessions
  - Integrated AlignmentModal display and error handling
- [x] Frontend: Clean production build (81 modules, 0 errors)

### Phase 8: Assessment Reports & Recruiter Dashboard
- [x] Backend: app/schemas/report.py -- ReportEvidenceItem, ReportQuestionItem, ReportDimensionItem, ReportExecutiveSummary, AssessmentReportRead, SessionReportSummaryItem
- [x] Backend: app/services/report_service.py:
  - Aggregates session, job requirements, questions, responses, scores, and alignment deterministically
  - Auto-calculates alignment if not yet persisted for completed & scored sessions
  - Generates structured interview inquiry prompts for recruiter review
  - Generates ethical compliance disclaimer (strictly decision-support; no automated hire/reject recommendations; no mental health diagnosis)
  - Handles incomplete assessments and missing data safely
- [x] Backend: app/api/reports.py -- 2 endpoints:
  - GET /api/sessions/{session_id}/report (comprehensive explainable candidate assessment report)
  - GET /api/jobs/{job_id}/reports/summary (summary roll-up of all candidate sessions for a job)
  - Recruiter authentication & job ownership authorization enforced
- [x] Backend: app/main.py updated -- reports router registered under /api
- [x] Backend: tests/test_reports.py -- 9 tests:
  - Full report generation for completed scored session
  - Safety & handling of incomplete/unscored sessions
  - Dynamic generation of tailored recruiter inquiry prompts
  - Explicit non-diagnostic ethical disclaimer verification
  - Recruiter authorization & 403 Forbidden for cross-recruiter access
  - 404 handling for non-existent session
  - Job-level session report summary roll-up
- [x] Backend: ALL 170 TESTS PASSING (0 errors, 1 upstream warning)
- [x] Frontend: services/api.js -- reportsApi added (getReport, getJobSummary)
- [x] Frontend: pages/AssessmentReportPage.jsx -- CREATED:
  - Executive summary card with overall alignment score gauge & formula badge
  - Requirements vs. Candidate benchmark visualizer with side-by-side comparative bars and gap metrics
  - Strengths & review areas with dynamic behavioral badges
  - Recommended interview inquiry questions for deep-dive in live rounds
  - Full question & response evidence transcript with collapsible accordions, detected indicators, confidence scores, and verbatim candidate quotes
  - Incomplete / pending assessment safe fallback state
  - Print-ready PDF stylesheet (@media print) with export button
  - Prominent ethical non-decision & non-diagnostic compliance warning
- [x] Frontend: App.jsx -- Registered `/jobs/:jobId/sessions/:sessionId/report` route
- [x] Frontend: pages/JobDetailPage.jsx -- Added "📄 Full Report" button on completed candidate session rows
- [x] Frontend: Clean production build (82 modules, 0 errors)

### Phase 9: Evaluation, Fairness & System Validation -- COMPLETE
- [x] Scoring & Alignment Validation:
  - Verified 100% deterministic scoring calculations in Python (identical input produces identical score across repeated runs)
  - Verified normalization boundaries [0, 100] and score clipping
  - Verified mathematical alignment formula: sum(candidate_score * weight) / sum(weight) matches sum of dimension point contributions
  - Handled boundary conditions: zero weights, negative weights (clamped to 0), float weights, division-by-zero safely
- [x] Evidence Validation:
  - Verified every scored response has supporting evidence records with similarity and discrete level tags
  - Quality gate catches too_short, garbled, and empty answers, preventing false positive evidence
  - Fixed indicator resolution fallback in `ScoringService.get_question_with_indicators` so custom/generated question indicators are never dropped
- [x] Question Validation:
  - Verified questions map to the 6 core behavioral dimensions
  - Verified question coverage aligns with recruiter-confirmed requirements and weights
  - Validated question length, types, and observable indicators via Pydantic
- [x] Fairness & Safety Audit:
  - Verified zero use of sensitive/protected personal characteristics (race, gender, age, religion, disability)
  - Verified zero clinical or mental-health diagnostic terminology in prompts, schemas, reports, and calculators
  - Verified system NEVER makes automated hire/reject/select decisions; strictly provides objective decision-support
  - Mandatory ethical compliance disclaimer included on all assessment reports
  - Verified recruiter human oversight remains required at all stages (requirement confirmation, question approval, assessment evaluation)
- [x] Security Audit:
  - Audited JWT authentication and recruiter authorization across all endpoints
  - Verified recruiter tenant isolation: Recruiter B receives 403 Forbidden when attempting to access Recruiter A's jobs, sessions, scores, alignments, or reports
  - Verified candidate token security: UUID access token; public endpoint returns only PublicSessionRead and never exposes recruiter IDs, weights, internal scores, or other candidate data
  - Verified secrets/API keys are kept strictly in backend and never exposed to frontend
- [x] Data Validation:
  - Verified safe handling of missing dimensions (marked as 'missing' with 0 contribution and flagged in review areas)
  - Verified handling of incomplete assessments, brief responses, and garbled text
  - Verified duplicate submissions to completed sessions are blocked with 403 Forbidden
  - Verified expired session links are blocked with 403 Forbidden
- [x] Fixes Made:
  1. `backend/app/services/report_service.py`: Fixed `_get_responses_by_session` query to select actual schema columns (`answer`, `created_at`) instead of non-existent columns (`response_text`, `submitted_at`), and supported both formats gracefully.
  2. `backend/app/services/scoring_service.py`: Added fallback for custom/generated question indicators so they are preserved and scored even if not pre-seeded in the database table.
  3. `backend/app/services/session_service.py`: Added missing `get_session(session_id)` method used by report verification.
- [x] Tests:
  - Added `backend/tests/test_validation_fairness.py` with 21 comprehensive audit tests
  - ALL 191 BACKEND TESTS PASSING (100% green in 4.70s)
  - Frontend production build verified (82 modules, 0 errors in 747ms)

### Phase 10: Production Hardening & Final System Evaluation -- COMPLETE
- [x] Production Security Hardening & Rate Limiting:
  - Implemented thread-safe, sliding-window rate limiter in `backend/app/core/rate_limiter.py` with automatic timestamp pruning and RFC 6585 HTTP 429 Retry-After response
  - Rate-limited public candidate assessment endpoints in `backend/app/api/sessions.py`:
    - `GET /sessions/{token}`: 60 requests / minute per client IP
    - `POST /sessions/{token}/responses`: 15 submissions / minute per client IP
  - Reverse proxy IP resolution with `X-Forwarded-For` header support
  - Bypassed in test environment by default for full test-runner velocity; isolated test suite verifies enforcement
  - Re-verified tenant isolation: Recruiter B receives 403 Forbidden when attempting to access Recruiter A's resources
  - Re-verified zero secret or API key leakage to the frontend
- [x] Database Readiness:
  - Fully verified `docs/supabase_schema.sql` (lines 622-805) covering Phase 5-7 tables (`interview_sessions`, `candidate_responses`, `response_scores`, `session_alignments`)
  - Confirmed all primary keys, foreign keys, cascade deletes, unique constraints, and recruiter RLS policies are 100% aligned with application services
  - Documented exact SQL migration steps for production deployment
- [x] Reliability & Idempotency:
  - Verified idempotent scoring (`POST /api/sessions/{session_id}/score` upserts on conflict `response_id`)
  - Verified idempotent alignment calculation (`POST /api/sessions/{session_id}/alignment` upserts on conflict `session_id`)
  - Verified idempotent assessment reporting (`GET /api/sessions/{session_id}/report` safely aggregates and auto-resolves alignment without side-effects)
  - Verified candidate submission safety: completed sessions reject resubmission with 403 Forbidden ("This assessment has already been submitted")
- [x] Performance & Resource Optimization:
  - Embedding model (`all-MiniLM-L6-v2`) is loaded once per process via thread-safe lazy singleton in `backend/app/nlp/embedder.py`
  - Normalized embeddings allow instant dot-product cosine similarity matrix multiplication ($O(N)$ vectorized)
  - Response scoring embeds candidate text and indicators in a single combined batch
  - Database queries batch indicator and dimension lookups via `.in_()` clauses, eliminating $N+1$ query overhead
- [x] Final Test Suite:
  - Added `backend/tests/test_rate_limiter.py` with 6 unit and integration tests
  - ALL 197 BACKEND TESTS PASSING (100% green in 4.27s)
  - Frontend production build verified (82 modules, 0 errors in 759ms)

### Post-Hardening: Live System Verification & Bug Fixes -- COMPLETE
- [x] Groq Model Migration (Decommissioned Model Fix):
  - Groq decommissioned `llama3-70b-8192` with HTTP 400 `model_decommissioned`.
  - Queried live Groq API key and verified `openai/gpt-oss-120b` supports JSON schema generation for job analysis and STAR question generation.
  - Updated default model to `openai/gpt-oss-120b` in `backend/.env`, root `.env`, and `backend/app/core/config.py`.
  - Added automatic fallback in `backend/app/ai/groq_client.py` to intercept deprecated LLaMA models and route them to `openai/gpt-oss-120b`.
- [x] API Ownership & Service Signature Fixes:
  - `JobService.get_job`: Made `recruiter_id: Optional[str] = None` to support internal service lookups, and added null-check for `result is None` to avoid `AttributeError: 'NoneType' object has no attribute 'data'`.
  - `backend/app/api/scoring.py`: Fixed `_get_session_or_404` to pass `recruiter_id` to `JobService.get_job` and enforce ownership in both unit tests and live Supabase queries.
  - `backend/app/api/alignment.py`: Fixed `_get_session_or_404` and `_verify_job_ownership` to pass `recruiter_id`.
  - `backend/app/api/reports.py`: Fixed `_verify_session_access` and `_verify_job_ownership` to pass `recruiter_id`.
- [x] Embedding Model Initialization:
  - Downloaded and locally cached `all-MiniLM-L6-v2` weights (~80MB) at `~/.cache/huggingface/hub` for zero-latency offline embedding inference.
- [x] Live End-to-End Walkthrough Verified:
  1. Recruiter Auth: Logged in with confirmed recruiter credentials (`user@gmail.com`).
  2. Job Creation & Analysis: Created "Senior Full-Stack Engineer" job, ran Groq analysis (`HTTP 201 Created`), successfully extracted and saved 6 behavioral dimensions (`leadership`, `communication`, `adaptability`, `teamwork`, `decision_making`, `stress_management`).
  3. Question Generation: Generated 11 structured STAR interview questions mapped to confirmed dimensions.
  4. Candidate Assessment: Generated unique session token, answered all 11 questions with detailed STAR responses via `/assess/:token`, and successfully submitted.
  5. Response Scoring: Triggered local SentenceTransformers semantic NLP scoring via `POST /api/sessions/:id/score` (`HTTP 200 OK`); all 11 responses scored and saved to `response_scores`.
  6. Alignment Calculation: Calculated weighted overall Job-Fit percentage and dimension contributions via `POST /api/sessions/:id/alignment` (`HTTP 200 OK`).
  7. Assessment Report: Generated comprehensive candidate report via `GET /api/sessions/:id/report` (`HTTP 200 OK`).
- [x] Version Control:
  - Committed Resend & Gmail SMTP email invitation integration, Candidate Sessions UI updates, retry endpoints, and test suite. Pushed to GitHub `origin/main`.
  - Verified no `.env` files or credentials were leaked.

- [x] Free Candidate Invitation Email Service (Option 1: Gmail SMTP + Resend Support):
  - Added `EMAIL_PROVIDER`, `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD` to `app/core/config.py`, `.env.example`, and `backend/.env`.
  - Updated `backend/app/services/email_service.py` (`EmailService.send_assessment_invitation`):
    - Supports **100% Free Gmail SMTP** (`smtp.gmail.com:587` with TLS) sending to **any candidate email address** without domain verification restrictions.
    - Seamlessly falls back to Resend API when `EMAIL_PROVIDER=resend`.
    - Features credential masking for both SMTP passwords and Resend API keys.
  - Updated `backend/tests/test_email_service.py`: added 3 new unit tests for Gmail SMTP delivery success, missing credentials handling, and password redaction (16 email tests total).

### Phase 11 -- Admin-Managed Behavioral Framework & Versioning -- COMPLETE
- [x] Database Schema & Migration (`docs/supabase_schema.sql` lines 811-960):
  - Created `framework_versions` table with `version_number`, `name`, `description`, `status` ('draft', 'active', 'archived'), `dimensions_snapshot` (frozen JSONB), `activated_at`, `created_by`.
  - Added `order_index`, `status` ('active', 'draft', 'archived'), and `updated_at` to `behavioral_dimensions`.
  - Added `order_index`, `is_active`, and `updated_at` to `behavioral_indicators`.
  - Added `framework_version_id` foreign key referencing `framework_versions(id)` to `jobs`.
  - Configured RLS policies: public read for framework versions, and strict admin write policies (`profiles.role = 'admin'`) for dimensions, indicators, and framework versions.
  - Added idempotent SQL seed logic for Version 1.0 snapshot preserving the original 6 core dimensions and pinning historical unassigned jobs.
- [x] Security & Authorization:
  - Implemented `require_admin` dependency in `backend/app/core/security.py` asserting caller has `role == "admin"`.
  - Enforced `require_admin` on all management endpoints; unauthenticated callers receive HTTP 401, recruiters receive HTTP 403 Forbidden.
  - Preserved recruiter access on candidate and assessment endpoints; recruiters cannot modify framework configurations.
- [x] Admin Framework Backend API (`backend/app/api/admin_framework.py`):
  - `GET    /api/admin/framework/versions`: List all framework versions.
  - `GET    /api/admin/framework/current`: Fetch current active framework and snapshot.
  - `POST   /api/admin/framework/validate`: Pre-activation integrity check (min 3 active dimensions, min 2 indicators per dimension, identifier and description validation).
  - `POST   /api/admin/framework/publish`: Freezes active dimensions snapshot, supersedes previous active version, creates new version number.
  - `GET    /api/admin/dimensions`: List all dimensions with embedded indicators and indicator counts.
  - `POST   /api/admin/dimensions`: Create new dimension with optional initial indicators.
  - `GET    /api/admin/dimensions/{id}`: Dimension detail with usage references count.
  - `PUT    /api/admin/dimensions/{id}`: Update dimension properties.
  - `DELETE /api/admin/dimensions/{id}`: Safe archive/delete (referenced dimensions are safely archived to preserve historical assessments).
  - `PATCH  /api/admin/dimensions/reorder`: Bulk update display ordering across dimensions.
  - `POST   /api/admin/dimensions/{id}/indicators`: Add observable behavioral indicator.
  - `PUT    /api/admin/indicators/{id}`: Update observable indicator.
  - `DELETE /api/admin/indicators/{id}`: Delete indicator.
  - Registered under `/api` in `backend/app/main.py`.
- [x] Dynamic Behavioral Framework Engine:
  - `backend/app/ai/schemas.py`: Replaced hardcoded 6-dimension set with dynamic registry and database-backed validator supporting custom dimensions.
  - `backend/app/ai/question_schemas.py`: Made question validator dynamic, supporting any registered or active framework dimensions.
  - `backend/app/ai/job_analyzer.py`: Generates dynamic Groq analysis system prompt containing all active framework dimensions and observable indicator signals.
  - `backend/app/ai/question_generator.py`: Generates dynamic STAR interview question prompt based on confirmed requirements and custom dimensions.
  - `backend/app/services/job_requirement_service.py` & `question_service.py`: Resolves custom dimension names from `behavioral_dimensions` table dynamically.
  - `backend/app/scoring/analyzer.py` & `rubric.py`: Preserved 100% deterministic Python NLP scoring with SentenceTransformers (`all-MiniLM-L6-v2`); evaluated against custom observable indicators without LLM hallucinations.
  - `backend/app/alignment/calculator.py`: Verified pure math alignment weighting for any number of custom dimensions.
  - `backend/app/services/report_service.py`: Added framework version tracking to report metadata. Historical assessments remain immutable.
- [x] Admin UI & Frontend Management:
  - Centralized API: added `adminFrameworkApi` methods to `frontend/src/services/api.js`.
  - Context & Navigation: updated `frontend/src/context/AuthContext.jsx` with `role` and `isAdmin`; updated `Navbar.jsx` with prominent Admin Framework Manager link.
  - Vite HMR Fast Refresh Fix: extracted `useAuth` hook into standalone `frontend/src/context/useAuth.js`, cleanly decoupling hook exports from `AuthProvider` component to eliminate React plugin fast-refresh compiler warnings.
  - Route Protection: created `frontend/src/components/AdminRoute.jsx` restricting access to `role === 'admin'`.
  - Framework Manager Page (`frontend/src/pages/AdminFrameworkPage.jsx`):
    - Comprehensive dashboard displaying active dimensions, drafts, total indicators, and release versions.
    - Drag / up-down dimension reordering with instant server sync.
    - Interactive indicator management: view, create, edit, and delete observable behavioral signals per dimension.
    - Dedicated in-modal error banners for Dimension, Indicator, and Publish modals with intelligent guidance when duplicate dimension identifiers are entered.
    - Dynamic initial indicators with interactive row additions/removals directly inside the Create Dimension modal.
    - Smart action buttons: displays red "Delete" for unreferenced dimensions and "Archive" for referenced dimensions.
    - Real-time pre-activation validation checklist modal.
    - Version publishing modal with changelog notes and staged snapshot preview.
    - Version history tab with immutable snapshot inspector.
  - Recruiter Dimensions View (`frontend/src/pages/DimensionsPage.jsx`): Updated with active framework badge and admin quick-action banner.
  - Registered route `/admin/framework` in `frontend/src/App.jsx`.
- [x] Backend Framework Service Fixes:
  - Fixed `framework_service.py` `list_dimensions_admin` indicator dictionary grouping (`ind_by_dim`) to eliminate runtime `NameError`.
  - Added safe `is_referenced` detection in `list_dimensions_admin` and `DimensionDetail` schema to differentiate between safe permanent deletion of unused dimensions vs archiving of historical ones.
- [x] Test Suite:
  - Added `backend/tests/test_admin_framework.py` with 23 comprehensive tests covering:
    - Authorization (401 anonymous, 403 recruiter, 200 admin)
    - Dimension and indicator CRUD
    - Reordering
    - Safe archiving of referenced dimensions
    - Pre-activation framework validation
    - Version publishing and snapshot freezing
    - Pipeline compatibility (job analysis, questions, deterministic NLP scoring, alignment)
  - ALL 236/236 BACKEND TESTS PASSING (100% green in 43.81s).
  - Clean frontend production build (85 modules, 0 errors in 1.27s).

### Phase 12 (Fairness Features) — Phase A: Framework Snapshot Binding — COMPLETE
Fixes all 4 framework snapshot gaps identified in the pre-implementation audit (FS-1 → FS-4).
Goal: Every assessment session is permanently anchored to the exact frozen framework snapshot
that was active when the session was created. Historical reports and re-scores are reproducible
even if an admin modifies or archives live dimensions/indicators later.

- [x] **FS-4 — `backend/app/services/job_service.py`** (`create_job`):
  - Added `_get_active_framework_version_id()` helper (local import of `FrameworkService`,
    non-fatal — returns `None` if no active version or DB unavailable).
  - `create_job()` now inserts `framework_version_id` on every new job row when an active
    version exists. Fully backwards-compatible: skipped when `None`.

- [x] **FS-2 — `backend/app/services/session_service.py`** (`create_session`):
  - `create_session()` now reads `jobs.framework_version_id` and writes it to the new
    `interview_sessions` row, freezing the snapshot link at session creation time.
  - Graceful fallback: job lookup errors are swallowed (debug-logged); session creation
    always succeeds.

- [x] **FS-3 — `backend/app/services/scoring_service.py`** (snapshot-based indicator resolution):
  - `get_session()` now also selects `framework_version_id`.
  - Added `_get_snapshot_for_session(session)` — loads `framework_versions.dimensions_snapshot`
    JSONB for the pinned version ID; returns `None` if no version is pinned.
  - Added `_get_indicators_from_snapshot(snapshot, dimension_id, indicator_names)` — resolves
    `dimension_name` and full indicator objects from the frozen snapshot; falls back to live DB
    when dimension is absent from snapshot.
  - `get_question_with_indicators(question_id, snapshot=None)` — now accepts optional snapshot;
    snapshot path is tried first, live DB fallback is preserved.
  - `score_session()` — loads snapshot once per session, passes it to every
    `get_question_with_indicators()` call; logs whether scoring used snapshot or live DB.

- [x] **FS-1 — `backend/app/services/report_service.py`** (framework version label):
  - Added `_get_framework_version_label(framework_version_id)` — queries `framework_versions`
    by the FK to get `version_number` and `name`; returns graceful fallback strings on error.
  - Removed the two broken `job.get('framework_version_number')` /
    `job.get('framework_version_name')` reads that referenced nonexistent `jobs` columns.
  - `get_assessment_report()` now calls `_get_framework_version_label()` to populate
    `metadata.framework_version` with the real DB-sourced label.

- [x] **SQL Migration — `docs/migrations/phase_a_snapshot_binding.sql`** (NEW FILE):
  - `ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS framework_version_id UUID REFERENCES framework_versions(id) ON DELETE SET NULL;`
  - Index: `idx_interview_sessions_framework_version_id`.
  - Idempotent (safe to re-run). Must be applied to Supabase before inviting new candidates.

- [x] **Regression Tests — `backend/tests/test_phase_a_snapshot_binding.py`** (NEW FILE, 17 tests):
  - `TestFS4JobCreationPinsFrameworkVersion` (3 tests):
    attaches active framework ID, skips when none exists, helper swallows errors.
  - `TestFS2SessionCreationBindsFrameworkVersion` (3 tests):
    copies job FK, omits when job has none, succeeds if job lookup fails.
  - `TestFS3ScoringUsesSnapshot` (6 tests):
    snapshot loaded from DB, None returned when no FK, indicator resolution from snapshot,
    unknown indicator fallback, unknown dimension returns None, live-DB fallback without snapshot.
  - `TestFS1ReportFrameworkVersionLabel` (4 tests):
    label from DB, default when None ID, fallback when DB row absent,
    regression guard that broken job column reads are no longer used.

- [x] **Phase B — Evidence-Based Scoring Explanations (ES-1 to ES-3)**:
  - **ES-1 (Persistence & Data Structure)**:
    - `IndicatorEvidence` dataclass in [`backend/app/scoring/rubric.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/scoring/rubric.py) updated with optional `evidence_text: Optional[str] = None` field.
    - `build_evidence()` updated to accept and pair `evidence_texts` per indicator, retaining full backward compatibility.
    - `ScoringService` in [`backend/app/services/scoring_service.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/services/scoring_service.py) serializes `evidence_text` into JSONB blob stored in `response_scores.evidence`.
    - `IndicatorEvidenceRead` in [`backend/app/schemas/scoring.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/schemas/scoring.py) and `ReportEvidenceItem` in [`backend/app/schemas/report.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/schemas/report.py) define `evidence_text: Optional[str] = None`.
  - **ES-2 (Sentence Segmentation)**:
    - `_split_sentences()` in [`backend/app/scoring/analyzer.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/scoring/analyzer.py) splits cleaned candidate responses into sentence units via regex punctuation boundaries (`.!?`), stripping whitespace and handling empty/single-sentence edge cases cleanly.
  - **ES-3 (Per-Sentence Embedding Grounding)**:
    - `_extract_sentence_evidence()` in [`backend/app/scoring/analyzer.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/scoring/analyzer.py) embeds sentences in a single batch with the active embedding model, computes pairwise cosine similarity against behavioral indicators, and attributes the top-matching sentence per indicator.
    - Respects a 0.10 similarity floor to avoid attributing unrelated sentences as false evidence.
    - Completely exception-safe and non-blocking; returns `None` on any internal failure.
    - Strictly additive: deterministic scoring rubric mathematics and confidence calculations remain 100% authoritative and unchanged. Cosine similarity and sentence quotes serve solely as supporting context for recruiters.
  - **Report & Frontend Integration**:
    - [`backend/app/services/report_service.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/services/report_service.py) extracts `evidence_text` and passes it through `questions_evidence` in candidate reports.
    - Frontend ([`AssessmentReportPage.jsx`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/frontend/src/pages/AssessmentReportPage.jsx) and [`ScoreModal.jsx`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/frontend/src/components/ScoreModal.jsx)) displays quoted, styled evidence snippets with indicator-matched badges.
    - Zero DDL alterations required; PostgreSQL JSONB stores new fields natively. Documented in [`docs/migrations/phase_b_evidence_explanations.sql`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/docs/migrations/phase_b_evidence_explanations.sql).
  - **Regression Tests — `backend/tests/test_phase_b_evidence.py`** (NEW FILE, 26 tests):
    - `TestSentenceSegmentation` (5 tests): standard punctuation, single sentences, empty/whitespace, multiple spaces/newlines, stripping.
    - `TestSentenceEvidenceExtraction` (4 tests): top sentence matching, 0.10 similarity floor, empty answers, exception safety.
    - `TestIndicatorEvidenceRubric` (7 tests): field existence, default None, immutability/frozen check, build_evidence, length validation, score aggregation pass-through.
    - `TestScoringInvariance` (1 test): verifies scores and confidence ratings are 100% invariant to sentence grounding.
    - `TestAnalyzerIntegration` (4 tests): analyze_response populates evidence, quality gate rejection handling, no indicators, safe exception wrapper.
    - `TestScoringServicePersistence` (1 test): verified JSONB serialization in `response_scores`.
    - `TestReportServiceEvidence` (2 tests): report generation with evidence_text, backward compatibility with legacy rows missing evidence_text.
    - `TestSchemaValidation` (2 tests): Pydantic validation with and without evidence_text.

- [x] **Phase C — Demographic Fairness Evaluation (FA-1 to FA-5)**:
  - **FA-1 (Dedicated Module & Admin-Only Ingestion/Audit API)**:
    - Created dedicated package [`backend/app/fairness/`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/fairness/):
      - [`metrics.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/fairness/metrics.py): 100% pure Python, deterministic metric calculation with zero network dependencies.
      - [`schemas.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/fairness/schemas.py): Pydantic v2 schemas for controlled evaluation records, dataset ingestion, audit requests, and reports.
      - [`service.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/fairness/service.py): `FairnessService` managing dataset ingestion, validation, persistence, and audit runs with memory fallback.
    - Created admin API router [`backend/app/api/fairness.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/api/fairness.py) registered in [`backend/app/main.py`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/backend/app/main.py):
      - `POST /api/fairness/datasets` (ingest controlled dataset, validated min 2 groups)
      - `GET /api/fairness/datasets` & `GET /api/fairness/datasets/{id}` (list/retrieve)
      - `POST /api/fairness/datasets/{id}/audit` (run audit on dataset)
      - `POST /api/fairness/evaluate` (atomic ingest + direct audit)
      - `GET /api/fairness/audits` & `GET /api/fairness/audits/{id}` (audit reports)
      - All endpoints protected by `require_admin`. Ordinary recruiters and public users receive HTTP 403 Forbidden.
  - **FA-2 (Demographic Parity, Equal Opportunity & Subgroup Recall)**:
    - **DPD**: Maximum pairwise selection rate disparity across all subgroups ($\max SR_g - \min SR_g$) and per-subgroup difference from reference group ($SR_g - SR_{\text{ref}}$).
    - **Adverse Impact Ratio (AIR)**: Four-fifths (80%) rule evaluation ($SR_g / SR_{\text{ref}}$), flagging disparities below 0.80.
    - **EOD**: True Positive Rate (Recall) disparity across subgroups ($\max TPR_g - \min TPR_g$).
    - **Subgroup Recall**: $TP_g / (TP_g + FN_g)$ calculated per subgroup when positive ground truth instances exist.
  - **FA-3 (Subgroup Sample Counts & Minimum Sample Warnings)**:
    - Evaluates observation counts $N_g$ per subgroup with configurable threshold (default `MIN_SAMPLE_SIZE = 30`).
    - Emits prominent high-variance sampling warning (`has_sample_warning=True`) whenever $N_g < 30$.
    - Emits overall sample warning if total dataset $N < 30$.
  - **FA-4 (Missing Ground-Truth Validation & Isolation)**:
    - **EOD is strictly omitted (returns `None`)** when outcome labels are unavailable or partially missing, with explicit warnings preventing attrition bias.
    - If a subgroup has zero positive ground-truth instances, its recall is undefined (`None`) and EOD is omitted.
    - Zero division guards prevent errors on empty groups, 0 selections, or 0 ground truth.
    - **Complete data isolation**: Demographic evaluation datasets are strictly quarantined from applicant scoring tables (`candidate_responses`, `response_scores`, `session_alignments`) and recruiter reports.
  - **FA-5 (Controlled Dataset Ingestion & SQL Migration)**:
    - Pydantic validation rejects records missing both score and prediction, records with blank group names, and scores outside 0–100.
    - SQL migration [`docs/migrations/phase_c_fairness_evaluation.sql`](file:///c:/Users/purus/OneDrive/Documents/Desktop/AI-ASSISTED%20BEHAVIORAL%20JOB-FIT%20ASSESSMENT/docs/migrations/phase_c_fairness_evaluation.sql) creates `fairness_datasets` and `fairness_audits` tables with RLS policies restricting access to platform administrators.
  - **Regression Tests — `backend/tests/test_phase_c_fairness.py`** (NEW FILE, 24 tests):
    - `TestDemographicParityMetrics` (3 tests): known selection rates, continuous scores, Adverse Impact Ratio 80% rule.
    - `TestEqualOpportunityMetrics` (4 tests): complete ground truth, missing ground truth omits EOD, partial ground truth omits EOD, zero positive outcomes omits EOD.
    - `TestSampleCountWarnings` (3 tests): N < 30 warning, configurable threshold, overall small sample warning.
    - `TestEdgeCasesAndZeroDenominators` (4 tests): empty dataset, single group, zero selections, mandatory limitations.
    - `TestFairnessApiAuthorization` (4 tests): 401 unauthenticated, 403 ordinary recruiter, 200 platform admin, 201 direct evaluate.
    - `TestFairnessDataIsolation` (2 tests): candidate scoring model isolation, report schema isolation.

  - **Phase D (Recruiter Oversight and Audit Trails — OV-1 to OV-6) — COMPLETE**:
    - **OV-1 (Sample-Size & Fairness Limitations Warning)**:
      - Emits sample-size notices when responses < questions or responses < 3.
      - Emits evidence-quality notices when average similarity confidence < 0.45 or dimension confidence < 0.40.
      - Emits research-backed fairness caveat clarifying that passing statistical score thresholds does NOT prove absence of bias, and human recruiter judgment is required for all hiring decisions.
    - **OV-2 (Immutable Audit Logs & Credential Sanitization)**:
      - Persistent `audit_logs` table (`actor_id`, `actor_role`, `action`, `target_type`, `target_id`, `details`, `ip_address`, `user_agent`, `created_at`).
      - Service `AuditService` with recursive credential sanitizer `sanitize_audit_details` redacting passwords, tokens, API keys, and authorization headers.
      - Indexed for actor, target entity, action, and timestamp.
    - **OV-3 & OV-4 (Recruiter Review State & Tenant Isolation)**:
      - Additive columns on `session_alignments`: `reviewed_at`, `reviewed_by`, `review_action`, `recruiter_notes`, `override_score`.
      - Preserves deterministic assessment scores (`overall_score`); human overrides and notes are stored as auditable events rather than silent rewrites.
      - Enforces tenant isolation: recruiters can only review sessions for jobs they own (`job.recruiter_id == user.id`), with admin bypass.
    - **OV-5 (POST /api/sessions/{session_id}/review Endpoint)**:
      - Validates allowed review actions (`'reviewed'`, `'flagged_for_interview'`, `'request_reassessment'`, `'overridden'`, `'completed'`).
      - Validates authenticated recruiter permissions and job ownership.
      - Detects and tracks repeated submissions (`is_repeated_review=True`), preserving audit history.
    - **OV-6 (AssessmentReportPage.jsx UI Enhancements)**:
      - Displays Framework Snapshot Version badge in candidate header.
      - Displays Notices & Fairness Caveats warning banner (amber glassmorphism).
      - Displays Recruiter Oversight Card with current review status, human override score, reviewer identity, and notes.
      - Interactive review form supporting action selection, score override (0-100), and notes submission with instant optimistic UI update.
    - **Regression Tests — `backend/tests/test_phase_d_oversight.py`** (NEW FILE, 9 tests):
      - `test_sanitize_audit_details_redacts_credentials`
      - `test_log_event_records_and_retrieves`
      - `test_review_session_success`
      - `test_review_session_tenant_isolation_forbidden`
      - `test_review_session_admin_bypass_allowed`
      - `test_review_session_repeated_submission`
      - `test_review_session_invalid_action`
      - `test_review_session_not_found`
      - `test_report_includes_sample_size_and_fairness_caveat_warnings`

## Database: Apply Pending SQL
REQUIRED before deploying to live users:
Go to Supabase Dashboard > SQL Editor and run:
1. `docs/migrations/all_phases_a_b_c_d_consolidated.sql` — contains all schema updates, tables, indexes, and RLS policies for:
   - Phase A: `interview_sessions.framework_version_id` binding
   - Phase B: (Zero DDL; uses existing JSONB `response_scores.evidence`)
   - Phase C: `fairness_datasets`, `fairness_records`, `fairness_audits` tables + admin RLS
   - Phase D: `session_alignments` review columns (`reviewed_at`, `reviewed_by`, `review_action`, `recruiter_notes`, `override_score`) + `audit_logs` table + RLS
All statements use `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ADD COLUMN IF NOT EXISTS` and are strictly idempotent.

## Admin Account Setup
To grant an account Platform Administrator privileges:
1. Register/sign in with your user email in the application.
2. Go to Supabase Dashboard > SQL Editor and run:
   ```sql
   UPDATE profiles SET role = 'admin' WHERE id = (SELECT id FROM auth.users WHERE email = 'your_admin_email@example.com');
   ```
   Or update the user's `raw_user_meta_data`:
   ```sql
   UPDATE auth.users SET raw_user_meta_data = raw_user_meta_data || '{"role": "admin"}'::jsonb WHERE email = 'your_admin_email@example.com';
   ```
3. Refresh the application; the "⚙️ Framework Manager" navigation link will immediately appear.

## Important Decisions & Final Architecture
- **Architecture Philosophy**: Hybrid AI + Deterministic Analytics + Version-Controlled Frameworks + Human Oversight:
  - Generative AI (Groq / `openai/gpt-oss-120b`) is strictly restricted to qualitative tasks: JD requirement extraction and STAR interview question generation.
  - Behavioral Framework is fully administrator-managed with versioning and immutable snapshots.
  - All scoring, indicator matching, confidence ratings, and alignment calculations are 100% deterministic pure Python math. LLMs never calculate, invent, or hallucinate scores.
  - Evidence text extraction provides explainability via sentence grounding without modifying authoritative scoring math.
  - Demographic Fairness Audits (DPD, EOD, Subgroup Recall) run exclusively via controlled evaluation datasets in an isolated administrative governance boundary.
  - Recruiter Oversight & Audit Trails: Human decisions, qualitative notes, and score overrides are auditable events with complete credential sanitization; deterministic model outputs remain preserved.
  - Email Invitations: React → FastAPI → Supabase + Dual Email Engine (Gmail SMTP / Resend API).
- **Fairness & Ethics**:
  - Zero collection or utilization of protected/sensitive demographic attributes in live candidate assessments.
  - Zero psychiatric or clinical mental health diagnosis.
  - Zero automated hiring decisions ("Hire", "Reject", "Select").
  - Mandatory ethical compliance disclaimer displayed on all reports.
  - Mandatory human recruiter oversight at all decision stages.
- **Candidate Security**: Unguessable UUID tokens; no Supabase Auth credentials required for applicants; public schema completely conceals internal job weights, recruiter identities, scores, and email credentials.
- **Backend Stack**: FastAPI + Python 3.14 + Pydantic v2 + SentenceTransformers (`all-MiniLM-L6-v2`) + Supabase Python SDK + Groq API + smtplib / Resend SDK.
- **Frontend Stack**: Vite 8 + React 19 + Tailwind v4 + React Router v7.

## Tests
- **312/312 backend tests passing** (Python 3.14.2, pytest 9.1.1, 33.93s):
  - test_phase_d_oversight.py:          9 tests (NEW Phase 12D — OV-1 to OV-6)
  - test_phase_c_fairness.py:          24 tests (Phase 12C — FA-1 to FA-5)
  - test_phase_b_evidence.py:          26 tests (Phase 12B — ES-1 to ES-3)
  - test_phase_a_snapshot_binding.py: 17 tests (Phase 12A — FS-1 to FS-4)
  - test_admin_framework.py:          23 tests
  - test_health.py:                    3 tests
  - test_jobs.py:                     11 tests
  - test_schemas.py:                   8 tests
  - test_dimensions.py:               10 tests
  - test_analysis.py:                 13 tests
  - test_questions.py:                19 tests
  - test_sessions.py:                 19 tests
  - test_email_service.py:            16 tests
  - test_scoring.py:                  55 tests
  - test_alignment.py:                23 tests
  - test_reports.py:                  10 tests
  - test_validation_fairness.py:      21 tests
  - test_rate_limiter.py:              6 tests
- **Frontend**: clean production build (85 modules, 0 errors in 798ms)

## Remaining Risks & Recommendations
1. **Supabase SQL Migration**: Run `docs/migrations/all_phases_a_b_c_d_consolidated.sql` in the Supabase Dashboard SQL Editor prior to inviting real candidates or activating custom frameworks.
2. **Reverse Proxy Configuration**: Ensure production ingress / reverse proxy (e.g. Nginx, Cloudflare) sets the `X-Forwarded-For` header accurately for IP rate limiting.
3. **Gmail App Password Setup**: When using Gmail SMTP (`EMAIL_PROVIDER=smtp`), ensure **2-Step Verification** is enabled on your Google Account and enter your 16-character **App Password** in `SMTP_PASSWORD`.
4. **Admin Account Promotion**: Use the provided SQL snippet in Supabase SQL Editor to elevate authorized administrators.

## Project Status
Phase 12 (Fairness Features) — Phase A (Framework Snapshot Binding), Phase B (Evidence-Based Scoring Explanations), Phase C (Demographic Fairness Evaluation), and Phase D (Recruiter Oversight and Audit Trails) are COMPLETE.
312/312 backend tests passing (0 regressions). Clean frontend build (85 modules, 0 errors).
