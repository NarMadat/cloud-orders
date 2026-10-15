import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database import Base, engine
from app.routers import health, orders
from app.schemas import AppInfo

# Setup logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cloud-orders-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} on {settings.hostname}")
    logger.info(f"Environment: {settings.APP_ENV}")
    # Initialize DB tables (for a real prod setup developers or devops might use alembic, but create_all is great out-of-the-box)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database schema: {e}")
    yield
    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="E-Commerce Orders Microservice built for DevOps learning path (Docker, CI/CD, K8s, Terraform, Ansible, AWS).",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics Instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Include Routers
app.include_router(health.router)
app.include_router(orders.router)


@app.get("/", tags=["General"])
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}!",
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_check": "/health",
        "metrics_url": "/metrics",
        "pod_hostname": settings.hostname
    }


@app.get("/api/v1/info", response_model=AppInfo, tags=["General"])
def app_info():
    return AppInfo(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        hostname=settings.hostname,
        features={
            "database_postgresql": not settings.USE_SQLITE,
            "database_sqlite": settings.USE_SQLITE,
            "redis_cache": settings.REDIS_ENABLED,
            "prometheus_metrics": True
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=(settings.APP_ENV == "development")
    )
