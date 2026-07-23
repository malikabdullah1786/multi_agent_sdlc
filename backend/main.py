import os
import logging
from contextlib import asynccontextmanager

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import engine, Base
from backend.routers.projects import router as projects_router
from backend.routers.tasks import router as tasks_router
from backend.routers.workflows import router as workflows_router
from backend.routers.approvals import router as approvals_router
from backend.routers.logs import router as logs_router
from backend.routers.files import router as files_router
from backend.routers.terminal import router as terminal_router
from backend.routers.ws import router as ws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager to initialize database tables on startup."""
    logger.info("Initializing AgenticDB tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("AgenticDB tables ready.")
    yield
    logger.info("Shutting down backend...")

app = FastAPI(
    title="Multi-Agent SDLC Orchestrator API",
    description="Backend API connecting the Multi-Agent SDLC Orchestrator to AgenticDB and Frontend UI.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration - Allow all origins for seamless frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers directly at root level
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(workflows_router)
app.include_router(approvals_router)
app.include_router(logs_router)
app.include_router(files_router)
app.include_router(terminal_router)
app.include_router(ws_router)

@app.get("/")
async def root_health_check():
    """Health check endpoint."""
    return {
        "status": "HEALTHY",
        "service": "SDLC Orchestrator Backend API",
        "database": "AgenticDB"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
