# Project Memory

## Current Phase
Phase 2 -- Behavioral Framework + API -- COMPLETE

## Completed
### Phase 0
- [x] Project structure, README.md, architecture.md, .gitignore, .env.example

### Phase 1
- [x] Backend: Python venv (.venv) with all dependencies (Python 3.14.2)
- [x] Backend: requirements.txt (fastapi, pydantic, supabase, uvicorn, pytest-env, etc.)
- [x] Backend: pyproject.toml with pytest config + env var injection for tests
- [x] Backend: app/core/config.py (pydantic-settings, all env vars)
- [x] Backend: app/core/security.py (Supabase JWT validation, require_recruiter dep)
- [x] Backend: app/db/client.py (anon + admin Supabase client singletons)
- [x] Backend: app/schemas/common.py, jobs.py, profiles.py
- [x] Backend: app/services/job_service.py (full CRUD, defense-in-depth recruiter_id filter)
- [x] Backend: app/services/profile_service.py (get, upsert, update)
- [x] Backend: app/api/health.py (/health, /health/db)
- [x] Backend: app/api/auth.py (GET /api/auth/me, PATCH /api/auth/profile)
- [x] Backend: app/api/jobs.py (full CRUD: POST/GET/PATCH/DELETE /api/jobs)
- [x] Backend: app/main.py (lifespan, CORS, all routers)
- [x] Backend: tests/conftest.py (env loading, auth override, Supabase mock)
- [x] Backend: tests/test_health.py (3 tests)
- [x] Backend: tests/test_jobs.py (11 tests)
- [x] Backend: tests/test_schemas.py (8 tests)
- [x] Backend: ALL 22 TESTS PASSING (Python 3.14, 0 deprecation warnings)
- [x] Database: docs/supabase_schema.sql (14 tables, RLS policies, seed data, triggers)
- [x] Frontend: Vite + React 19 scaffold
- [x] Frontend: Tailwind CSS v4 + @tailwindcss/vite
- [x] Frontend: react-router-dom, @supabase/supabase-js, recharts
- [x] Frontend: src/services/supabase.js (browser auth client)
- [x] Frontend: src/services/api.js (fetch wrapper, jobs/auth/health endpoints)
- [x] Frontend: src/context/AuthContext.jsx (session state, signIn/signUp/signOut)
- [x] Frontend: src/components/ProtectedRoute.jsx, Navbar.jsx
- [x] Frontend: src/pages/LoginPage.jsx, DashboardPage.jsx, JobsPage.jsx, CreateJobPage.jsx, JobDetailPage.jsx
- [x] Frontend: src/App.jsx (BrowserRouter, all routes)
- [x] Frontend: Clean production build -- 77 modules, 0 errors, 0 warnings

### Phase 2
- [x] Backend: app/schemas/dimensions.py (IndicatorRead, DimensionRead, DimensionDetail)
- [x] Backend: app/services/dimension_service.py (list, get, get_by_name, list_indicators)
- [x] Backend: app/api/dimensions.py (GET /api/dimensions, GET /api/dimensions/{id})
- [x] Backend: app/main.py updated -- dimensions router registered
- [x] Backend: tests/test_dimensions.py (10 tests: list, detail, 404, 422, service error, no-indicators)
- [x] Backend: ALL 32 TESTS PASSING (0 new warnings)
- [x] Frontend: src/services/api.js -- dimensionsApi added (list, get)
- [x] Frontend: src/pages/DimensionsPage.jsx (accordion card grid, per-dimension colors + icons)
- [x] Frontend: src/components/Navbar.jsx -- Dimensions nav link added
- [x] Frontend: src/App.jsx -- /dimensions route registered
- [x] Frontend: Clean production build -- 78 modules, 0 errors, 0 warnings
- [x] Git: Phase 2 committed to main branch

## Current Work
N/A -- Phase 2 complete.

## Pending
- Phase 3: Groq job analysis
  - Add GROQ_API_KEY to config + .env.example
  - Implement app/ai/groq_client.py (shared client, retry, error handling)
  - Implement app/ai/schemas.py (Pydantic I/O models for Groq responses)
  - Implement app/ai/job_analyzer.py (JD -> [{dimension, importance, reason}])
  - Implement app/services/job_requirement_service.py (save/list/confirm requirements)
  - Implement app/schemas/requirements.py
  - Add POST /api/jobs/{id}/analyze endpoint
  - Add GET/PATCH /api/jobs/{id}/requirements endpoints
  - Add JobDetailPage requirements section (review + confirm)
  - Tests: mock Groq, test job_analyzer, test requirements API

## Important Decisions
- Python version: 3.14.2 (user's system) -- using pydantic>=2.13 + pydantic-core>=2.46 for Py3.14 support
- Groq model: llama3-70b-8192 (env var override available)
- NLP embedding model: all-MiniLM-L6-v2 (Phase 7)
- Candidate access: UUID token, no Supabase Auth (Phase 6)
- Scoring: fully deterministic Python rubric; Groq extracts evidence only (Phase 8)
- Database: Supabase PostgreSQL only -- no local DB
- RLS: enforced on ALL 14 tables; service-role key used in backend only
- FastAPI lifespan: using asynccontextmanager (not deprecated on_event)
- Test strategy: pytest-env injects stub Supabase creds; Supabase client mocked; auth dep overridden
- Frontend: Vite 8 (Rolldown bundler) + React 19 + Tailwind v4 + React Router v7
- Dimensions API: read-only, public-read RLS -- no write endpoints needed in the app

## Files Changed (Phase 1)
### Backend
- backend/requirements.txt            -- created + updated (Py3.14 compat)
- backend/pyproject.toml              -- created (pytest config + env injection)
- backend/.env.test                   -- created (stub creds for CI)
- backend/app/__init__.py             -- created
- backend/app/main.py                 -- created (lifespan, CORS, routers)
- backend/app/core/__init__.py        -- created
- backend/app/core/config.py          -- created
- backend/app/core/security.py        -- created
- backend/app/db/__init__.py          -- created
- backend/app/db/client.py            -- created
- backend/app/schemas/__init__.py     -- created
- backend/app/schemas/common.py       -- created
- backend/app/schemas/jobs.py         -- created
- backend/app/schemas/profiles.py     -- created
- backend/app/services/__init__.py    -- created
- backend/app/services/job_service.py -- created
- backend/app/services/profile_service.py -- created
- backend/app/api/__init__.py         -- created
- backend/app/api/health.py           -- created
- backend/app/api/auth.py             -- created
- backend/app/api/jobs.py             -- created
- backend/tests/__init__.py           -- created
- backend/tests/conftest.py           -- created + updated
- backend/tests/test_health.py        -- created
- backend/tests/test_jobs.py          -- created
- backend/tests/test_schemas.py       -- created
### Database
- docs/supabase_schema.sql            -- created (full schema + RLS + seed)
### Frontend
- frontend/index.html                 -- updated
- frontend/vite.config.js             -- updated (Tailwind plugin, proxy)
- frontend/.env.example               -- created
- frontend/src/index.css              -- updated (Tailwind v4 + design tokens)
- frontend/src/main.jsx               -- updated
- frontend/src/App.jsx                -- updated (all routes)
- frontend/src/services/api.js        -- created
- frontend/src/services/supabase.js   -- created
- frontend/src/context/AuthContext.jsx       -- created
- frontend/src/components/ProtectedRoute.jsx -- created
- frontend/src/components/Navbar.jsx         -- created
- frontend/src/pages/LoginPage.jsx           -- created
- frontend/src/pages/DashboardPage.jsx       -- created
- frontend/src/pages/JobsPage.jsx            -- created
- frontend/src/pages/CreateJobPage.jsx       -- created
- frontend/src/pages/JobDetailPage.jsx       -- created

## Files Changed (Phase 2)
### Backend
- backend/app/schemas/dimensions.py          -- created (IndicatorRead, DimensionRead, DimensionDetail)
- backend/app/services/dimension_service.py  -- created (list, get, get_by_name, list_indicators)
- backend/app/api/dimensions.py              -- created (GET /api/dimensions, GET /api/dimensions/{id})
- backend/app/main.py                        -- updated (dimensions router added)
- backend/tests/test_dimensions.py           -- created (10 tests)
### Frontend
- frontend/src/services/api.js               -- updated (dimensionsApi added)
- frontend/src/pages/DimensionsPage.jsx      -- created (accordion card grid)
- frontend/src/components/Navbar.jsx         -- updated (Dimensions nav link)
- frontend/src/App.jsx                       -- updated (/dimensions route)

## Known Issues
- Starlette TestClient warns "Using httpx with starlette.testclient is deprecated; install httpx2"
  This is a Starlette upstream issue (httpx2 not published on PyPI yet). Not our code. Tests pass.
- Frontend build shows no errors. VITE_SUPABASE_URL must be set in frontend/.env.local before running.

## Tests
- 32/32 backend tests passing (Python 3.14.2, pytest 9.1.1)
  - test_health.py: 3 tests
  - test_jobs.py: 11 tests
  - test_schemas.py: 8 tests
  - test_dimensions.py: 10 tests
- Frontend: clean production build (78 modules, 0 errors)
- Run tests: cd backend && .venv\Scripts\pytest tests\ -v

## Next Step
WAIT for user instruction before starting Phase 3.
Phase 3 = Groq job analysis (JD -> behavioral requirements).
BEFORE STARTING: Ensure docs/supabase_schema.sql has been applied to your Supabase project.
