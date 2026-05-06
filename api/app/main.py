from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.labels.models import Base
import app.claims.models  # noqa: F401 — register models with Base
import app.matching.models  # noqa: F401
import app.reviews.models  # noqa: F401
from app.labels.router import router as labels_router
from app.claims.router import router as claims_router
from app.reviews.router import router as reviews_router
from core.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="FDA Claims Intelligence",
    description="MLR Review Assistant — claim-by-claim validation against FDA-approved drug labels",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(labels_router)
app.include_router(claims_router)
app.include_router(reviews_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
