from fastapi import APIRouter
from .runs import router as runs_router
from .analytics import router as analytics_router
from .health import router as health_router

api_router = APIRouter(prefix="/api")

api_router.include_router(runs_router)
api_router.include_router(analytics_router)
api_router.include_router(health_router)
