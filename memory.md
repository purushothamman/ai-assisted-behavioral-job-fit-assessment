# Project Memory

## Current Phase
Phase 3 -- Groq Job Analysis -- COMPLETE

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

## Current Work
N/A -- Phase 3 complete.

## Pending
- Phase 4: Question generation (Groq)
  - Implement app/ai/question_generator.py (JD + confirmed requirements -> [{question, dimension, type, difficulty, indicators}])
  - Implement app/schemas/questions.py (QuestionRead, QuestionUpdate, QuestionCreate)
  - Implement app/services/question_service.py (save, list, update, delete)
  - Add POST /api/jobs/{id}/questions/generate
  - Add GET /api/jobs/{id}/questions
  - Add PATCH /api/questions/{id}
  - Add DELETE /api/questions/{id}
  - Add questions panel to JobDetailPage (approve / edit / delete questions)
  - Tests: mock Groq, test question generator, test questions API

## Important Decisions
- Python version: 3.14.2 (user's system) -- using pydantic>=2.13 + pydantic-core>=2.46 for Py3.14 support
- Groq model: llama3-70b-8192 (env var override available)
- Groq error handling: GroqError (retryable) -> 503; ValueError (validation) -> 422; 4xx -> immediate fail
- Groq JSON mode: response_format={"type":"json_object"} used on all calls
- NLP embedding model: all-MiniLM-L6-v2 (Phase 7)
- Candidate access: UUID token, no Supabase Auth (Phase 6)
- Scoring: fully deterministic Python rubric; Groq extracts evidence only (Phase 8)
- Database: Supabase PostgreSQL only -- no local DB
- RLS: enforced on ALL 14 tables; service-role key used in backend only
- FastAPI lifespan: using asynccontextmanager (not deprecated on_event)
- Test strategy: pytest-env injects stub Supabase creds; Supabase client mocked; auth dep overridden
- Frontend: Vite 8 (Rolldown bundler) + React 19 + Tailwind v4 + React Router v7
- Dimensions API: read-only, public-read RLS -- no write endpoints needed in the app
- Job analysis: upsert on (job_id, dimension_id) -- re-analyzing replaces previous output

## Files Changed (Phase 3)
### Backend
- backend/requirements.txt                         -- updated (groq>=1.7.0 added)
- backend/app/ai/groq_client.py                    -- created (shared client, retry, GroqError)
- backend/app/ai/schemas.py                        -- created (DimensionRequirement, JobAnalysisOutput)
- backend/app/ai/job_analyzer.py                   -- created (analyze_job, prompt template)
- backend/app/schemas/requirements.py              -- created (RequirementRead, RequirementConfirm)
- backend/app/services/job_requirement_service.py  -- created (save, list, update)
- backend/app/api/analysis.py                      -- created (3 endpoints)
- backend/app/main.py                              -- updated (analysis router added)
- backend/tests/test_analysis.py                   -- created (13 tests)
### Frontend
- frontend/src/services/api.js                     -- updated (analysisApi added)
- frontend/src/pages/JobDetailPage.jsx             -- rewritten (Behavioral Requirements panel)

## Known Issues
- Starlette TestClient warns "Using httpx with starlette.testclient is deprecated; install httpx2"
  This is a Starlette upstream issue (httpx2 not published on PyPI yet). Not our code. Tests pass.
- Frontend build shows no errors. VITE_SUPABASE_URL must be set in frontend/.env.local before running.
- Groq analysis requires GROQ_API_KEY in backend/.env to work in production.

## Tests
- 45/45 backend tests passing (Python 3.14.2, pytest 9.1.1)
  - test_health.py: 3 tests
  - test_jobs.py: 11 tests
  - test_schemas.py: 8 tests
  - test_dimensions.py: 10 tests
  - test_analysis.py: 13 tests
- Frontend: clean production build (78 modules, 0 errors)
- Run tests: cd backend && .venv\Scripts\pytest tests\ -v

## Next Step
WAIT for user instruction before starting Phase 4.
Phase 4 = Question generation (Groq: confirmed requirements -> interview questions).
BEFORE STARTING: Ensure GROQ_API_KEY is set in backend/.env and docs/supabase_schema.sql is applied.
