# models/user_recommendation.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Text, DateTime, JSON, Enum, Boolean, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.core.config import Base


class RecommendationSource(PyEnum):
    AI = "ai"
    CLINICIAN = "clinician"
    HYBRID = "hybrid"


class RecommendationType(PyEnum):
    ACTIVITY = "activity"
    JOURNAL_PROMPT = "journal_prompt"
    SELF_LETTER = "self_letter"
    NUDGE = "nudge"
    GOAL = "goal"
    GENERAL = "general"


class RecommendationStatus(PyEnum):
    PENDING = "pending"          # Waiting for clinician review
    APPROVED = "approved"        # Clinician validated
    REJECTED = "rejected"        # Clinician dismissed
    MODIFIED = "modified"        # Clinician edited AI suggestion


class UserRecommendation(Base):
    __tablename__ = "user_recommendation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_auth.id", ondelete="CASCADE"), nullable=False)
    
    # ---- Classification ----
    recommendation_type = Column(Enum(RecommendationType), default=RecommendationType.GENERAL, index=True)
    source = Column(Enum(RecommendationSource), default=RecommendationSource.AI)
    status = Column(Enum(RecommendationStatus), default=RecommendationStatus.PENDING, index=True)

    # ---- Recommendation Payload ----
    ai_recommendation = Column(JSON, nullable=True)          # {"text": "...", "score": 0.87, "context": {...}}
    clinician_recommendation = Column(JSON, nullable=True)   # {"text": "...", "comment": "..."}
    metadata = Column(JSON, nullable=True)                   # {"related_activity_id": "...", "tags": ["stress", "sleep"]}
    
    # ---- Context ----
    context_date = Column(DateTime, nullable=True)           # when it was generated/relevant
    reasioning = Column(Text, nullable=True)                # e.g., "Based on your recent stress levels..."

    # ---- Approval ----
    validated_by_clinician = Column(Boolean, default=False)
    validated_at = Column(DateTime, nullable=True)
    
    # ---- Metadata ----
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # ---- Relationship ----
    user = relationship("UserAuth", back_populates="recommendations")
