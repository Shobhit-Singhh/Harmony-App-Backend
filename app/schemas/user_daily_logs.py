from __future__ import annotations
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID
from datetime import datetime, date

from pydantic import BaseModel, Field


# ----------------------
# Generic / Shared Types
# ----------------------
JSONDict = Dict[str, Any]
JSONList = List[Dict[str, Any]]


# ----------------------
# UserCheckin Schemas
# ----------------------
class sleepEntry(BaseModel):
    duration: int
    quality: str


class UserCheckinBase(BaseModel):
    mood: Dict[str, str] = Field(
        ...,
        description="Key-value pairs of ISO timestamp and mood (explain in your own words)",
    )
    stress_level: Dict[str, str] = Field(
        ...,
        description="Key-value pairs of ISO timestamp and stress level (explain in your own words)",
    )
    energy_level: Dict[str, str] = Field(
        ...,
        description="Key-value pairs of ISO timestamp and energy level (explain in your own words)",
    )
    sleep: Dict[str, sleepEntry] = Field(
        ...,
        description="Key-value pairs of ISO timestamp and sleep details {duration: int, quality: str (explain in your own words)}",
    )


class UserCheckinUpdate(BaseModel):
    mood: Optional[Dict[str, str]] = None
    stress_level: Optional[Dict[str, str]] = None
    energy_level: Optional[Dict[str, str]] = None
    sleep: Optional[Dict[str, sleepEntry]] = None


class UserCheckinRead(UserCheckinBase):
    id: UUID
    created_at: datetime
    last_updated_at: datetime

    class Config:
        orm_mode = True


# ----------------------
# UserJournal Schemas
# ----------------------


class UserJournalBase(BaseModel):
    journal: Dict[str, List[Any]] = Field(
        default_factory=dict,
        description="Dictionary keyed by ISO timestamp, value=[type, content, sentiment, topics]",
    )
    analysis: Optional[JSONDict] = Field(
        None, description="NLP analysis, sentiment, topics, etc."
    )


class UserJournalUpdate(BaseModel):
    journal: Optional[Dict[str, List[Any]]] = None
    analysis: Optional[JSONDict] = None


class UserJournalRead(UserJournalBase):
    id: UUID
    created_at: datetime
    last_updated_at: datetime

    class Config:
        orm_mode = True


class JournalEntryRequest(BaseModel):
    content: str
    entry_type: Optional[str] = "text"
    sentiment: Optional[str] = None
    topics: Optional[List[str]] = []
    timestamp: Optional[datetime] = None


class JournalEntryUpdateRequest(BaseModel):
    content: Optional[str] = None
    entry_type: Optional[str] = None
    sentiment: Optional[str] = None
    topics: Optional[List[str]] = None


class JournalActionRequest(BaseModel):
    """Request for adding/updating journal entries"""

    content: str
    entry_type: Optional[str] = "text"
    sentiment: Optional[str] = None
    topics: Optional[List[str]] = []
    timestamp: Optional[datetime] = None


# ----------------------
# UserChatbotLog Schemas
# ----------------------


class UserChatbotLogBase(BaseModel):
    conversation: List[JSONDict] = Field(
        ..., description="List of message objects: {role: str, content: str}"
    )
    analysis: Optional[JSONDict] = Field(
        None, description="NLP analysis, sentiment, topics, etc."
    )


class UserChatbotLogUpdate(BaseModel):
    conversation: Optional[List[JSONDict]] = None
    analysis: Optional[JSONDict] = None


class UserChatbotLogRead(UserChatbotLogBase):
    id: UUID
    created_at: datetime
    last_updated_at: datetime

    class Config:
        orm_mode = True


class UserActivityTrackerBase(BaseModel):
    """Base schema for activity tracker."""

    health_activity: JSONList = Field(
        default_factory=list, description="List of activity objects for health pillar"
    )
    work_activity: JSONList = Field(
        default_factory=list,
        description="List of activity objects for work/productivity pillar",
    )
    growth_activity: JSONList = Field(
        default_factory=list,
        description="List of activity objects for growth/mindfulness pillar",
    )
    relationship_activity: JSONList = Field(
        default_factory=list,
        description="List of activity objects for social/relationships pillar",
    )
    health_coping: JSONList = Field(
        default_factory=list,
        description="List of coping activity objects for health pillar",
    )
    productivity_coping: JSONList = Field(
        default_factory=list,
        description="List of coping activity objects for productivity pillar",
    )
    mindfulness_coping: JSONList = Field(
        default_factory=list,
        description="List of coping activity objects for mindfulness pillar",
    )
    relationship_coping: JSONList = Field(
        default_factory=list,
        description="List of coping activity objects for social pillar",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "health_activity": [
                    {
                        "name": "Morning Walk",
                        "description": "Daily morning walk",
                        "pillar": "health",
                        "configuration": {
                            "dimension": "distance",
                            "complete": 5000,
                            "unit": "steps",
                            "quota": {"value": 10000, "reset_frequency": "daily"},
                        },
                    }
                ],
                "work_activity": [],
                "growth_activity": [],
                "relationship_activity": [],
                "health_coping": [],
                "productivity_coping": [],
                "mindfulness_coping": [],
                "relationship_coping": [],
            }
        }


class UserActivityTrackerUpdate(BaseModel):
    """Schema for updating activity tracker."""

    health_activity: Optional[JSONList] = None
    work_activity: Optional[JSONList] = None
    growth_activity: Optional[JSONList] = None
    relationship_activity: Optional[JSONList] = None
    health_coping: Optional[JSONList] = None
    productivity_coping: Optional[JSONList] = None
    mindfulness_coping: Optional[JSONList] = None
    relationship_coping: Optional[JSONList] = None


class UserActivityTrackerRead(UserActivityTrackerBase):
    """Schema for reading activity tracker."""

    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =====================================================================
# Activity Update Schemas
# =====================================================================


class ActivityUpdateRequest(BaseModel):
    """Request to update an activity's complete value."""

    complete: int = Field(
        ..., ge=0, description="New complete/covered value (must be non-negative)"
    )
    category: Optional[str] = Field(
        None, description="Category to search in (health, work, growth, relationship)"
    )

    class Config:
        json_schema_extra = {"example": {"complete": 7500, "category": "health"}}


class ActivityIncrementRequest(BaseModel):
    """Request to increment an activity's complete value."""

    increment: int = Field(
        ...,
        description="Amount to increment complete value (can be negative to decrement)",
    )
    category: Optional[str] = Field(
        None, description="Category to search in (health, work, growth, relationship)"
    )

    class Config:
        json_schema_extra = {"example": {"increment": 1000, "category": "health"}}


class ActivityResetRequest(BaseModel):
    """Request to reset activity or activities."""

    category: Optional[str] = Field(None, description="Optional category filter")


# =====================================================================
# Progress Response Schemas
# =====================================================================


class ProgressSummaryResponse(BaseModel):
    """Summary of daily activity progress."""

    total: int = Field(..., description="Total number of activities")
    completed: int = Field(..., description="Number of activities that met quota")
    in_progress: int = Field(
        ..., description="Number of activities started but not completed"
    )
    not_started: int = Field(
        ..., description="Number of activities not started (complete=0)"
    )
    completion_rate: float = Field(
        ..., description="Percentage of activities completed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "total": 10,
                "completed": 3,
                "in_progress": 5,
                "not_started": 2,
                "completion_rate": 30.0,
            }
        }


class StreakResponse(BaseModel):
    """Activity streak information."""

    activity_name: str = Field(..., description="Name of the activity")
    current_streak: int = Field(..., description="Current consecutive days")
    longest_streak: int = Field(..., description="Longest streak in the period")
    days_checked: int = Field(default=30, description="Number of days analyzed")

    class Config:
        json_schema_extra = {
            "example": {
                "activity_name": "Morning Walk",
                "current_streak": 7,
                "longest_streak": 14,
                "days_checked": 30,
            }
        }


class ActivityDetailResponse(BaseModel):
    """Detailed information about a specific activity."""

    name: str
    description: str
    pillar: str
    configuration: Dict[str, Any]
    complete_percentage: Optional[float] = Field(
        None, description="Completion percentage (0-100)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Morning Walk",
                "description": "Daily morning walk for fitness",
                "pillar": "health",
                "configuration": {
                    "dimension": "distance",
                    "complete": 7500,
                    "unit": "steps",
                    "quota": {"value": 10000, "reset_frequency": "daily"},
                },
                "complete_percentage": 75.0,
            }
        }


class CategoryProgressResponse(BaseModel):
    """Progress summary for a specific category."""

    category: str
    activities: List[Dict[str, Any]]
    total_activities: int
    completed_activities: int
    completion_rate: float

    class Config:
        json_schema_extra = {
            "example": {
                "category": "health",
                "activities": [
                    {
                        "name": "Morning Walk",
                        "complete": 7500,
                        "quota": 10000,
                        "percentage": 75.0,
                    }
                ],
                "total_activities": 3,
                "completed_activities": 1,
                "completion_rate": 33.33,
            }
        }


# =====================================================================
# Bulk Update Schemas
# =====================================================================


class BulkActivityUpdateRequest(BaseModel):
    """Request to update multiple activities at once."""

    updates: List[Dict[str, Any]] = Field(
        ..., description="List of activity updates with name and complete value"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "updates": [
                    {"name": "Morning Walk", "complete": 10000},
                    {"name": "Meditation", "complete": 15},
                    {"name": "Reading", "complete": 30},
                ]
            }
        }


class BulkUpdateResponse(BaseModel):
    """Response for bulk update operations."""

    success_count: int = Field(
        ..., description="Number of activities successfully updated"
    )
    error_count: int = Field(..., description="Number of failed updates")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    message: str = Field(..., description="Overall result message")

    class Config:
        json_schema_extra = {
            "example": {
                "success_count": 2,
                "error_count": 1,
                "errors": ["Activity 'Invalid' not found"],
                "message": "Bulk update completed: 2 succeeded, 1 failed",
            }
        }


# =====================================================================
# Analytics Schemas
# =====================================================================


class ActivityAnalyticsRequest(BaseModel):
    """Request for activity analytics over a period."""

    activity_name: str = Field(..., description="Name of activity to analyze")
    start_date: datetime = Field(..., description="Start date for analysis")
    end_date: datetime = Field(..., description="End date for analysis")
    category: Optional[str] = Field(None, description="Optional category filter")


class ActivityAnalyticsResponse(BaseModel):
    """Analytics data for an activity over time."""

    activity_name: str
    period_days: int
    total_complete: int = Field(..., description="Total complete value over period")
    average_daily: float = Field(..., description="Average daily complete value")
    days_active: int = Field(..., description="Number of days with complete > 0")
    days_completed: int = Field(..., description="Number of days meeting quota")
    completion_rate: float = Field(..., description="Percentage of days meeting quota")
    current_streak: int
    longest_streak: int

    class Config:
        json_schema_extra = {
            "example": {
                "activity_name": "Morning Walk",
                "period_days": 30,
                "total_complete": 285000,
                "average_daily": 9500.0,
                "days_active": 28,
                "days_completed": 25,
                "completion_rate": 83.33,
                "current_streak": 7,
                "longest_streak": 14,
            }
        }


# =====================================================================
# Validation Response Schema
# =====================================================================


class ActivityValidationResponse(BaseModel):
    """Response for activity validation checks."""

    is_valid: bool
    activity_name: str
    exists: bool
    has_quota: bool
    can_track_progress: bool
    messages: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": True,
                "activity_name": "Morning Walk",
                "exists": True,
                "has_quota": True,
                "can_track_progress": True,
                "messages": [],
            }
        }


# =====================================================================
# Success Response
# =====================================================================


class ActivitySuccessResponse(BaseModel):
    """Generic success response for activity operations."""

    message: str
    activity_name: str
    complete_value: Optional[int] = None
    category: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Activity updated successfully",
                "activity_name": "Morning Walk",
                "complete_value": 10000,
                "category": "health",
            }
        }


# ----------------------
# UserDailyLog Schemas
# ----------------------
class UserDailyLogBase(BaseModel):
    user_id: UUID
    date: date
    current_status_summary: Optional[str] = None
    frequency: Optional[JSONDict] = Field(
        None, description='{"checkin": int, "journal": int, "chat": int}'
    )
    active_hours: Optional[JSONDict] = Field(
        None, description='{"start": "HH:MM", "end": "HH:MM"}'
    )


class UserDailyLogCreate(UserDailyLogBase):
    # Optional nested one-to-one relations at creation time
    checkin: Optional[UserCheckinBase] = None
    chatbot_log: Optional[UserChatbotLogBase] = None
    journal: Optional[UserJournalBase] = None
    activities: Optional[UserActivityTrackerBase] = None


class UserDailyLogUpdate(BaseModel):
    current_status_summary: Optional[str] = None
    frequency: Optional[JSONDict] = None
    active_hours: Optional[JSONDict] = None

    # Allow partial updates for nested relations
    checkin: Optional[UserCheckinUpdate] = None
    chatbot_log: Optional[UserChatbotLogUpdate] = None
    journal: Optional[UserJournalUpdate] = None
    activities: Optional[UserActivityTrackerUpdate] = None


class UserDailyLogRead(UserDailyLogBase):
    id: UUID
    created_at: datetime

    # Nested one-to-one relationships (use read variants)
    checkin: Optional[UserCheckinRead] = None
    chatbot_log: Optional[UserChatbotLogRead] = None
    journal: Optional[UserJournalRead] = None
    activities: Optional[UserActivityTrackerRead] = None

    class Config:
        orm_mode = True


# ----------------------
# Convenience / Response Schemas
# ----------------------
class UserDailyLogList(BaseModel):
    items: List[UserDailyLogRead]
    total: int

    class Config:
        orm_mode = True
