# models/user_priorities.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.config import Base
from sqlalchemy.orm import relationship


class UserPriorities(Base):
    __tablename__ = "user_priorities"

    # One-to-One PK link with user_auth
    id = Column(
        UUID(as_uuid=True), 
        ForeignKey("user_auth.id", ondelete="CASCADE"), 
        primary_key=True, 
        unique=True, 
        index=True, 
        nullable=False
    )

    # ---- Minimal Profile Info ----
    display_name = Column(String(255), nullable=True)
    age_group = Column(String(50), nullable=True)
    gender_identity = Column(String(50), nullable=True)
    preferred_pronouns = Column(String(50), nullable=True)

    # ---- Pillars Importance Ranking ----
    pillar_importance = Column(JSON, nullable=True)  # {"health": 0.35, "work": 0.25, ...}

    # ---- Health Pillar ----
    health_goals = Column(Text, nullable=True)
    health_baseline = Column(Text, nullable=True)
    health_activities = Column(JSON, nullable=True)  # List[CompleteActivity] as JSON

    # ---- Work Pillar ----
    work_goals = Column(Text, nullable=True)
    work_baseline = Column(Text, nullable=True)
    work_activities = Column(JSON, nullable=True)  # List[CompleteActivity] as JSON

    # ---- Growth Pillar ----
    growth_goals = Column(Text, nullable=True)
    growth_baseline = Column(Text, nullable=True)
    growth_activities = Column(JSON, nullable=True)  # List[CompleteActivity] as JSON

    # ---- Relationships Pillar ----
    relationships_goals = Column(Text, nullable=True)
    relationships_baseline = Column(Text, nullable=True)
    relationships_activities = Column(JSON, nullable=True)  # List[CompleteActivity] as JSON

    # ---- Preferences & Engagement ----
    checkin_schedule = Column(JSON, nullable=True)
    privacy_settings = Column(JSON, nullable=True)
    notification_preferences = Column(JSON, nullable=True)

    # ---- Metadata ----
    onboarding_completed_at = Column(DateTime, nullable=True)
    last_updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # ---- Relationship ----
    user = relationship("UserAuth", back_populates="priorities", uselist=False)