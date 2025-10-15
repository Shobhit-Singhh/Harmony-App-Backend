# models/user_insight.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, JSON, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.config import Base


class UserInsight(Base):
    __tablename__ = "user_insight"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_auth.id", ondelete="CASCADE"), nullable=False)

    # ---- a. Demographics & Background ----
    age = Column(Integer, nullable=True)
    living_situation = Column(String(255), nullable=True)
    occupation = Column(String(255), nullable=True)
    marital_status = Column(String(50), nullable=True)
    education_level = Column(String(255), nullable=True)

    # ---- b. Medical & Mental Health History ----
    prior_diagnoses = Column(JSON, nullable=True)
    family_history = Column(JSON, nullable=True)
    current_medications = Column(JSON, nullable=True)
    therapy_history = Column(JSON, nullable=True)
    lab_results = Column(JSON, nullable=True)

    # ---- c. Lifestyle & Risk Factors ----
    sleep_pattern = Column(String(255), nullable=True)
    exercise_habits = Column(String(255), nullable=True)
    substance_use = Column(String(255), nullable=True)
    nutrition_pattern = Column(String(255), nullable=True)
    risk_behaviors = Column(JSON, nullable=True)

    # ---- d. Psychological Assessment Scales ----
    assessment_scales = Column(JSON, nullable=True)
    resilience_score = Column(JSON, nullable=True)
    coping_score = Column(JSON, nullable=True)

    # ---- e. Caregiver Notes & Conclusion ----
    caregiver_notes = Column(Text, nullable=True)
    therapy_goals = Column(JSON, nullable=True)
    clinician_summary = Column(Text, nullable=True)

    # ---- Metadata ----
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    assessed_by = Column(UUID(as_uuid=True), nullable=True)
    assessment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # ---- Relationship ----
    user = relationship("UserAuth", back_populates="insight")