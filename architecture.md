# System Architecture

## AI-Assisted Behavioral Job-Fit Assessment

---

## 1. High-Level Architecture

```
+------------------+
|   React Frontend |  (Tailwind, React Router, Recharts)
+--------+---------+
         |  HTTPS REST
+--------v---------+
|   FastAPI Backend |
|   (Python 3.11+) |
+--+-----+-----+---+
   |     |     |
   v     v     v
Supabase  Groq  NLP
 (DB/Auth) (AI) (sentence-transformers)
```

---

## 2. Component Responsibilities

### 2.1 Supabase

| Responsibility | Details |
|----------------|---------|
| Authentication | Supabase Auth (JWT) for recruiters |
| Database       | PostgreSQL with RLS |
| Row Level Security | Recruiters see only their own data |
| Storage        | Candidate access tokens (if needed) |

### 2.2 FastAPI

| Responsibility | Details |
|----------------|---------|
| REST API       | All business logic endpoints |
| Auth middleware| Validates Supabase JWTs |
| Groq orchestration | Calls Groq; validates + structures responses |
| NLP pipeline   | Processes candidate answers |
| Scoring engine | Deterministic rubric calculations |
| Alignment      | Weighted job-candidate alignment |

### 2.3 Groq AI

| Responsibility | Details |
|----------------|---------|
| Job analysis   | Extract behavioral requirements from JD |
| Question generation | Generate role-specific questions |
| Evidence extraction | Extract behavioral evidence from answers |
| Report narrative | Generate recruiter-facing explanations |

**Groq NEVER determines final candidate scores or hire/reject decisions.**

### 2.4 NLP Pipeline

| Responsibility | Details |
|----------------|---------|
| Preprocessing  | Clean, tokenize, normalize candidate text |
| Embeddings     | sentence-transformers (all-MiniLM-L6-v2) |
| Semantic similarity | Cosine similarity vs indicator vectors |
| Indicator matching | Match responses to behavioral indicator library |

### 2.5 Python Scoring Engine

| Responsibility | Details |
|----------------|---------|
| Rubric scoring | 0-2 per indicator, deterministic rules |
| Normalization  | Scale to 0-100 per dimension |
| Weighted score | Apply job importance weights |
| Alignment      | Compute weighted job-candidate alignment |

---

## 3. Data Flow

### 3.1 Job Analysis Flow

```
Recruiter enters JD
        |
        v
POST /api/jobs/analyze
        |
        v
FastAPI -> Groq (structured JSON prompt)
        |
        v
Groq returns: [{dimension, importance, reason}]
        |
        v
Pydantic validation
        |
        v
Saved to: job_requirements table
        |
        v
Recruiter reviews/edits in UI
        |
        v
Status set to "confirmed" -> locked for assessment
```

### 3.2 Question Generation Flow

```
Recruiter triggers generate
        |
        v
POST /api/questions/generate
        |
        v
FastAPI -> Groq (JD + confirmed requirements)
        |
        v
Groq returns: [{question, dimension, type, difficulty, indicators}]
        |
        v
Pydantic validation
        |
        v
Saved to: questions table (status=draft)
        |
        v
Recruiter edits/approves
        |
        v
Selected questions added to assessment_questions
```

### 3.3 Response Analysis Flow

```
Candidate submits answers
        |
        v
POST /api/assessments/{id}/submit
        |
        v
For each response:
  1. Text preprocessing (clean, normalize)
  2. Embed with sentence-transformers
  3. Cosine similarity vs indicator embeddings
  4. Groq: extract evidence + positive/missing indicators
  5. Deterministic rubric: score each indicator 0-2
  6. Normalize dimension score to 0-100
  7. Store in: responses, response_analysis, behavioral_scores, evidence
        |
        v
Compute job-candidate alignment:
  alignment = SUM(candidate_score * job_weight) / SUM(job_weight)
        |
        v
Generate report narrative (Groq)
        |
        v
Recruiter reviews report, adds notes, makes final decision
```

---

## 4. Supabase Database Schema

### 4.1 Core Tables

```sql
-- User profiles (linked to Supabase Auth)
profiles (
  id            uuid PRIMARY KEY REFERENCES auth.users,
  role          text CHECK (role IN ('recruiter')),
  full_name     text,
  created_at    timestamptz DEFAULT now()
)

-- Jobs created by recruiters
jobs (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recruiter_id  uuid REFERENCES profiles(id),
  title         text NOT NULL,
  description   text,
  responsibilities text,
  requirements  text,
  status        text DEFAULT 'draft',
  created_at    timestamptz DEFAULT now(),
  updated_at    timestamptz DEFAULT now()
)

-- Six behavioral dimensions (seeded, not user-created)
behavioral_dimensions (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text UNIQUE NOT NULL,
  description   text,
  is_active     boolean DEFAULT true
)

-- Behavioral indicators per dimension (seeded)
behavioral_indicators (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dimension_id  uuid REFERENCES behavioral_dimensions(id),
  name          text NOT NULL,
  description   text,
  example_behaviors text
)

-- AI-extracted requirements per job (recruiter reviews/confirms)
job_requirements (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id        uuid REFERENCES jobs(id) ON DELETE CASCADE,
  dimension_id  uuid REFERENCES behavioral_dimensions(id),
  importance    int CHECK (importance BETWEEN 0 AND 100),
  reason        text,
  confirmed     boolean DEFAULT false,
  created_at    timestamptz DEFAULT now()
)

-- Interview questions
questions (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id        uuid REFERENCES jobs(id) ON DELETE CASCADE,
  dimension_id  uuid REFERENCES behavioral_dimensions(id),
  question_text text NOT NULL,
  question_type text CHECK (question_type IN ('behavioral','situational','scenario')),
  difficulty    text CHECK (difficulty IN ('easy','medium','hard')),
  indicators    jsonb,          -- array of indicator names targeted
  source        text DEFAULT 'ai',
  status        text DEFAULT 'draft',
  created_at    timestamptz DEFAULT now()
)

-- Assessments sent to candidates
assessments (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id        uuid REFERENCES jobs(id),
  recruiter_id  uuid REFERENCES profiles(id),
  token         text UNIQUE NOT NULL,
  status        text DEFAULT 'pending',
  created_at    timestamptz DEFAULT now(),
  submitted_at  timestamptz
)

-- Junction: which questions are in an assessment
assessment_questions (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_id uuid REFERENCES assessments(id) ON DELETE CASCADE,
  question_id   uuid REFERENCES questions(id),
  order_index   int
)

-- Candidate contact info (minimal PII)
candidates (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_id uuid REFERENCES assessments(id) ON DELETE CASCADE,
  name          text,
  email         text,
  created_at    timestamptz DEFAULT now()
)

-- Raw candidate responses
responses (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_id uuid REFERENCES assessments(id) ON DELETE CASCADE,
  question_id   uuid REFERENCES questions(id),
  candidate_id  uuid REFERENCES candidates(id),
  response_text text,
  word_count    int,
  submitted_at  timestamptz DEFAULT now()
)

-- NLP + Groq analysis of each response
response_analysis (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  response_id     uuid REFERENCES responses(id) ON DELETE CASCADE,
  dimension_id    uuid REFERENCES behavioral_dimensions(id),
  groq_evidence   jsonb,        -- extracted behavioral evidence
  positive_indicators jsonb,
  missing_indicators  jsonb,
  similarity_scores   jsonb,    -- NLP cosine similarity results
  confidence      float CHECK (confidence BETWEEN 0 AND 1),
  analyzed_at     timestamptz DEFAULT now()
)

-- Behavioral scores per dimension per candidate
behavioral_scores (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_id   uuid REFERENCES assessments(id) ON DELETE CASCADE,
  dimension_id    uuid REFERENCES behavioral_dimensions(id),
  raw_score       float,        -- 0-100
  normalized_score float,       -- 0-100
  evidence_count  int,
  created_at      timestamptz DEFAULT now()
)

-- Evidence items supporting each score
evidence (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  response_id     uuid REFERENCES responses(id) ON DELETE CASCADE,
  dimension_id    uuid REFERENCES behavioral_dimensions(id),
  indicator_id    uuid REFERENCES behavioral_indicators(id),
  evidence_text   text,
  score_contribution float,
  created_at      timestamptz DEFAULT now()
)

-- Final assessment report
assessment_reports (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_id   uuid UNIQUE REFERENCES assessments(id) ON DELETE CASCADE,
  overall_alignment float,
  dimension_scores  jsonb,
  strengths         jsonb,
  areas_for_review  jsonb,
  narrative         text,       -- Groq-generated explanation
  generated_at      timestamptz DEFAULT now()
)

-- Recruiter notes on a candidate
recruiter_notes (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assessment_id   uuid REFERENCES assessments(id) ON DELETE CASCADE,
  recruiter_id    uuid REFERENCES profiles(id),
  note_text       text,
  final_decision  text CHECK (final_decision IN ('proceed','reject','hold',NULL)),
  created_at      timestamptz DEFAULT now()
)
```

### 4.2 Row Level Security Policies

```
profiles:         users can read/update their own row
jobs:             recruiters access only their own jobs
job_requirements: accessible only via recruiter's own jobs
questions:        accessible only via recruiter's own jobs
assessments:      recruiters access own; candidates access via token
candidates:       recruiters see via their assessments only
responses:        recruiters see via their assessments; candidates write via token
response_analysis: recruiters only (via their jobs)
behavioral_scores: recruiters only (via their jobs)
evidence:          recruiters only (via their jobs)
assessment_reports: recruiters only (via their jobs)
recruiter_notes:   recruiter who created the note only
```

---

## 5. FastAPI Architecture

### 5.1 Module Structure

```
backend/app/
|-- main.py              # FastAPI app factory, middleware, CORS
|-- api/
|   |-- __init__.py
|   |-- deps.py          # Shared dependencies (DB, auth)
|   |-- jobs.py          # POST/GET/PATCH /jobs
|   |-- analysis.py      # POST /jobs/{id}/analyze
|   |-- questions.py     # POST /jobs/{id}/questions/generate
|   |-- assessments.py   # POST/GET /assessments
|   |-- candidates.py    # POST /assessments/{token}/submit
|   |-- reports.py       # GET /assessments/{id}/report
|   +-- notes.py         # POST /assessments/{id}/notes
|-- core/
|   |-- config.py        # Settings via pydantic-settings
|   |-- security.py      # JWT validation (Supabase)
|   +-- dependencies.py  # get_current_user, get_db
|-- schemas/
|   |-- jobs.py
|   |-- questions.py
|   |-- assessments.py
|   |-- candidates.py
|   |-- responses.py
|   |-- reports.py
|   +-- common.py
|-- services/
|   |-- job_service.py
|   |-- question_service.py
|   |-- assessment_service.py
|   |-- analysis_service.py
|   +-- report_service.py
|-- ai/                  # Groq integration only
|   |-- groq_client.py
|   |-- job_analyzer.py
|   |-- question_generator.py
|   |-- response_analyzer.py
|   |-- report_generator.py
|   +-- schemas.py       # Pydantic models for Groq I/O
|-- nlp/
|   |-- preprocessor.py
|   |-- embeddings.py
|   |-- similarity.py
|   +-- indicator_matcher.py
|-- scoring/
|   |-- rubrics.py
|   |-- behavioral_score.py
|   |-- normalization.py
|   +-- alignment.py
+-- db/
    |-- client.py        # Supabase Python client
    +-- queries.py       # Typed query helpers
```

### 5.2 Key API Endpoints

| Method | Endpoint                              | Auth       | Description                        |
|--------|---------------------------------------|------------|------------------------------------|
| POST   | /auth/verify                          | JWT        | Verify Supabase token              |
| POST   | /jobs                                 | Recruiter  | Create a new job                   |
| GET    | /jobs                                 | Recruiter  | List recruiter's jobs              |
| GET    | /jobs/{id}                            | Recruiter  | Get job detail                     |
| POST   | /jobs/{id}/analyze                    | Recruiter  | Groq: extract behavioral requirements |
| PATCH  | /jobs/{id}/requirements/{req_id}      | Recruiter  | Edit/confirm requirement           |
| POST   | /jobs/{id}/questions/generate         | Recruiter  | Groq: generate questions           |
| PATCH  | /questions/{id}                       | Recruiter  | Edit a question                    |
| DELETE | /questions/{id}                       | Recruiter  | Delete a question                  |
| POST   | /assessments                          | Recruiter  | Create assessment + token          |
| GET    | /assessments/{id}                     | Recruiter  | Get assessment detail              |
| GET    | /assessments/{id}/report              | Recruiter  | Get full behavioral report         |
| POST   | /assessments/{token}/submit           | Token only | Candidate submits answers          |
| POST   | /assessments/{id}/notes               | Recruiter  | Add recruiter note / final decision|

---

## 6. Groq Integration

### 6.1 Prompt Engineering Principles

- All prompts use structured JSON output mode
- System prompt defines strict JSON schema expected
- Every response validated with Pydantic before use
- Retry up to 3 times on malformed output
- Graceful fallback if Groq unavailable

### 6.2 Groq Modules

| Module | Responsibility |
|--------|---------------|
| groq_client.py | Shared client, retry logic, error handling |
| job_analyzer.py | Prompt: JD -> [{dimension, importance, reason}] |
| question_generator.py | Prompt: JD + requirements -> [{question, ...}] |
| response_analyzer.py | Prompt: answer -> {evidence, indicators, confidence} |
| report_generator.py | Prompt: scores + evidence -> narrative text |
| schemas.py | Pydantic models for all Groq I/O |

### 6.3 Error Handling

- API key missing: fail at startup with clear message
- Timeout: retry with backoff, fallback to empty result
- Rate limit: exponential backoff, surface error to caller
- Malformed JSON: retry, log raw output, return structured error
- Empty response: return null evidence, do not crash scoring

---

## 7. NLP Pipeline

### 7.1 Pipeline Steps

```
Raw candidate answer
        |
        v
1. Preprocessing
   - Lowercase, strip HTML
   - Remove excess whitespace
   - Tokenize sentences
        |
        v
2. Embedding
   - Model: all-MiniLM-L6-v2 (sentence-transformers)
   - Embed candidate answer
   - Embed each behavioral indicator description
        |
        v
3. Cosine Similarity
   - Compute similarity(answer_embedding, indicator_embedding)
   - Score threshold: >= 0.35 = evidence present
        |
        v
4. Indicator Matching
   - Aggregate per-indicator similarity scores
   - Identify top-N matching indicators per dimension
        |
        v
Combined with Groq evidence
        |
        v
Input to Scoring Engine
```

### 7.2 Model Choice Rationale

- `all-MiniLM-L6-v2`: compact, fast, strong semantic performance
- Runs locally, no external API cost
- Suitable for CPU inference

---

## 8. Scoring Methodology

### 8.1 Rubric (per indicator, 0-2)

```
0 = No evidence found in response
1 = Weak or indirect evidence found
2 = Clear, explicit evidence found
```

### 8.2 Dimension Score (0-100)

```
dimension_score =
  (SUM of indicator_scores) / (num_indicators * 2) * 100
```

### 8.3 Job-Candidate Alignment (0-100)

```
alignment =
  SUM(dimension_score_i * job_weight_i) / SUM(job_weight_i)
```

Where `job_weight_i` is the importance (0-100) assigned to dimension i by Groq
and confirmed by the recruiter.

### 8.4 Reporting

Every score in the report must link to:
- Evidence quotes from candidate responses
- Indicator names that were/were not found
- Confidence level from NLP similarity

---

## 9. Security Design

| Concern | Solution |
|---------|---------|
| Auth | Supabase Auth JWT, validated in FastAPI |
| RLS | Postgres RLS per table |
| Candidate access | Random UUID token, no login required |
| Secrets | Environment variables only, never in code |
| Input validation | Pydantic on all inputs |
| CORS | Strict origin allowlist |
| PII | Minimal: only name + email for candidates |
| Prohibited inferences | Not stored, not computed |

---

## 10. Evaluation Plan (Phase 10)

### 10.1 Evaluation Dataset

```
evaluation_dataset.csv:
  question | dimension | candidate_response | human_score | indicators
```

### 10.2 Metrics

| Metric | Purpose |
|--------|---------|
| MAE    | Mean absolute error vs human scores |
| RMSE   | Root mean squared error |
| Pearson r | Correlation with human scores |
| Cohen kappa | Inter-rater agreement (ordinal) |
| Precision/Recall/F1 | Indicator detection |

### 10.3 Fairness Checks

- Verify score distributions are not systematically different across demographic
  groups (if voluntary disclosure data is available)
- Evaluate consistency: same answer -> same score across runs
- Evaluate evidence grounding: every score has an evidence chain
