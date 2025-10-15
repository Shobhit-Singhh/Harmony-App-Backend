# models/user_daily_log.py

import uuid
from datetime import datetime, timezone, date
from sqlalchemy import (
    Column, Date, DateTime, JSON, ForeignKey, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.config import Base


class UserDailyLog(Base):
    __tablename__ = "user_daily_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_auth.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)

    # Optional summary snapshot — end of day AI or aggregation
    current_status_summary = Column(Text, nullable=True)

    frequency = Column(JSON, nullable=True)  # {"checkin": int, "journal": int, "chat": int}
    active_hours = Column(JSON, nullable=True)  # {"start": time, "end": time}

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    checkins = relationship("UserCheckin", back_populates="daily_log", cascade="all, delete-orphan")
    journals = relationship("UserJournal", back_populates="daily_log", cascade="all, delete-orphan")
    chatbot_logs = relationship("UserChatbotLog", back_populates="daily_log", cascade="all, delete-orphan")
    activities = relationship("UserActivityTracker", back_populates="daily_log", cascade="all, delete-orphan")
    # sensor_data = relationship("UserSensorData", back_populates="daily_log", cascade="all, delete-orphan")
    
    user = relationship("UserAuth", back_populates="daily_logs")
