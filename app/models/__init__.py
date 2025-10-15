# app/models/__init__.py

from app.core.config import Base

# Import all models here so Alembic and app-wide imports work
from .user_auth import UserAuth
from .user_daily_logs import UserDailyLog
from .user_checkin import UserCheckin
from .user_journal import UserJournal
from .user_chatbot_log import UserChatbotLog
from .user_activity_tracker import UserActivityTracker
# from .user_sensor_data import UserSensorData   # Uncomment if you have this model

__all__ = [
    "Base",
    "UserAuth",
    "UserDailyLog",
    "UserCheckin",
    "UserJournal",
    "UserChatbotLog",
    "UserActivityTracker",
    # "UserSensorData",
]
