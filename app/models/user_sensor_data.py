# models/user_sensor_data.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, DateTime, JSON, Float, ForeignKey, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.config import Base


class UserSensorData(Base):
    __tablename__ = "user_sensor_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    daily_log_id = Column(UUID(as_uuid=True), ForeignKey("user_daily_log.id", ondelete="CASCADE"), nullable=False)

    # Sleep
    sleep_duration_minutes = Column(Float, nullable=True)  # total sleep time in minutes
    sleep_interruptions = Column(Integer, nullable=True)   # number of interruptions
    bedtime = Column(DateTime, nullable=True)
    wake_time = Column(DateTime, nullable=True)

    # Activity
    steps = Column(Integer, nullable=True)
    workouts = Column(JSON, nullable=True)                  # [{"type": "run", "duration": 30}, ...]
    sedentary_minutes = Column(Float, nullable=True)

    # Physiology
    heart_rate = Column(Float, nullable=True)              # bpm
    hrv = Column(Float, nullable=True)                     # heart rate variability
    stress_score = Column(Float, nullable=True)            # computed stress level

    # Digital habits
    screen_time_minutes = Column(Float, nullable=True)
    late_night_usage_minutes = Column(Float, nullable=True)
    relationship_activity = Column(JSON, nullable=True)          # {"calls": 5, "messages": 20}

    # Metadata
    custom_tags = Column(JSON, nullable=True)              # user-defined tags or notes
    meta = Column(JSON, nullable=True)                     # any additional metadata

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    daily_log = relationship("UserDailyLog", back_populates="sensor_data")
