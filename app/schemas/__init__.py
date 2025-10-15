# app/schemas/__init__.py

# Base Schema
from .user_auth import (
    UserAuthBase,
    UserAuthPasswordHash,
    UserAuthVerification,
    UserAuthCreate,
    UserAuthUpdate,
    UserRole,
    Status,
    SuccessResponse
)
from .user_daily_logs import (
    UserCheckinBase,
    UserCheckinUpdate,
    UserCheckinRead,
    UserChatbotLogBase,
    UserChatbotLogUpdate,
    UserChatbotLogRead,
    UserJournalBase,
    UserJournalUpdate,
    UserJournalRead,
    JournalEntryRequest,
    UserActivityTrackerBase,
    UserActivityTrackerUpdate,
    UserActivityTrackerRead,
    UserDailyLogBase,
    UserDailyLogCreate,
    UserDailyLogUpdate,
    UserDailyLogRead,
    UserDailyLogList
)



__all__ = [
    # Auth
    "UserAuthBase", "UserAuthPasswordHash", "UserAuthVerification",
    "UserAuthCreate", "UserAuthRead", "UserAuthUpdate",
    "UserRole", "Status", "SuccessResponse",

    # Daily Logs
    "UserCheckinBase", "UserCheckinUpdate", "UserCheckinRead",
    "UserChatbotLogBase", "UserChatbotLogUpdate", "UserChatbotLogRead",
    "UserJournalBase", "UserJournalUpdate", "UserJournalRead", "JournalEntryRequest",
    "UserActivityTrackerBase", "UserActivityTrackerUpdate", "UserActivityTrackerRead",
    "UserDailyLogBase", "UserDailyLogCreate", "UserDailyLogUpdate", "UserDailyLogRead", "UserDailyLogList"
]
