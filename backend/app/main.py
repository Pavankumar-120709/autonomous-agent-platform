import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import init_db
from .api.router import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("agent.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Autonomous Agent Platform...")
    await init_db()
    logger.info("Database initialized. Ready to serve agent execution requests.")
    yield
    logger.info("Shutting down Autonomous Agent Platform.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade Autonomous Research Agent Platform with Bounded Execution & Step-Level Logging.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "message": "Autonomous Agent Platform API",
        "docs": "/docs",
        "health": "/api/health",
        "version": "1.0.0",
    }
