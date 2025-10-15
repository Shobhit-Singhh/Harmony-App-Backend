# models/user_journal.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.config import Base


class UserJournal(Base):
    __tablename__ = "user_journal"

    id = Column(UUID(as_uuid=True), ForeignKey("user_daily_log.id", ondelete="CASCADE"), primary_key=True, default=uuid.uuid4, unique=True, index=True)

    journal = Column(JSON, nullable=False)  # [Time: [Type, Content, Sentiment, Topics],...]
    analysis = Column(JSON, nullable=True)  # NLP analysis, sentiment, topics, etc.
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    daily_log = relationship("UserDailyLog", back_populates="journals")