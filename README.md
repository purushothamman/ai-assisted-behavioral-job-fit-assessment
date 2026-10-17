# AI-Assisted Behavioral Job-Fit Assessment

> **MSc Data Science Project**
> An AI-assisted decision-support system that evaluates job-related behavioral
> characteristics of candidates and compares them against role requirements.
> The final hiring decision always belongs to a human recruiter.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [System Architecture](#3-system-architecture)
4. [Behavioral Dimensions](#4-behavioral-dimensions)
5. [User Roles](#5-user-roles)
6. [Project Structure](#6-project-structure)
7. [Getting Started](#7-getting-started)
8. [Environment Variables](#8-environment-variables)
9. [Development Phases](#9-development-phases)
10. [Ethical Principles](#10-ethical-principles)
11. [License](#11-license)

---

## 1. Project Overview

This system supports recruiters by:

- Analyzing a job description with Groq AI to extract behavioral requirements
- Generating role-specific behavioral/situational interview questions
- Collecting candidate responses via a secure assessment portal
- Running an NLP + deterministic scoring pipeline on responses
- Producing an explainable, evidence-grounded behavioral profile
- Computing job-candidate alignment scores
- Generating a structured report for the human recruiter to review

**This is an assistive tool.** It does not make hiring decisions. It does not
diagnose psychological conditions. It only evaluates job-related behavioral indicators.

---

## 2. Technology Stack

| Layer    | Technology                                    |
|----------|-----------------------------------------------|
| Frontend | React, Tailwind CSS, React Router, Recharts   |
| Backend  | Python, FastAPI, Pydantic                     |
| Database | Supabase PostgreSQL                           |
| Auth     | Supabase Auth                                 |
| AI       | Groq API (LLaMA 3 70B)                        |
| NLP      | sentence-transformers, scikit-learn           |
| Data     | numpy, pandas                                 |

---

## 3. System Architecture

```
Job Description
      |
  Groq AI  ---- Behavioral Requirements Extraction
      |
Role-Specific Questions (10-15)
      |
Candidate Answers (Secure Portal)
      |
  NLP Pipeline  ---- Embeddings + Semantic Similarity
      +
  Groq AI  ---- Evidence Extraction (not scoring)
      |
Behavioral Indicators + Evidence
      |
Python Scoring Engine  ---- Deterministic Rubric
      |
Behavioral Profile + Alignment Score
      |
Explainable Report
      |
Human Recruiter (Final Decision)
```

---

## 4. Behavioral Dimensions & Framework

The platform includes a baseline set of six default behavioral dimensions, but is fully extensible via the **Admin-Managed Behavioral Framework Engine (Phase 11)**:

| Dimension        | Key Observable Indicators                                             |
|------------------|-----------------------------------------------------------------------|
| Communication    | Clarity, active listening, information sharing, conflict communication |
| Teamwork         | Collaboration, responsibility, conflict resolution, supportiveness     |
| Adaptability     | Flexibility, handling change, alternative planning, learning new processes |
| Decision Making  | Information evaluation, risk consideration, prioritization, action taking |
| Leadership       | Responsibility, delegation, accountability, coordination, motivation   |
| Stress Management| Prioritization, competing demands, task focus, organizing urgent work  |

> **Note:** Stress Management evaluates only job-related behavioral responses to
> workplace pressure. No psychological or medical conditions are assessed.

Authorized Platform Administrators can create custom competencies (e.g. `strategic_thinking`, `customer_centricity`), configure observable indicators, validate framework integrity, and publish immutable versioned releases (`framework_versions`).

---

## 5. User Roles

### Platform Administrator (`role: admin`)

- Access the Framework Control Center at `/admin/framework`
- Create, edit, activate/draft, reorder, and safely delete/archive dimensions
- Manage observable behavioral indicators per dimension
- Run pre-activation framework validation checks
- Publish and activate new framework versions with frozen immutable snapshots
- Inspect historical framework release snapshots

### Recruiter (`role: recruiter`)

- Register/login via Supabase Auth
- Create and manage job listings
- Run AI-assisted behavioral job description analysis
- Review and approve required competencies and importance weights
- Generate, edit, delete, or manually add STAR assessment questions
- Create assessment sessions and invite candidates via email (Gmail SMTP / Resend)
- View candidate behavioral profiles, evidence citations, and weighted alignment scores
- Add recruiter notes and make the final human hiring decision

### Candidate (Public Assessment Portal)

- Access assessment via a secure single-use token link (no login required)
- Answer behavioral/situational questions using the STAR framework
- Submit assessment responses with instant confirmation
- Strict data isolation: candidate portal cannot access internal weights, recruiter identities, or scoring algorithms

---

## 6. Project Structure

```
project/
|
|-- frontend/                   # React + Tailwind UI
|   |-- src/
|   |   |-- components/
|   |   |-- pages/
|   |   |-- hooks/
|   |   |-- services/
|   |   +-- utils/
|   +-- public/
|
|-- backend/
|   |-- app/
|   |   |-- api/               # FastAPI route handlers
|   |   |-- core/              # Config, security, dependencies
|   |   |-- schemas/           # Pydantic models
|   |   |-- services/          # Business logic services
|   |   |-- ai/                # Groq integration
|   |   |-- nlp/               # NLP pipeline
|   |   |-- scoring/           # Deterministic scoring
|   |   +-- db/                # Supabase client + helpers
|   +-- tests/
|
|-- data/
|   |-- seed/                  # Seed data for dimensions/indicators
|   +-- evaluation/            # Evaluation dataset
|
|-- notebooks/                 # Jupyter notebooks for analysis
|-- docs/                      # Extended documentation
|
|-- memory.md                  # Project development memory (read first!)
|-- README.md
|-- architecture.md
|-- .env.example
+-- .gitignore
```

---

## 7. Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project (free tier is sufficient)
- A Groq API key

### Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Copy .env.example to .env and fill in your values
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## 8. Environment Variables

Copy `.env.example` to `.env` and fill in all values.

| Variable                   | Description                              |
|----------------------------|------------------------------------------|
| GROQ_API_KEY               | Groq API key                             |
| GROQ_MODEL                 | Model name (default: llama3-70b-8192)    |
| SUPABASE_URL               | Your Supabase project URL                |
| SUPABASE_ANON_KEY          | Supabase anonymous key                   |
| SUPABASE_SERVICE_ROLE_KEY  | Supabase service role key (backend only) |
| APP_SECRET_KEY             | FastAPI JWT secret                       |
| APP_CORS_ORIGINS           | Allowed frontend origin(s)               |

**Never commit `.env`** -- it is listed in `.gitignore`.

---

## 9. Development Phases

| Phase | Description                                                | Status     |
|-------|------------------------------------------------------------|------------|
| 0     | Planning, architecture, project structure                  | Complete   |
| 1     | Supabase PostgreSQL + FastAPI security foundation          | Complete   |
| 2     | Baseline behavioral framework + indicators seed            | Complete   |
| 3     | Groq AI behavioral requirements extraction from JD         | Complete   |
| 4     | AI question generation (STAR methodology)                  | Complete   |
| 5     | Candidate assessment portal + token authentication         | Complete   |
| 6     | SentenceTransformers NLP + deterministic rubric scoring    | Complete   |
| 7     | Pure math job-candidate alignment weighting                | Complete   |
| 8     | Explainable candidate evaluation reports + PDF generation  | Complete   |
| 9     | Dual email dispatch engine (Gmail SMTP + Resend API)       | Complete   |
| 10    | Production hardening, security, rate limiting, fairness    | Complete   |
| 11    | Admin-managed behavioral framework & immutable versioning  | Complete   |

---

## 10. Platform Administrator Setup

To promote an authenticated user to Platform Administrator:

1. Register or log in to the application.
2. In Supabase Dashboard > SQL Editor, execute:
   ```sql
   UPDATE profiles SET role = 'admin' WHERE id = (SELECT id FROM auth.users WHERE email = 'your_admin_email@example.com');
   ```
3. Refresh the app. The **⚙️ Framework Manager** link will appear in the navigation bar.

---

## 10. Ethical Principles

- This system is a **decision-support tool**, not an automated hiring system.
- The final decision always belongs to a **human recruiter**.
- The system does **not** infer or store: race, religion, political beliefs,
  sexual orientation, medical conditions, or mental-health conditions.
- Stress Management evaluates only job-related behavioral responses to workplace pressure.
- Every score must be accompanied by **explainable evidence** from candidate responses.
- Groq extracts evidence; Python calculates scores. Groq never determines hiring outcomes.

---

## 11. License

Developed as part of an MSc Data Science thesis. All rights reserved.
