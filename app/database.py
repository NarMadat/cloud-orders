import logging
from typing import Generator
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy setup
connect_args = {"check_same_thread": False} if settings.USE_SQLITE else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False


# Redis setup
redis_client = None
if settings.REDIS_ENABLED:
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            decode_responses=True
        )
    except Exception as e:
        logger.warning(f"Failed to initialize Redis client: {e}")
        redis_client = None


def check_redis_connection() -> bool:
    if not settings.REDIS_ENABLED or redis_client is None:
        return True  # If redis disabled, don't fail readiness probe
    try:
        return bool(redis_client.ping())
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return False
