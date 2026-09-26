# Project Memory

## Current Phase
Phase 7 -- Job-Candidate Behavioral Alignment -- COMPLETE

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

## Current Work
N/A -- Phase 7 complete.

## Database: Apply Pending SQL
REQUIRED before running Phase 5, Phase 6, and Phase 7 features in production:
Go to Supabase Dashboard > SQL Editor and run:
1. Lines 622-706: interview_sessions and candidate_responses tables + RLS policies (Phase 5)
2. Lines 708-759: response_scores table + RLS policies (Phase 6)
3. Lines 760-805: session_alignments table + RLS policies (Phase 7)
All statements use CREATE TABLE IF NOT EXISTS and are idempotent.

## Pending
- Phase 8: Results & Reporting Dashboard
  - Advanced candidate comparisons across applicants for the same job
  - Behavioral fit matrix & radar chart visualization
  - Exportable candidate evaluation reports (PDF / print view)
- Phase 9: Email delivery (optional)
  - Send candidate invite links by email (Resend / SendGrid)

## Important Decisions
- Python version: 3.14.2 (user system) -- pydantic>=2.13 + pydantic-core>=2.46 for Py3.14 support
- Groq model: llama3-70b-8192 (env var override available)
- NLP embedding model: all-MiniLM-L6-v2 (sentence-transformers)
- Scoring & Alignment determinism: 100% calculated by Python logic & cosine similarity rubrics (NO Groq hallucination in scores)
- Alignment formula: sum(candidate_score * job_weight) / sum(job_weight)
- Decision ethics: Strictly objective behavioral analytics; NO automated hire/reject recommendations or employment decisions
- Candidate access: UUID token, no Supabase Auth
- Database: Supabase PostgreSQL only -- no local DB
- RLS: enforced on ALL tables; service-role key used in backend only
- FastAPI lifespan: using asynccontextmanager (not deprecated on_event)
- Frontend: Vite 8 (Rolldown bundler) + React 19 + Tailwind v4 + React Router v7

## Tests
- 161/161 backend tests passing (Python 3.14.2, pytest 9.1.1)
  - test_health.py:      3 tests
  - test_jobs.py:       11 tests
  - test_schemas.py:     8 tests
  - test_dimensions.py: 10 tests
  - test_analysis.py:   13 tests
  - test_questions.py:  19 tests
  - test_sessions.py:   19 tests
  - test_scoring.py:    55 tests
  - test_alignment.py:  23 tests
- Frontend: clean production build (81 modules, 0 errors)

## Next Step
Phase 7 is complete.
Next step is Phase 8: Results & Reporting Dashboard (comparative analysis, fit visualizations, exportable reports).
