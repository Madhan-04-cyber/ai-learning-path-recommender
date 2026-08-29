# PathMind AI

PathMind AI is a dependency-aware learning path recommender. It turns a learner's goal into a supported career track, assesses current skills, generates a prerequisite-safe roadmap, and adapts that roadmap through project evidence and feedback.

## Architecture

```text
Student
  |
Goal Analysis
  |
Career Classification
  |
Assessment
  |
Skill State
  |
Roadmap Engine
  |
Project Engine
  |
Project Evidence
  |
Skill Update
  |
Roadmap Recalculation
  |
AI Mentor
```

The deterministic backend is the source of truth. Gemini can improve wording, explain concepts, and help troubleshoot, but it does not control career classification, prerequisites, assessment correctness, mastery, evidence validity, milestone unlocking, or roadmap ordering.

## Core Systems

- **Goal classification:** maps supported technical goals to career blueprints and preserves `outside_scope` for unsupported professional goals.
- **Assessment engine:** selects career-relevant skills, validates generated question shape, uses deterministic fallbacks, and scores answers on the server.
- **Skill graph:** stores prerequisites, proficiency thresholds, resources, practice, and project relationships.
- **Roadmap engine:** topologically orders prerequisites and recalculates the next best action from verified skill state.
- **Project-Based Learning:** selects an adaptive project, then presents milestones, build tasks, checkpoints, hints, and validation checks.
- **Project Mentor:** uses project and learner context to explain the current milestone without changing milestone rules.
- **Evidence loop:** assessment and project evidence update skill proficiency and confidence, which drives roadmap adaptation.

## Environment Setup

Copy the example values into local environment files and replace only the placeholders:

```text
GEMINI_API_KEY=your_gemini_api_key_here
FRONTEND_URL=http://localhost:3000
PORT=8000
BACKEND_URL=http://localhost:8000
```

Never commit `.env` or real API keys. The frontend uses same-origin `/api/...` routes in production; `BACKEND_URL` is read server-side by the Next.js proxy.

## Run Locally

Backend, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend, in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. API documentation is available at `http://localhost:8000/docs`.

## Verification

From the repository root:

```powershell
python -m unittest discover -q
```

From `frontend`:

```powershell
npm run build
npm run lint
npm run test:e2e
```

Playwright expects a running frontend. Set `PLAYWRIGHT_BASE_URL` when using a non-default port.

## Known Limitations

- Gemini availability affects explanation quality, not deterministic path, assessment, evidence, or roadmap correctness.
- The frontend lint configuration still reports legacy hook and typing issues in older pages; these should be addressed in a dedicated refactor rather than mixed into behavior changes.
- Career classification supports the career blueprints defined in `main.py`; unsupported goals are intentionally not given a fabricated technical route.
