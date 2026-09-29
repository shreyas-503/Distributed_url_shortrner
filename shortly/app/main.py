from fastapi import FastAPI

from app.api.routes.urls import router as url_router
from app.api.routes.redirect import router as redirect_router


app = FastAPI(
    title="Shortly",
    description="Distributed URL Shortener",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


app.include_router(url_router)
app.include_router(redirect_router)