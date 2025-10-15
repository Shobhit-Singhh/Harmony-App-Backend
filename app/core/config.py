from typing import Generator, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from pydantic_settings import BaseSettings
import os


# =====================================================================
# SETTINGS
# =====================================================================


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Harmony API"
    DEBUG: bool = True

    # Database (updated path — use persistent folder for Render)
    DATABASE_URL = os.getenv("DATABASE_URL")

    # JWT
    SECRET_KEY: str = "Supersecretkey"
    REFRESH_SECRET_KEY: str = "Harmonysecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS - Simple list without reading from settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://harmony-app-frontend.onrender.com",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


# =====================================================================
# DATABASE
# =====================================================================

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    ),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
