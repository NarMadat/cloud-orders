from datetime import datetime
from fastapi import APIRouter, status, Response
from app.database import check_db_connection, check_redis_connection
from app.schemas import HealthStatus
from app.config import settings

router = APIRouter(prefix="/health", tags=["Health Checks"])


@router.get(
    "/live",
    summary="Liveness probe for Kubernetes",
    description="Returns 200 if the application process is running and responsive."
)
def liveness():
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get(
    "/ready",
    summary="Readiness probe for Kubernetes",
    description="Returns 200 if dependencies (database, cache) are reachable and ready to handle traffic."
)
def readiness(response: Response):
    db_ok = check_db_connection()
    redis_ok = check_redis_connection()

    if not db_ok or not redis_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "connected" if db_ok else "disconnected",
            "redis": "connected" if redis_ok else "disconnected",
            "timestamp": datetime.utcnow().isoformat()
        }

    return {
        "status": "ready",
        "database": "connected",
        "redis": "connected" if settings.REDIS_ENABLED else "disabled",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "",
    response_model=HealthStatus,
    summary="Comprehensive health check"
)
def full_health(response: Response):
    db_ok = check_db_connection()
    redis_ok = check_redis_connection()

    is_healthy = db_ok and redis_ok
    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthStatus(
        status="healthy" if is_healthy else "unhealthy",
        database="connected" if db_ok else "disconnected",
        redis="connected" if redis_ok else ("disabled" if not settings.REDIS_ENABLED else "disconnected"),
        timestamp=datetime.utcnow()
    )
