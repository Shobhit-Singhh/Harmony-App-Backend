# models/user_auth.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, ForeignKey, Enum as SqlEnum
)
import enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.config import Base

class UserRole(enum.Enum):
    user = "user"
    professional = "professional"
    admin = "admin"

class Status(enum.Enum):
    active = "active"
    suspended = "suspended"
    deactivated = "deactivated"

class UserAuth(Base):
    __tablename__ = "user_auth"

    # ---- Base fields ----
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    username = Column(String(50), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SqlEnum(UserRole), default=UserRole.user)

    # ---- Account status & verification ----
    status = Column(SqlEnum(Status), default=Status.active)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    
    # ---- Security & login tracking ----
    last_login_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    lockout_until = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)

    # ---- Relationships ----
    insight = relationship("UserInsight", back_populates="user", uselist=False, cascade="all, delete-orphan")
    priorities = relationship("UserPriorities", back_populates="user", uselist=False, cascade="all, delete-orphan")
    daily_logs = relationship("UserDailyLog", back_populates="user", cascade="all, delete-orphan")
    # recommendations = relationship("UserRecommendation", back_populates="user", cascade="all, delete-orphan")