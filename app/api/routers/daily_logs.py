from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Path
from sqlalchemy.orm import Session


from app.core.config import get_db
from app.core.security import get_current_user
from app.services.user_daily_log import user_daily_log_service
from app import models, schemas
from app.schemas.user_daily_logs import (
    UserActivityTrackerRead,
    ActivityUpdateRequest,
    ActivityIncrementRequest,
    ActivityResetRequest,
    ProgressSummaryResponse,
    StreakResponse,
    ActivityDetailResponse,
    ActivitySuccessResponse,
    BulkActivityUpdateRequest,
    BulkUpdateResponse,
)


from pydantic import BaseModel, Field


# ====================================================
# PYDANTIC SCHEMAS
# ====================================================


class DailyLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    date: date
    current_status_summary: Optional[str]
    frequency: Optional[dict]
    active_hours: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class DailyLogDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    date: date
    current_status_summary: Optional[str]
    frequency: Optional[dict]
    active_hours: Optional[dict]
    created_at: datetime
    checkin: dict
    journal: dict
    chatbot: dict
    activities: dict


class CheckinUpdateRequest(BaseModel):
    field: str = Field(
        ..., description="Field to update: mood, stress_level, energy_level, sleep"
    )
    value: Any = Field(..., description="Value to set")
    timestamp: Optional[str] = Field(
        default=None, description="Optional timestamp, defaults to now"
    )


class JournalActionRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Journal entry content")
    entry_type: str = Field(default="text", description="Type of entry")
    sentiment: Optional[str] = None
    topics: Optional[List[str]] = None


class JournalEntryUpdateRequest(BaseModel):
    content: Optional[str] = Field(
        ..., min_length=1, description="Journal entry content"
    )
    entry_type: Optional[str] = Field(default="text", description="Type of entry")
    sentiment: Optional[str] = None
    topics: Optional[List[str]] = None


class ChatbotMessageRequest(BaseModel):
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., min_length=1, description="Message content")


class ActivityUpdateRequest(BaseModel):
    completed: float = Field(..., description="Completed/covered value")
    category: Optional[str] = None


class ActivityIncrementRequest(BaseModel):
    increment: float = Field(..., description="Amount to increment completed value")
    category: Optional[str] = None


class ActivityResetRequest(BaseModel):
    activity_name: str
    category: Optional[str] = None


class CategoryResetRequest(BaseModel):
    category: str


class ProgressSummaryResponse(BaseModel):
    total: int
    completed: int
    in_progress: int
    not_started: int
    completion_rate: float


class StreakResponse(BaseModel):
    activity_name: str
    current_streak: int
    longest_streak: int


class DailySummaryResponse(BaseModel):
    summary: str
    date: date


# ====================================================
# ROUTER
# ====================================================


router = APIRouter(prefix="/daily-log", tags=["Daily Log"])

# ====================================================
# DAILY LOG ENDPOINTS
# ====================================================


@router.get("/today", response_model=DailyLogDetailResponse)
def get_today_log(
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get or create today's daily log with all details."""
    try:
        data = user_daily_log_service.get_daily_log_with_details(
            db=db, user_id=current_user.id, log_date=date.today()
        )

        if not data:
            # Create today's log if it doesn't exist
            user_daily_log_service.get_or_create_daily_log(
                db=db, user_id=current_user.id, log_date=date.today()
            )
            data = user_daily_log_service.get_daily_log_with_details(
                db=db, user_id=current_user.id, log_date=date.today()
            )

        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{log_date}", response_model=DailyLogDetailResponse)
def get_log_by_date(
    log_date: date,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get daily log for a specific date."""
    try:
        data = user_daily_log_service.get_daily_log_with_details(
            db=db, user_id=current_user.id, log_date=log_date
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No log found for date {log_date}",
            )

        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/range/", response_model=List[dict])
def get_logs_by_range(
    start_date: date = Query(..., description="Start date (inclusive)"),
    end_date: date = Query(..., description="End date (inclusive)"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get daily logs within a date range."""
    try:
        logs = user_daily_log_service.get_date_range_logs(
            db=db, user_id=current_user.id, start_date=start_date, end_date=end_date
        )
        return logs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ====================================================
# CHECKIN ENDPOINTS
# ====================================================


class CheckinActionRequest(BaseModel):
    field: str = Field(
        ..., description="Field name: mood, stress_level, energy_level, sleep"
    )
    value: Any = Field(..., description="Value to set")
    timestamp: Optional[datetime] = Field(
        None, description="ISO timestamp, defaults to now"
    )


@router.post("/{log_date}/checkin/add", status_code=status.HTTP_200_OK)
def add_checkin_entry(
    log_date: date,
    request: CheckinActionRequest,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a NEW check-in entry for a specific date.

    This will add a new timestamped entry without overwriting existing ones.

    Fields:
        - mood: happy, sad, neutral, anxious, etc.
        - stress_level: high, medium, low
        - energy_level: high, medium, low
        - sleep: {"duration": int (minutes), "quality": str}
    """
    try:
        # Validate field
        valid_fields = ["mood", "stress_level", "energy_level", "sleep"]
        if request.field not in valid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field. Must be one of: {', '.join(valid_fields)}",
            )

        timestamp = request.timestamp or datetime.now()

        checkin = user_daily_log_service.add_checkin_entry(
            db=db,
            user_id=current_user.id,
            log_date=log_date,
            field=request.field,
            timestamp=timestamp,
            value=request.value,
        )

        return {
            "message": "Check-in entry added successfully",
            "field": request.field,
            "value": request.value,
            "timestamp": timestamp.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/{log_date}/checkin/update", status_code=status.HTTP_200_OK)
def update_checkin_entry(
    log_date: date,
    request: CheckinActionRequest,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an EXISTING check-in entry at a specific timestamp.

    This will update the value at the given timestamp. If the timestamp doesn't exist,
    it will return an error.

    Fields:
        - mood: happy, sad, neutral, anxious, etc.
        - stress_level: high, medium, low
        - energy_level: high, medium, low
        - sleep: {"duration": int (minutes), "quality": str}
    """
    try:
        # Validate field
        valid_fields = ["mood", "stress_level", "energy_level", "sleep"]
        if request.field not in valid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field. Must be one of: {', '.join(valid_fields)}",
            )

        if not request.timestamp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timestamp is required for update operation",
            )

        checkin = user_daily_log_service.update_checkin_entry(
            db=db,
            user_id=current_user.id,
            log_date=log_date,
            field=request.field,
            timestamp=request.timestamp,
            value=request.value,
        )

        return {
            "message": "Check-in entry updated successfully",
            "field": request.field,
            "value": request.value,
            "timestamp": request.timestamp.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{log_date}/checkin/latest", response_model=dict)
def get_latest_checkin(
    log_date: date,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get latest check-in values for a specific date."""
    try:
        data = user_daily_log_service.get_latest_checkin_values(
            db=db, user_id=current_user.id, log_date=log_date
        )
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{log_date}/checkin", response_model=dict)
def get_full_day_checkin_history(
    log_date: date,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full-day check-in history for a specific date."""
    try:
        data = user_daily_log_service.get_full_day_checkin_history(
            db=db, user_id=current_user.id, log_date=log_date
        )
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ====================================================
# JOURNAL ENDPOINTS
# ====================================================


@router.post("/{log_date}/journal", status_code=status.HTTP_201_CREATED)
def add_journal_entry(
    log_date: date,
    request: JournalActionRequest,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new journal entry for a specific date."""
    try:
        timestamp = datetime.now(timezone.utc)

        journal = user_daily_log_service.add_journal_entry(
            db=db,
            user_id=current_user.id,
            log_date=log_date,
            content=request.content,
            entry_type=request.entry_type,
            sentiment=request.sentiment,
            topics=request.topics,
            timestamp=timestamp,
        )

        return {
            "message": "Journal entry added",
            "timestamp": timestamp.isoformat(),
            "entry": journal.journal[timestamp.isoformat()],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{log_date}/journal/{timestamp}")
def update_journal_entry(
    log_date: date,
    timestamp: datetime,
    request: JournalEntryUpdateRequest,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing journal entry."""
    try:
        journal = user_daily_log_service.update_journal_entry(
            db=db,
            user_id=current_user.id,
            log_date=log_date,
            timestamp=timestamp,
            content=request.content,
            entry_type=request.entry_type,
            sentiment=request.sentiment,
            topics=request.topics,
        )

        return {
            "message": "Journal entry updated",
            "timestamp": timestamp.isoformat(),
            "entry": journal.journal[timestamp.isoformat()],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{log_date}/journal")
def get_journal_entries(
    log_date: date,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all journal entries for a specific date."""
    entries = user_daily_log_service.get_journal_entries(
        db=db, user_id=current_user.id, log_date=log_date
    )
    return entries or {}


@router.delete("/{log_date}/journal/{timestamp}")
def delete_journal_entry(
    log_date: date,
    timestamp: datetime,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a specific journal entry."""
    try:
        success = user_daily_log_service.delete_journal_entry(
            db=db, user_id=current_user.id, log_date=log_date, timestamp=timestamp
        )

        if not success:
            raise HTTPException(status_code=404, detail="Entry not found")

        return {"message": "Entry deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ====================================================
# CHATBOT ENDPOINTS
# ====================================================


@router.post("/{log_date}/chatbot", status_code=status.HTTP_201_CREATED)
def add_chatbot_message(
    log_date: date,
    request: ChatbotMessageRequest,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a message to chatbot conversation."""
    try:
        if request.role not in ["user", "assistant"]:
            raise HTTPException(
                status_code=400, detail="Role must be 'user' or 'assistant'"
            )

        chatbot = user_daily_log_service.add_chatbot_message(
            db=db,
            user_id=current_user.id,
            log_date=log_date,
            role=request.role,
            content=request.content,
        )

        return {
            "message": "Message added",
            "timestamp": chatbot.conversation[-1]["timestamp"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{log_date}/chatbot")
def get_chatbot_conversation(
    log_date: date,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get chatbot conversation for a specific date."""
    conversation = user_daily_log_service.get_chatbot_conversation(
        db=db, user_id=current_user.id, log_date=log_date
    )
    return conversation or []


@router.delete("/{log_date}/chatbot/{message_index}")
def delete_chatbot_message(
    log_date: date,
    message_index: int,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a specific message from chatbot conversation."""
    try:
        success = user_daily_log_service.delete_chatbot_message(
            db=db,
            user_id=current_user.id,
            log_date=log_date,
            message_index=message_index,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Message not found")

        return {"message": "Message deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{log_date}/chatbot")
def clear_chatbot_conversation(
    log_date: date,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear all messages from chatbot conversation."""
    try:
        success = user_daily_log_service.clear_chatbot_conversation(
            db=db, user_id=current_user.id, log_date=log_date
        )

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {"message": "Conversation cleared"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ====================================================
# ACTIVITY TRACKING
# ====================================================


@router.post(
    "/{log_date}/activities/initialize",
    response_model=UserActivityTrackerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize daily activities from priorities",
)
def initialize_daily_activities(
    log_date: date = Path(..., description="Date for the daily log (YYYY-MM-DD)"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initialize daily activities from user priorities.

    This endpoint:
    - Copies activities from user priorities to the daily tracker
    - Sets all `complete` values to 0
    - Creates the tracker if it doesn't exist

    **Example:**
    ```
    POST /daily-log/2025-10-14/activities/initialize
    ```

    Returns all activity categories with their initial state.
    """
    activities = user_daily_log_service.initialize_daily_activities(
        db=db, user_id=current_user.id, log_date=log_date
    )
    return activities


# =====================================================================
# GET ACTIVITIES
# =====================================================================


@router.get(
    "/{log_date}/activities",
    response_model=UserActivityTrackerRead,
    summary="Get all activities for a date",
)
def get_daily_activities(
    log_date: date = Path(..., description="Date to retrieve activities for"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all activities for a specific date.

    Returns activities across all categories with their current progress.
    """
    activities = user_daily_log_service.get_activities_by_date(
        db=db, user_id=current_user.id, log_date=log_date
    )

    if not activities:

        raise HTTPException(
            status_code=404,
            detail=f"No activities found for {log_date}. Try initializing first.",
        )

    return activities


@router.get(
    "/{log_date}/activities/{activity_name}",
    response_model=ActivityDetailResponse,
    summary="Get specific activity details",
)
def get_activity_detail(
    log_date: date = Path(..., description="Date of the log"),
    activity_name: str = Path(..., description="Name of the activity"),
    category: Optional[str] = Query(None, description="Category filter"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get details for a specific activity including completion percentage.

    **Example:**
    ```
    GET /daily-log/2025-10-14/activities/Morning Walk?category=health
    ```
    """
    activity = user_daily_log_service.get_activity_by_name(
        db=db,
        user_id=current_user.id,
        log_date=log_date,
        activity_name=activity_name,
        category=category,
    )

    if not activity:

        raise HTTPException(
            status_code=404,
            detail=f"Activity '{activity_name}' not found for {log_date}",
        )

    # Calculate completion percentage
    percentage = user_daily_log_service.get_completion_percentage(
        db=db,
        user_id=current_user.id,
        log_date=log_date,
        activity_name=activity_name,
        category=category,
    )

    return ActivityDetailResponse(
        name=activity["name"],
        description=activity["description"],
        pillar=activity["pillar"],
        configuration=activity["configuration"],
        complete_percentage=percentage,
    )


# =====================================================================
# UPDATE ACTIVITY PROGRESS
# =====================================================================


@router.put(
    "/{log_date}/activities/{activity_name}",
    response_model=ActivitySuccessResponse,
    summary="Update activity complete value",
)
def update_activity_complete(
    log_date: date = Path(..., description="Date of the log"),
    activity_name: str = Path(..., description="Name of the activity"),
    request: ActivityUpdateRequest = Body(...),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the complete value for an activity.

    **Request body:**
    ```json
    {
        "complete": 7500,
        "category": "health"
    }
    ```

    This sets the complete value directly (not incremental).
    """
    activities = user_daily_log_service.update_activity_complete(
        db=db,
        user_id=current_user.id,
        log_date=log_date,
        activity_name=activity_name,
        complete_value=request.complete,
        category=request.category,
    )

    return ActivitySuccessResponse(
        message="Activity updated successfully",
        activity_name=activity_name,
        complete_value=request.complete,
        category=request.category,
    )


@router.patch(
    "/{log_date}/activities/{activity_name}/increment",
    response_model=ActivitySuccessResponse,
    summary="Increment activity complete value",
)
def increment_activity_complete(
    log_date: date = Path(..., description="Date of the log"),
    activity_name: str = Path(..., description="Name of the activity"),
    request: ActivityIncrementRequest = Body(...),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Increment (or decrement) the complete value for an activity.

    **Request body:**
    ```json
    {
        "increment": 1000,
        "category": "health"
    }
    ```

    This adds to the existing complete value.
    Use negative values to decrement.
    """
    activities = user_daily_log_service.increment_activity_complete(
        db=db,
        user_id=current_user.id,
        log_date=log_date,
        activity_name=activity_name,
        increment=request.increment,
        category=request.category,
    )

    return ActivitySuccessResponse(
        message=f"Activity incremented by {request.increment}",
        activity_name=activity_name,
        complete_value=None,
        category=request.category,
    )


# =====================================================================
# RESET OPERATIONS
# =====================================================================


@router.post(
    "/{log_date}/activities/{activity_name}/reset",
    response_model=ActivitySuccessResponse,
    summary="Reset specific activity to 0",
)
def reset_activity(
    log_date: date = Path(..., description="Date of the log"),
    activity_name: str = Path(..., description="Name of the activity"),
    category: Optional[str] = Query(None, description="Category filter"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reset a specific activity's complete value to 0.
    """
    activities = user_daily_log_service.reset_activity(
        db=db,
        user_id=current_user.id,
        log_date=log_date,
        activity_name=activity_name,
        category=category,
    )

    return ActivitySuccessResponse(
        message=f"Activity '{activity_name}' reset to 0",
        activity_name=activity_name,
        complete_value=0,
        category=category,
    )


@router.post(
    "/{log_date}/activities/reset/category/{category}",
    response_model=UserActivityTrackerRead,
    summary="Reset all activities in a category",
)
def reset_category_activities(
    log_date: date = Path(..., description="Date of the log"),
    category: str = Path(
        ..., description="Category to reset (health, work, growth, relationship)"
    ),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reset all activities in a specific category to complete=0.

    **Valid categories:**
    - health
    - work
    - growth
    - relationship
    """
    activities = user_daily_log_service.reset_category_activities(
        db=db, user_id=current_user.id, log_date=log_date, category=category
    )

    return activities


@router.post(
    "/{log_date}/activities/reset/all",
    response_model=UserActivityTrackerRead,
    summary="Reset all activities",
)
def reset_all_activities(
    log_date: date = Path(..., description="Date of the log"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reset all activities across all categories to complete=0.
    """
    activities = user_daily_log_service.reset_all_activities(
        db=db, user_id=current_user.id, log_date=log_date
    )

    return activities


# =====================================================================
# PROGRESS & ANALYTICS
# =====================================================================


@router.get(
    "/{log_date}/progress/summary",
    response_model=ProgressSummaryResponse,
    summary="Get daily progress summary",
)
def get_progress_summary(
    log_date: date = Path(..., description="Date to analyze"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get summary of activity progress for the day.

    Returns:
    - Total activities
    - Completed (met quota)
    - In progress
    - Not started
    - Completion rate
    """
    summary = user_daily_log_service.get_activity_progress_summary(
        db=db, user_id=current_user.id, log_date=log_date
    )

    return summary


@router.get(
    "/activities/{activity_name}/streak",
    response_model=StreakResponse,
    summary="Get activity streak",
)
def get_activity_streak(
    activity_name: str = Path(..., description="Name of the activity"),
    category: Optional[str] = Query(None, description="Category filter"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calculate streak for a specific activity.

    An activity counts toward a streak if:
    - complete >= quota (for activities with quotas)
    - complete > 0 (for activities without quotas)

    **Example:**
    ```
    GET /daily-log/activities/Morning Walk/streak?days=30&category=health
    ```
    """
    streak = user_daily_log_service.get_activity_streak(
        db=db,
        user_id=current_user.id,
        activity_name=activity_name,
        category=category,
        days_to_check=days,
    )

    return streak


@router.get(
    "/{log_date}/activities/{activity_name}/percentage",
    summary="Get completion percentage",
)
def get_completion_percentage(
    log_date: date = Path(..., description="Date of the log"),
    activity_name: str = Path(..., description="Name of the activity"),
    category: Optional[str] = Query(None, description="Category filter"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get completion percentage for a specific activity.

    Returns percentage (0-100) based on complete vs quota.
    """
    percentage = user_daily_log_service.get_completion_percentage(
        db=db,
        user_id=current_user.id,
        log_date=log_date,
        activity_name=activity_name,
        category=category,
    )

    if percentage is None:

        raise HTTPException(
            status_code=404,
            detail=f"Activity '{activity_name}' not found for {log_date}",
        )

    return {
        "activity_name": activity_name,
        "date": log_date,
        "completion_percentage": percentage,
    }


# =====================================================================
# BULK OPERATIONS
# =====================================================================


@router.put(
    "/{log_date}/activities/bulk-update",
    response_model=BulkUpdateResponse,
    summary="Bulk update multiple activities",
)
def bulk_update_activities(
    log_date: date = Path(..., description="Date of the log"),
    request: BulkActivityUpdateRequest = Body(...),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update multiple activities at once.

    **Request body:**
    ```json
    {
        "updates": [
            {"name": "Morning Walk", "complete": 10000},
            {"name": "Meditation", "complete": 15},
            {"name": "Reading", "complete": 30}
        ]
    }
    ```

    Returns count of successful and failed updates.
    """
    success_count = 0
    error_count = 0
    errors = []

    for update in request.updates:
        try:
            activity_name = update.get("name")
            complete_value = update.get("complete")
            category = update.get("category")

            if not activity_name or complete_value is None:
                errors.append(f"Invalid update: {update}")
                error_count += 1
                continue

            user_daily_log_service.update_activity_complete(
                db=db,
                user_id=current_user.id,
                log_date=log_date,
                activity_name=activity_name,
                complete_value=complete_value,
                category=category,
            )
            success_count += 1

        except Exception as e:
            error_count += 1
            errors.append(f"Failed to update '{update.get('name')}': {str(e)}")

    return BulkUpdateResponse(
        success_count=success_count,
        error_count=error_count,
        errors=errors,
        message=f"Bulk update completed: {success_count} succeeded, {error_count} failed",
    )


# ====================================================
# DAILY SUMMARY
# ====================================================


@router.get("/{log_date}/summary", response_model=DailySummaryResponse)
def get_daily_summary(
    log_date: date,
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate AI-ready summary of the day."""
    try:
        summary = user_daily_log_service.generate_daily_summary(
            db=db, user_id=current_user.id, log_date=log_date
        )

        return {"summary": summary, "date": log_date}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ====================================================
# BULK OPERATIONS
# ====================================================


@router.get("/activities/all", response_model=dict)
def get_all_activities(
    log_date: date = Query(..., description="Date to fetch activities for"),
    current_user: models.UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all activities for a specific date."""
    try:
        data = user_daily_log_service.get_daily_log_with_details(
            db=db, user_id=current_user.id, log_date=log_date
        )

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No activities found for date {log_date}",
            )

        return data["activities"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
