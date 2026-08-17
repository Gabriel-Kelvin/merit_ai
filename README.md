# Merit AI

Merit AI is an adaptive, evidence-backed engineering readiness assessment. It behaves like a structured senior interviewer: questions respond to a candidate's background and previous evidence, difficulty changes when warranted, and every score remains explainable.

## Assessment engine

The FastAPI backend supports:

- an AI-generated capability blueprint tailored to each candidate's role and background;
- role-native questions recomposed after every answer from accumulated evidence and uncertainty;
- a checkpointed LangGraph controller for conversation memory, topic switching, coverage, and
  state transitions;
- a guaranteed “Tell me about yourself” opening followed by adaptive experience, project,
  role-capability, and professional-judgment evidence gathering;
- AI-selected 2, 3, or 5 minute limits with refresh-safe expiry and automatic partial submission;
- dynamic early stopping with a hard maximum of 20 questions;
- visible per-answer decisions: probe a gap, increase difficulty, advance, or stop;
- intelligent stopping based on evidence quantity, quality, confidence, and dimension coverage;
- Gemini structured-output evaluation with prompt-injection boundaries and deterministic calibration;
- Gemini 3.1 Flash-Lite as primary with an OpenRouter free-model-only fallback;
- per-response evaluator model auditing when fallback is used;
- application-owned scoring with confidence gating and evidence-quality adjustment;
- signal-level verdicts, confidence labels, limiting gaps, and a complete evaluation trace;
- resumable Supabase persistence;
- idempotent replay plus database-level duplicate-response protection;
- fully described Swagger and ReDoc contracts with examples and documented errors.

## Candidate experience

The React candidate application includes:

- a premium, focused landing experience;
- candidate signup and email/password login through Supabase Auth, with immediate access and no
  email-verification step;
- signed, HttpOnly application sessions, logout, and account-isolated profiles and assessments;
- PDF, DOCX, and TXT resume parsing with selective profile autofill;
- structured work history, achievements, certifications, projects, and readable resume context
  retained for question personalization while the raw upload is discarded;
- one-question-at-a-time adaptive assessment presentation;
- browser-level question-copy and answer-paste deterrents;
- professional processing and recoverable error states;
- refresh/resume using a versioned assessment identifier;
- readiness score, dimension evidence, confidence, strengths, gaps, and recommendations;
- a specific development priority and printable report;
- responsive desktop and mobile layouts.

## Architecture

```text
API client / React candidate app
              |
              v
           FastAPI
              |
       AssessmentService
              |
   LangGraph state controller
         /           \
QuestionPlanner   GeminiEvaluator
         \           /
       evidence + deterministic calibration
                   |
                   v
            Supabase/PostgreSQL
```

Gemini generates the role-specific blueprint and adaptive questions, then evaluates answer evidence.
LangGraph updates the thread state and routes each transition. Python validates structured outputs
and controls safe coverage, calibrated scoring, stopping, persistence, and recommendations.

## API

- `POST /api/v1/auth/signup` - create a candidate account and session
- `POST /api/v1/auth/login` - sign in with email/password or the local demo account
- `GET /api/v1/auth/me` - inspect the current session
- `POST /api/v1/auth/logout` - clear the session
- `POST /api/v1/assessments` - start an assessment and receive a personalised question
- `POST /api/v1/assessments/{id}/responses` - evaluate an answer and receive the adaptive decision
- `GET /api/v1/assessments/{id}` - retrieve or resume the exact assessment state
- `GET /api/v1/assessments/{id}/result` - retrieve the completed evidence-backed result
- `GET /api/v1/assessment-methodology` - inspect rubric weights and adaptive stopping rules
- `POST /api/v1/resumes/parse` - extract supported profile fields without storing the raw resume
- `GET /health` - health and active backend configuration without secrets
- `/docs` - interactive Swagger UI
- `/redoc` - structured API reference
- `/openapi.json` - OpenAPI 3 contract

## Local setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the backend demonstration.

Start the candidate app in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` for the candidate experience.

The default local demo credentials are `demo` / `MeritDemo@2026`. New candidates can instead
create their own account. Change the demo password and session secret in `.env` before sharing a
separate environment.

## Production

- Candidate app: `https://merit-ai-chi.vercel.app`
- API: `https://merit-ai-api.onrender.com`
- Swagger: `https://merit-ai-api.onrender.com/docs`

## Security and scope

`SUPABASE_SECRET_KEY` is backend-only and must never use a `VITE_` prefix or be placed in the frontend. `.env` is intentionally ignored by Git. Browser roles cannot directly access assessment tables; business operations flow through FastAPI.

The practical IDE challenge and payment integration are intentionally outside the current scope.
Assessments currently accept text responses; voice transcription remains optional.

The copy/paste controls are assessment-integrity deterrents, not an absolute browser security boundary. Screenshots, developer tools, and external devices cannot be reliably blocked by a web application.
