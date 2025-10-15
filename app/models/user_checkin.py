# models/user_checkin.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.config import Base


class UserCheckin(Base):
    __tablename__ = "user_checkin"

    #  i want one to one relationship with daily log, means same id used in daily log will be used here
    id = Column(UUID(as_uuid=True), ForeignKey("user_daily_log.id", ondelete="CASCADE"), primary_key=True, default=uuid.uuid4, unique=True, index=True)

    mood = Column(JSON, nullable=False)  # key value pair key: time, value: Enum: happy, sad, anxious, angry, neutral
    stress_level = Column(JSON, nullable=False)  # key value pair key: time, value: Enum: low, medium, high
    energy_level = Column(JSON, nullable=False)  # key value pair key: time, value: Enum: low, medium, high
    sleep = Column(JSON, nullable=False)  # key value pair key: time, value: [Duration: int, Enum: good, average, poor]
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    daily_log = relationship("UserDailyLog", back_populates="checkins")