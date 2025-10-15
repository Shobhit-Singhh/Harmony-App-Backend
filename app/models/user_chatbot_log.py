# models/user_chatbot_log.py

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.config import Base


class UserChatbotLog(Base):
    __tablename__ = "user_chatbot_log"

    id = Column(UUID(as_uuid=True), ForeignKey("user_daily_log.id", ondelete="CASCADE"), primary_key=True, default=uuid.uuid4, unique=True, index=True)

    conversation = Column(JSON, nullable=False)   # [{role: user/assistant, content: text},..]
    analysis = Column(JSON, nullable=True)        # NLP analysis, sentiment, topics, etc.

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    daily_log = relationship("UserDailyLog", back_populates="chatbot_logs")