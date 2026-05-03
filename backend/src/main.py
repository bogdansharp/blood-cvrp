from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.src.data.routing_provider import ORSRoutingProvider
from backend.src.data.routing import RoutingData
from backend.src.solver.job_executor import JobExecutor

# from application.data_access import RUNS_DIR
from backend.src.api.routes.scenarios import router as scenarios_router
from backend.src.api.routes.hospitals import router as hospitals_router
from backend.src.api.routes.solutions import router as solutions_router
from backend.src.api.routes.jobs import router as jobs_router
from backend.src.api.routes.routing import router as routing_router
from backend.src.api.routes.health import router as health_router

from backend.src.data.json_repositories import create_repositories
from backend.src.settings import Settings, load_settings

# Load environment variables
load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # RUNS_DIR.mkdir(parents=True, exist_ok=True)
    
    settings: Settings = load_settings()
    max_workers = max(1, (os.cpu_count() or 2) - 1)

    app.state.settings = settings
    app.state.executor = JobExecutor(max_workers=max_workers)
    app.state.jobs = {}
    app.state.lock = threading.Lock()
    app.state.job_subscribers = {}
    app.state.repos = create_repositories(storage_root=settings.storage_root)
    app.state.routing_data = RoutingData(
        dist_repo=app.state.repos.distances,
        geom_repo=app.state.repos.geometries,
        routing=ORSRoutingProvider(
            ors_api_key=settings.ors_api_key,
            ors_base_url=settings.ors_base_url,
        ),
    )

    try:
        yield
    finally:
        app.state.executor.shutdown(cancel_futures=True)


app = FastAPI(title="Blood Routing CVRP API", lifespan=lifespan)
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(scenarios_router)
api_v1_router.include_router(hospitals_router)
api_v1_router.include_router(solutions_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(routing_router)
api_v1_router.include_router(health_router)
app.include_router(api_v1_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
