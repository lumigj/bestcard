import uvicorn
from fastapi import FastAPI

from bestcard.api.routes.health import router as health_router
from bestcard.api.routes.recommend import router as recommend_router
from bestcard.config import settings

app = FastAPI(title="BestCard API", version="0.1.0")
app.include_router(health_router)
app.include_router(recommend_router)


def run() -> None:
    uvicorn.run("bestcard.api.app:app", host=settings.app_host, port=settings.app_port, reload=False)
