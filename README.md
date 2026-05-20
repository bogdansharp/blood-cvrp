# Blood Routing CVRP

A prototype planning system for Irish blood deliveries modelled as a Capacitated Vehicle Routing Problem (CVRP). It supports scenario-based experiments for daily depot-to-hospital deliveries using realistic Irish hospital/depot locations, road-network travel data, vehicle-capacity constraints, and estimated demand values (tested up to 132 locations within prototype scope).

The web app lets users create/edit/delete scenarios, run asynchronous solver jobs, and visualise routes on an interactive map (desktop + mobile). Backend: Python + FastAPI. Frontend: SvelteKit + TypeScript + Tailwind CSS + Leaflet.

Routing distance/time/geometry is obtained from OpenRouteService and cached locally to reduce repeated external API calls. Solvers include a custom Clarke–Wright Savings heuristic (optional 2-opt local search) and Google OR-Tools as a benchmark.

## Quickstart (local development)

Prerequisites: Git, Python 3.12, Node.js (Node 24 recommended for parity with Docker).

1) Clone

```bash
git clone <REPO_URL>
cd blood-cvrp
```

2) Configure env

Create a project-root `.env`:

```dotenv
ORS_API_KEY=your_openrouteservice_key_here
```

> A key is required for full routing/geometry; some runs may work from the existing `storage/` cache.

3) Backend (FastAPI)

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux (bash)
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r backend/requirements.txt
python -m uvicorn backend.src.main:app --reload --host 127.0.0.1 --port 8000
```

4) Frontend (SvelteKit)

```bash
cd frontend
npm ci
npm run dev
```

Open:

- App: http://localhost:5173/
- API health: http://127.0.0.1:8000/api/v1/health/

The frontend dev server proxies `/api/*` to the backend.

## More

- Full setup (Windows/Linux), tests, and Docker deployment: [docs/environment-setup.md](docs/environment-setup.md)

## Prototype scope

This is a research prototype (e.g. simplified demand modelling, file-based persistence, and external routing API limits); future work would add richer operational constraints and persistence.
