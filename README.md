# PathMind AI

PathMind AI is a dependency-aware learning GPS. It maps a career goal to a structured skill graph, calculates learner gaps, identifies bottlenecks, and replans after assessments and feedback.

## Run Locally

### Backend

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GEMINI_API_KEY = "your-gemini-api-key"
uvicorn main:app --reload --port 8000
```

The API is available at `http://localhost:8000` and its OpenAPI docs at `http://localhost:8000/docs`.

### Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend defaults to the backend URL above; set `NEXT_PUBLIC_BACKEND_URL` when using a deployed API.

## Validate

```powershell
python -m unittest test_engine.py -v
cd frontend
npm run build
```

The backend falls back to its structured career and skill graph when `GEMINI_API_KEY` is unavailable, so path generation and adaptive demonstrations remain usable.