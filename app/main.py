from fastapi import FastAPI

from contextlib import asynccontextmanager

from app.api.routes.urls import router as url_router
from app.api.routes.redirect import router as redirect_router

from app.cache.cache_service import initialize_bloom_filter

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_bloom_filter()
    yield

app = FastAPI(
    title="Shortly",
    description="Distributed URL Shortener",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


app.include_router(url_router)
app.include_router(redirect_router)