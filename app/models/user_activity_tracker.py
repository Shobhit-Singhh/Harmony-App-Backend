# models/user_activity_tracker.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.core.config import Base


class UserActivityTracker(Base):
    """
    Daily activity tracking - one entry per activity per day.
    Configuration comes from user_priorities, this just tracks progress.
    """

    __tablename__ = "user_activity_tracker"

    id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_daily_log.id", ondelete="CASCADE"),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True,
    )

    # Activity arrays: [{name, description, pillars, dimension, unit, quota_value, reset_frequency, completed}, ...]
    health_activity = Column(JSON, nullable=False)
    work_activity = Column(JSON, nullable=False)
    growth_activity = Column(JSON, nullable=False)
    relationship_activity = Column(JSON, nullable=False)

    health_coping = Column(JSON, nullable=True)
    productivity_coping = Column(JSON, nullable=True)
    mindfulness_coping = Column(JSON, nullable=True)
    relationship_coping = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    daily_log = relationship("UserDailyLog", back_populates="activities")
