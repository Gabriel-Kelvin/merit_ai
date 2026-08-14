# Merit AI

Merit AI is an adaptive, evidence-backed engineering readiness assessment. It behaves like a structured senior interviewer: questions respond to a candidate's background and previous evidence, difficulty changes when warranted, and every score remains explainable.

## Assessment engine

The FastAPI backend supports:

- personalised questions using candidate projects, stack, target role, and AI tools;
- controlled coverage of engineering fundamentals, problem solving, AI fluency, agentic engineering, and communication;
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
- candidate profile and project-context capture;
- one-question-at-a-time adaptive assessment presentation;
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
         /           \
QuestionPlanner   GeminiEvaluator
         \           /
       evidence + deterministic calibration
                   |
                   v
            Supabase/PostgreSQL
```

Gemini evaluates evidence. Python controls state transitions, capability coverage, difficulty, stopping, score calculations, classification, persistence, and recommendations.

## API

- `POST /api/v1/assessments` - start an assessment and receive a personalised question
- `POST /api/v1/assessments/{id}/responses` - evaluate an answer and receive the adaptive decision
- `GET /api/v1/assessments/{id}` - retrieve or resume the exact assessment state
- `GET /api/v1/assessments/{id}/result` - retrieve the completed evidence-backed result
- `GET /api/v1/assessment-methodology` - inspect rubric weights and adaptive stopping rules
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

## Security and scope

`SUPABASE_SECRET_KEY` is backend-only and must never use a `VITE_` prefix or be placed in the frontend. `.env` is intentionally ignored by Git. Browser roles cannot directly access assessment tables; business operations flow through FastAPI.

The practical IDE challenge, payment, GitHub integration, and deployment are intentionally out of scope while the assessment backend is being perfected. Assessments currently accept text responses; voice transcription remains optional.
