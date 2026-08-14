# Merit AI

Merit AI is an adaptive, evidence-backed engineering readiness assessment. It behaves like a structured
senior interviewer: questions respond to a candidate's background and previous evidence, practical
challenges test real engineering judgment, and every score remains explainable.

## Sprint 1 status

The FastAPI assessment engine supports:

- personalised first questions based on candidate projects and target role;
- controlled coverage of engineering fundamentals, problem solving, AI fluency, agentic engineering,
  and communication;
- one focused follow-up when evidence is weak, without sacrificing dimension coverage;
- practical debugging and agent-instruction challenges;
- Gemini structured-output evaluation with Pydantic validation;
- deterministic application-owned scoring and readiness classification;
- evidence, confidence, strengths, gaps, report, pathway, and proof-of-improvement challenge;
- resumable persistence through the Supabase repository;
- duplicate-response protection and a stable API contract.

## Architecture

```text
API client / Sprint 2 React app
            |
            v
         FastAPI
            |
     AssessmentService
       /           \
QuestionPlanner   GeminiEvaluator
       \           /
       evidence + deterministic scoring
                   |
                   v
            Supabase/PostgreSQL
```

The model evaluates evidence. Python controls state transitions, question coverage, score calculations,
classification, persistence, and recommendations.

## API

- `POST /api/v1/assessments` — create an assessment and receive the first question
- `POST /api/v1/assessments/{id}/responses` — evaluate a response and receive the next state
- `GET /api/v1/assessments/{id}` — retrieve/resume the current assessment
- `GET /api/v1/assessments/{id}/result` — retrieve the completed readiness result
- `GET /health` — health/configuration summary without exposing secrets
- `/docs` — interactive FastAPI Swagger demonstration

## Local setup

1. Copy `.env.example` to `.env` and fill the required values.
2. Create and activate a Python 3.11 virtual environment.
3. Install the backend and development dependencies.
4. Run tests, then start Uvicorn.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the Sprint 1 demo.

## Environment variables

See `.env.example`. `SUPABASE_SECRET_KEY` is backend-only and must never use a `VITE_` prefix or be
placed in the frontend. `.env` is intentionally ignored by Git.

## Known limitations

- Sprint 1 accepts text responses. Voice transcription belongs to Sprint 2 and is optional.
- Authentication UI and candidate ownership validation are Sprint 2 work. Database tables are already
  inaccessible to browser roles; all business operations flow through FastAPI.
- The repository can run in explicit `memory` mode for automated tests. The real application should use
  `supabase` mode.
