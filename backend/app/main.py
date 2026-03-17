from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import Base, engine
from app.routers import evaluations, jobs, reports

# Create all tables on startup (use Alembic migrations for production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Teacher Evaluation Analysis API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(evaluations.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
