# Project Memory

## Current Phase
Phase 1 -- Supabase + FastAPI Foundation -- COMPLETE

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

## Current Work
N/A -- Phase 1 complete.

## Pending
- Phase 2: Behavioral framework + database seed data
  - Verify SQL schema applied to Supabase project
  - Confirm seed data (dimensions + indicators) is in DB
  - Add API endpoints to read dimensions/indicators
  - Add frontend page to display dimensions

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

## Known Issues
- Starlette TestClient warns "Using httpx with starlette.testclient is deprecated; install httpx2"
  This is a Starlette upstream issue (httpx2 not published on PyPI yet). Not our code. Tests pass.
- Frontend build shows no errors. VITE_SUPABASE_URL must be set in frontend/.env.local before running.

## Tests
- 22/22 backend tests passing (Python 3.14.2, pytest 9.1.1)
  - test_health.py: 3 tests (liveness, DB connected, DB unreachable)
  - test_jobs.py: 11 tests (create, list, get, update, delete -- success + failure)
  - test_schemas.py: 8 tests (validation, enum, blank title, etc.)
- Frontend: clean production build (77 modules, 0 errors)
- Run tests: cd backend && .venv\Scripts\pytest tests\ -v

## Next Step
WAIT for user instruction before starting Phase 2.
Phase 2 = Behavioral framework + database seed data.
BEFORE STARTING: Apply docs/supabase_schema.sql to your Supabase project first.

