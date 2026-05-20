# Environment setup (Windows + Linux) and Docker deployment

This chapter describes how to set up the repository from a fresh GitHub clone, run it locally for development, and build/run a Docker image for external deployment.

## Prerequisites

- **Git** (to clone the repository)
- **Python 3.12** (backend)
- **Node.js** (frontend).
- **Docker** (optional; required for container builds)
  - Windows: Docker Desktop
  - Linux: Docker Engine + BuildKit

## 1) Clone the repository

```bash
git clone <REPO_URL>
cd blood-cvrp
```

## 2) Configure environment variables

The backend reads configuration from environment variables (and also from the project-root `.env` file).

Minimum required for full routing functionality:

- `ORS_API_KEY` – an OpenRouteService API key

Edit the project-root `.env` file and set the key:

```dotenv
ORS_API_KEY=your_openrouteservice_key_here
```


## 3) Local development run

### Backend (FastAPI)

From the repository root, create and activate a virtual environment, then install Python dependencies.

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

Run the API server:

```powershell
python -m uvicorn backend.src.main:app --reload --host 127.0.0.1 --port 8000
```

**Linux (bash):**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

Run the API server:

```bash
python -m uvicorn backend.src.main:app --reload --host 127.0.0.1 --port 8000
```

Sanity check:

- API health endpoint: `http://127.0.0.1:8000/api/v1/health/`

### Frontend (SvelteKit + Vite)

In a second terminal:

**Windows / Linux:**

```bash
cd frontend
npm ci
npm run dev
```

Open:

- Frontend dev server: `http://localhost:5173/`

The dev server proxies `GET/POST /api/*` to the backend at `http://127.0.0.1:8000` (see `frontend/vite.config.ts`).

## 4) Running tests (optional but recommended)

### Backend tests (pytest)

Install dev dependencies and run the suite from the repository root:

```bash
pip install -r backend/requirements-dev.txt
pytest
```

### Frontend unit tests (Vitest)

```bash
cd frontend
npm ci
npm test
```

### Frontend end-to-end tests (Playwright)

```bash
cd frontend
npm ci
npx playwright install
npm run test:e2e
```

## 5) Docker image build and run (external deployment)

The Docker build is a multi-stage build:

- builds the SvelteKit frontend into static files
- builds a Python runtime image that serves the API and mounts the frontend build at `/`

### Build

From the repository root:

```bash
docker build -t blood-cvrp:latest .
```

### Run

By default, the container listens on port `8080` (see `Dockerfile`). You must also provide `ORS_API_KEY`.

```bash
docker run --rm -p 8080:8080 -e ORS_API_KEY=your_openrouteservice_key_here blood-cvrp:latest
```

Open:

- App (frontend served by backend): `http://localhost:8080/`
- API health endpoint: `http://localhost:8080/api/v1/health/`

### Persisting the cache (optional)

The image includes the repository’s `storage/` directory at build time. For long-running deployments where you want the cache to persist across container restarts, mount a host volume:

**Linux:**

```bash
docker run --rm -p 8080:8080 \
  -e ORS_API_KEY=your_openrouteservice_key_here \
  -v "$(pwd)/storage:/app/storage" \
  blood-cvrp:latest
```

**Windows (PowerShell):**

```powershell
docker run --rm -p 8080:8080 `
  -e ORS_API_KEY=your_openrouteservice_key_here `
  -v "${PWD}\storage:/app/storage" `
  blood-cvrp:latest
```
