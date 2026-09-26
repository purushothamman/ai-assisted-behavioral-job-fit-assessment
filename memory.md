# Project Memory

## Current Phase
Phase 4 -- Question Generation -- COMPLETE

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
- [x] Backend: app/ai/schemas.py (DimensionRequirement, JobAnalysisOutput — Pydantic-validated)
- [x] Backend: app/ai/job_analyzer.py (analyze_job — prompt engineering + validation)
- [x] Backend: app/schemas/requirements.py (RequirementRead, RequirementConfirm)
- [x] Backend: app/services/job_requirement_service.py (save, list, update with ownership)
- [x] Backend: app/api/analysis.py (POST analyze, GET requirements, PATCH requirement)
- [x] Backend: app/main.py updated -- analysis router registered
- [x] Backend: requirements.txt -- groq>=1.7.0 added
- [x] Backend: tests/test_analysis.py (13 tests: analyze success/fail/503/422, list, confirm, ownership)
- [x] Backend: ALL 45 TESTS PASSING (0 new warnings)
- [x] Frontend: services/api.js -- analysisApi added (analyze, listRequirements, updateRequirement)
- [x] Frontend: JobDetailPage.jsx -- full Behavioral Requirements panel
  - "Analyze with AI" button -> calls Groq, shows results
  - Per-dimension importance bar + color badge (Critical/Important/Secondary)
  - Inline edit mode: slider for importance, textarea for reason
  - "Save & Confirm" per dimension, "Confirm All" batch action
  - Status badge on job header updates to "analyzed" after Groq call
- [x] Frontend: Clean production build (78 modules, 0 errors)

### Phase 4
- [x] Backend: app/ai/question_schemas.py (GeneratedQuestion, QuestionGeneratorOutput — Pydantic-validated)
- [x] Backend: app/ai/question_generator.py (generate_questions — STAR prompt, 2-3 questions/dim)
- [x] Backend: app/schemas/questions.py (QuestionRead, QuestionUpdate)
- [x] Backend: app/services/question_service.py (save w/ delete-then-insert, list, update, delete)
- [x] Backend: app/api/questions.py (4 endpoints: generate, list, PATCH, DELETE)
- [x] Backend: app/main.py updated -- questions router registered
- [x] Backend: tests/test_questions.py (19 tests: generate all paths, list, approve/edit, delete, schemas)
- [x] Backend: ALL 64 TESTS PASSING (0 errors)
- [x] Database: docs/supabase_schema.sql -- interview_questions table added (Phase 4 section)
  - type CHECK (behavioral/situational/competency)
  - difficulty CHECK (easy/medium/hard)
  - indicators JSONB column
  - Full RLS (select/insert/update/delete recruiter-scoped)
- [x] Frontend: services/api.js -- questionsApi added (generate, list, update, delete)
- [x] Frontend: JobDetailPage.jsx -- full Interview Questions panel
  - "Generate Questions" button (disabled until ≥1 requirement confirmed)
  - Questions grouped by behavioral dimension
  - Per-question: type badge, difficulty badge, approved badge, success indicators chips
  - Approve button (one-click), Edit (inline: question text, type, difficulty, indicators), Delete
  - "Approve All" batch action
  - Hint message when no confirmed requirements exist
  - Status badge updated to "questions_generated"
- [x] Frontend: Clean production build (78 modules, 0 errors)

## Current Work
N/A -- Phase 4 complete.

## Pending
- Phase 5: Candidate portal (UUID-token access, no Supabase Auth)
  - Generate candidate access tokens (UUID, stored in interview_sessions)
  - Public candidate endpoint (GET /api/sessions/{token}) -- fetch job + questions
  - POST /api/sessions/{token}/responses -- save candidate answers
  - Frontend: CandidatePage.jsx (token-gated, STAR-guided answer form per question)
  - Tests: candidate session flow

## Important Decisions
- Python version: 3.14.2 (user's system) -- using pydantic>=2.13 + pydantic-core>=2.46 for Py3.14 support
- Groq model: llama3-70b-8192 (env var override available)
- Groq error handling: GroqError (retryable) -> 503; ValueError (validation) -> 422; 4xx -> immediate fail
- Groq JSON mode: response_format={"type":"json_object"} used on all calls
- NLP embedding model: all-MiniLM-L6-v2 (Phase 7)
- Candidate access: UUID token, no Supabase Auth (Phase 6)
- Scoring: fully deterministic Python rubric; Groq extracts evidence only (Phase 8)
- Database: Supabase PostgreSQL only -- no local DB
- RLS: enforced on ALL tables; service-role key used in backend only
- FastAPI lifespan: using asynccontextmanager (not deprecated on_event)
- Test strategy: pytest-env injects stub Supabase creds; Supabase client mocked; auth dep overridden
- Frontend: Vite 8 (Rolldown bundler) + React 19 + Tailwind v4 + React Router v7
- Dimensions API: read-only, public-read RLS -- no write endpoints needed in the app
- Job analysis: upsert on (job_id, dimension_id) -- re-analyzing replaces previous output
- Question generation: delete-then-insert -- re-generating replaces entire previous batch
- Question PATCH/DELETE: job_id passed as query param for ownership check (avoids extra route nesting)

## Files Changed (Phase 4)
### Backend
- backend/app/ai/question_schemas.py              -- created (GeneratedQuestion, QuestionGeneratorOutput)
- backend/app/ai/question_generator.py            -- created (generate_questions, STAR prompt)
- backend/app/schemas/questions.py                -- created (QuestionRead, QuestionUpdate)
- backend/app/services/question_service.py        -- created (save, list, update, delete)
- backend/app/api/questions.py                    -- created (4 endpoints)
- backend/app/main.py                             -- updated (questions router added)
- backend/tests/test_questions.py                 -- created (19 tests)
### Frontend
- frontend/src/services/api.js                    -- updated (questionsApi added)
- frontend/src/pages/JobDetailPage.jsx            -- rewritten (Interview Questions panel added)
### Database
- docs/supabase_schema.sql                        -- updated (interview_questions table + RLS)

## Known Issues
- Starlette TestClient warns "Using httpx with starlette.testclient is deprecated; install httpx2"
  This is a Starlette upstream issue (httpx2 not published on PyPI yet). Not our code. Tests pass.
- Frontend build shows no errors. VITE_SUPABASE_URL must be set in frontend/.env.local before running.
- Groq analysis requires GROQ_API_KEY in backend/.env to work in production.
- Frontend chunk >500 kB warning (Vite info only -- not an error; code-splitting is a future optimisation).

## Tests
- 64/64 backend tests passing (Python 3.14.2, pytest 9.1.1)
  - test_health.py:      3 tests
  - test_jobs.py:       11 tests
  - test_schemas.py:     8 tests
  - test_dimensions.py: 10 tests
  - test_analysis.py:   13 tests
  - test_questions.py:  19 tests
- Frontend: clean production build (78 modules, 0 errors)
- Run tests: cd backend && .venv\Scripts\pytest tests\ -v

## Next Step
WAIT for user instruction before starting Phase 5.
Phase 5 = Candidate portal (UUID token, public endpoints, candidate response form).
BEFORE STARTING: Apply the Phase 4 interview_questions table addition in docs/supabase_schema.sql
to Supabase via Dashboard > SQL Editor.
