# =====================================================================
# UPDATED ROUTER - app/api/routers/priorities.py
# =====================================================================

from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.core.config import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.services.user_priorities import user_priorities_service
from app.models.user_auth import UserAuth
from app.schemas.user_priorities import (
    UserPrioritiesCreate,
    UserPrioritiesUpdate,
    UserPrioritiesOut,
    BuildActivityRequest,
    AddActivityRequest,
    BulkAddActivitiesRequest,
)
from app.schemas.user_auth import SuccessResponse

router = APIRouter(prefix="/priorities", tags=["User Priorities"])


# =====================================================================
# USER ENDPOINTS - Manage own priorities
# =====================================================================


@router.post(
    "",
    response_model=UserPrioritiesOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create my priorities",
)
def create_priorities(
    priorities_data: UserPrioritiesCreate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create priorities for the authenticated user.

    **Sections:**
    - Minimal Profile: display name, age group, gender identity, pronouns
    - Pillar Importance: ranking weights for health, work, growth, relationships (must sum to 1.0)
    - Health Pillar: goals, baseline, activities, coping strategies
    - Work Pillar: goals, baseline, activities, coping strategies
    - Growth Pillar: goals, baseline, activities, coping strategies
    - Relationships Pillar: goals, baseline, activities, coping strategies
    - Preferences: check-in schedule, privacy settings, notifications

    Can only be created once per user.
    """
    priorities = user_priorities_service.create_priorities(
        db=db, priorities_data=priorities_data, requesting_user=current_user
    )
    return priorities


@router.get("/me", response_model=UserPrioritiesOut, summary="Get my priorities")
def get_my_priorities(
    current_user: UserAuth = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get the authenticated user's priorities.
    """
    priorities = user_priorities_service.get_my_priorities(
        db=db, requesting_user=current_user
    )
    return priorities


@router.put("/me", response_model=UserPrioritiesOut, summary="Update my priorities")
def update_my_priorities(
    update_data: UserPrioritiesUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the authenticated user's priorities.

    All fields are optional - only provided fields will be updated.
    """
    priorities = user_priorities_service.update_my_priorities(
        db=db, update_data=update_data, requesting_user=current_user
    )
    return priorities


@router.delete("/me", response_model=SuccessResponse, summary="Delete my priorities")
def delete_my_priorities(
    current_user: UserAuth = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Delete the authenticated user's priorities.
    """
    user_priorities_service.delete_priorities(
        db=db, user_id=current_user.id, requesting_user=current_user
    )
    return SuccessResponse(message="Priorities deleted successfully")


@router.post(
    "/me/complete-onboarding",
    response_model=UserPrioritiesOut,
    summary="Complete onboarding",
)
def complete_onboarding(
    current_user: UserAuth = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Mark onboarding as complete for the current user.

    Sets the onboarding_completed_at timestamp.
    """
    priorities = user_priorities_service.complete_onboarding(
        db=db, requesting_user=current_user
    )
    return priorities


# =====================================================================
# ADMIN ENDPOINTS
# =====================================================================


@router.get(
    "/user/{user_id}",
    response_model=UserPrioritiesOut,
    summary="Get priorities by user ID (Admin only)",
)
def get_priorities_by_user(
    user_id: UUID,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get priorities for a specific user (Admin only).
    """
    priorities = user_priorities_service.get_priorities_by_user_id(
        db=db, user_id=user_id, requesting_user=current_user
    )
    return priorities


@router.get("/user/{user_id}/exists", summary="Check if user has priorities")
def check_user_has_priorities(
    user_id: UUID,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if a user has set up their priorities.

    Returns true if priorities exist, false otherwise.
    """
    has_priorities = user_priorities_service.check_user_has_priorities(
        db=db, user_id=user_id
    )
    return {"has_priorities": has_priorities, "user_id": str(user_id)}


@router.delete(
    "/user/{user_id}",
    response_model=SuccessResponse,
    summary="Delete user priorities (Admin only)",
)
def delete_user_priorities(
    user_id: UUID,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Delete priorities for a specific user (Admin only).
    """
    user_priorities_service.delete_priorities(
        db=db, user_id=user_id, requesting_user=current_user
    )
    return SuccessResponse(message="Priorities deleted successfully")


# =====================================================================
# ACTIVITY TEMPLATE ENDPOINTS (Read-only)
# =====================================================================


@router.get(
    "/activities/templates",
    response_model=Dict[str, List[Dict[str, Any]]],
    summary="Get all activity templates",
)
def get_all_activity_templates(current_user: UserAuth = Depends(get_current_user)):
    """
    Get all available activity templates grouped by pillar.

    Returns activity templates for:
    - Health (walking, running, yoga, gym, etc.)
    - Work (upskilling, deep work, networking, etc.)
    - Growth (meditation, reading, journaling, etc.)
    - Relationships (gatherings, family time, calls, etc.)

    Each activity includes:
    - name: Display name
    - description: Activity description
    - pillars: List of associated pillars

    Users can then customize these templates using the /activities/build endpoint.
    """
    return user_priorities_service.get_all_activity_templates()


@router.get(
    "/activities/templates/pillar/{pillar}",
    response_model=List[Dict[str, Any]],
    summary="Get activity templates by pillar",
)
def get_activity_templates_by_pillar(
    pillar: str, current_user: UserAuth = Depends(get_current_user)
):
    """
    Get activity templates for a specific pillar.

    **Pillars:**
    - health
    - work
    - growth
    - relationships

    Returns list of activities associated with the pillar.
    Activities can belong to multiple pillars.
    """
    return user_priorities_service.get_activity_templates_by_pillar(pillar)


@router.get(
    "/activities/templates/{activity_name}",
    response_model=Dict[str, Any],
    summary="Get specific activity template",
)
def get_activity_template(
    activity_name: str, current_user: UserAuth = Depends(get_current_user)
):
    """
    Get a specific activity template by name.

    **Example names:**
    - Walking
    - Meditation
    - Upskilling
    - Social Gatherings

    Returns basic activity information (name, description, pillars).
    Use /activities/build to configure and customize the activity.
    """
    return user_priorities_service.get_activity_template(activity_name)


@router.get(
    "/activities/dimensions",
    response_model=List[Dict[str, Any]],
    summary="Get all dimension options",
)
def get_dimension_options(current_user: UserAuth = Depends(get_current_user)):
    """
    Get all available dimensions with their valid units.

    Useful for populating UI dropdowns when building activities.

    Returns:
    - dimension: Dimension type (time, distance, count, etc.)
    - units: List of valid units for that dimension

    **Example response:**
    ```json
    [
        {
            "dimension": "time",
            "units": ["minutes", "hours"]
        },
        {
            "dimension": "distance",
            "units": ["steps", "km", "miles", "meters"]
        },
        {
            "dimension": "count",
            "units": ["count", "times", "repetitions", "pages", "books"]
        }
    ]
    ```
    """
    return user_priorities_service.get_all_dimension_options()


@router.get(
    "/activities/dimensions/{dimension}/units",
    response_model=List[str],
    summary="Get units for specific dimension",
)
def get_dimension_units(
    dimension: str, current_user: UserAuth = Depends(get_current_user)
):
    """
    Get available units for a specific dimension.

    **Example:**
    - GET /activities/dimensions/time/units
    - Returns: ["minutes", "hours"]

    **Dimensions:**
    - time: minutes, hours
    - distance: steps, km, miles, meters
    - weight: kg, lbs, grams
    - volume: liters, ml, gallons
    - count: count, times, repetitions, pages, books, people, messages
    - rating: rating, stars
    - boolean: completed
    - text: text
    """
    return user_priorities_service.get_dimension_units(dimension)


# =====================================================================
# ACTIVITY BUILDING ENDPOINT
# =====================================================================


@router.post(
    "/activities/build",
    response_model=Dict[str, Any],
    summary="Build custom activity configuration",
)
def build_custom_activity(
    request: BuildActivityRequest, current_user: UserAuth = Depends(get_current_user)
):
    """
    Build a custom activity configuration with validation.

    This endpoint allows users to:
    1. Customize existing activity templates
    2. Create completely new activities

    **Parameters:**
    - name: Activity name (e.g., "Walking", "Talking to Parents")
    - description: What this activity is about
    - pillar: Which life area it belongs to
    - dimension: What you're measuring (time, distance, count, etc.)
    - complete: Initial progress value (default: 0)
    - unit: Specific measurement unit (minutes, steps, times, etc.)
    - quota_value: Your target number
    - reset_frequency: How often (daily, weekly, monthly, etc.)

    **Example 1 - Customize Walking:**
    ```json
    {
        "name": "Walking",
        "description": "Daily morning walk",
        "pillar": "health",
        "dimension": "distance",
        "complete": 5000,
        "unit": "steps",
        "quota_value": 10000,
        "reset_frequency": "daily"
    }
    ```

    **Example 2 - Custom Activity:**
    ```json
    {
        "name": "Talking to Parents",
        "description": "Weekly calls with parents",
        "pillar": "relationships",
        "dimension": "count",
        "complete": 0,
        "unit": "times",
        "quota_value": 2,
        "reset_frequency": "weekly"
    }
    ```

    Returns the configured activity ready to be added to user priorities.
    This does NOT save the activity - use the add endpoint for that.
    """
    return user_priorities_service.build_activity(
        name=request.name,
        description=request.description,
        pillar=request.pillar,
        dimension=request.dimension,
        complete=request.complete,
        unit=request.unit,
        quota_value=request.quota_value,
        reset_frequency=request.reset_frequency,
    )


# =====================================================================
# USER ACTIVITY MANAGEMENT ENDPOINTS
# =====================================================================


@router.post(
    "/me/activities",
    response_model=UserPrioritiesOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add activity to my priorities",
)
def add_my_activity(
    request: AddActivityRequest,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a configured activity to the authenticated user's priorities.

    **Request body:**
    ```json
    {
        "pillar": "health",
        "name": "Walking",
        "description": "Daily morning walk",
        "dimension": "distance",
        "complete": 5000,
        "unit": "steps",
        "quota_value": 10000,
        "reset_frequency": "daily"
    }
    ```

    The activity will be validated, built, and stored in the specified pillar.
    The 'complete' field represents the initial progress value.
    """
    priorities = user_priorities_service.add_user_activity(
        db=db,
        user_id=current_user.id,
        pillar=request.pillar,
        name=request.name,
        description=request.description,
        dimension=request.dimension,
        complete=request.complete,
        unit=request.unit,
        quota_value=request.quota_value,
        reset_frequency=request.reset_frequency,
    )
    return priorities


@router.put(
    "/me/activities/{pillar}/{activity_name}",
    response_model=UserPrioritiesOut,
    summary="Update activity in my priorities",
)
def update_my_activity(
    pillar: str,
    activity_name: str,
    description: str = Query(None),
    dimension: str = Query(None),
    complete: int = Query(None, ge=0),
    unit: str = Query(None),
    quota_value: float = Query(None, gt=0),
    reset_frequency: str = Query(None),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing activity in the authenticated user's priorities.

    **Path parameters:**
    - pillar: The pillar containing the activity (health, work, growth, relationships)
    - activity_name: The name of the activity to update

    **Query parameters (all optional):**
    - description: Updated description
    - dimension: Updated dimension (time, distance, count, etc.)
    - complete: Updated progress value (must be non-negative)
    - unit: Updated unit
    - quota_value: Updated target value
    - reset_frequency: Updated frequency (daily, weekly, etc.)

    Only provided fields will be updated.
    """
    priorities = user_priorities_service.update_user_activity(
        db=db,
        user_id=current_user.id,
        pillar=pillar,
        activity_name=activity_name,
        dimension=dimension,
        complete=complete,
        unit=unit,
        quota_value=quota_value,
        reset_frequency=reset_frequency,
        description=description,
    )
    return priorities


@router.patch(
    "/me/activities/{pillar}/{activity_name}/progress",
    response_model=UserPrioritiesOut,
    summary="Update activity progress",
)
def update_activity_progress(
    pillar: str,
    activity_name: str,
    complete: int = Query(..., ge=0, description="New progress value"),
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update just the progress (complete) value for an activity.

    This is a convenience endpoint for updating activity progress without
    modifying other fields. Useful for tracking daily/weekly progress.

    **Path parameters:**
    - pillar: The pillar containing the activity
    - activity_name: The name of the activity

    **Query parameter:**
    - complete: The new progress value (must be non-negative)

    **Example:**
    ```
    PATCH /me/activities/health/Walking/progress?complete=7500
    ```

    Updates only the 'complete' field, leaving other configuration intact.
    """
    priorities = user_priorities_service.update_activity_progress(
        db=db,
        user_id=current_user.id,
        pillar=pillar,
        activity_name=activity_name,
        complete_value=complete,
    )
    return priorities


@router.delete(
    "/me/activities/{pillar}/{activity_name}",
    response_model=SuccessResponse,
    summary="Remove activity from my priorities",
)
def remove_my_activity(
    pillar: str,
    activity_name: str,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove an activity from the authenticated user's priorities.

    **Path parameters:**
    - pillar: The pillar containing the activity
    - activity_name: The name of the activity to remove
    """
    user_priorities_service.remove_user_activity(
        db=db, user_id=current_user.id, pillar=pillar, activity_name=activity_name
    )
    return SuccessResponse(
        message=f"Activity '{activity_name}' removed from {pillar} pillar"
    )


@router.get(
    "/me/activities",
    response_model=Dict[str, List[Dict[str, Any]]],
    summary="Get all my activities",
)
def get_all_my_activities(
    current_user: UserAuth = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get all configured activities for the authenticated user across all pillars.

    Returns a dictionary mapping pillar names to their activities:
    ```json
    {
        "health": [
            {
                "name": "Walking",
                "description": "Daily morning walk",
                "pillar": "health",
                "configuration": {
                    "dimension": "distance",
                    "complete": 5000,
                    "unit": "steps",
                    "quota": {
                        "value": 10000,
                        "reset_frequency": "daily"
                    }
                }
            }
        ],
        "work": [...],
        "growth": [...],
        "relationships": [...]
    }
    ```
    """
    return user_priorities_service.get_all_user_activities(
        db=db, user_id=current_user.id
    )


@router.get(
    "/me/activities/{pillar}",
    response_model=List[Dict[str, Any]],
    summary="Get my activities for specific pillar",
)
def get_my_activities_by_pillar(
    pillar: str,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all configured activities for a specific pillar.

    **Path parameters:**
    - pillar: health, work, growth, or relationships

    Returns a list of activity configurations for that pillar.
    Each activity includes the 'complete' field showing current progress.
    """
    return user_priorities_service.get_user_activities_by_pillar(
        db=db, user_id=current_user.id, pillar=pillar
    )


@router.post(
    "/me/activities/bulk",
    response_model=UserPrioritiesOut,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk add activities (onboarding)",
)
def bulk_add_my_activities(
    request: BulkAddActivitiesRequest,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add multiple activities at once (useful during onboarding).

    **Request body:**
    ```json
    {
        "activities": [
            {
                "pillar": "health",
                "name": "Walking",
                "description": "Daily morning walk",
                "dimension": "distance",
                "complete": 0,
                "unit": "steps",
                "quota_value": 10000,
                "reset_frequency": "daily"
            },
            {
                "pillar": "growth",
                "name": "Meditation",
                "description": "Morning meditation",
                "dimension": "time",
                "complete": 0,
                "unit": "minutes",
                "quota_value": 15,
                "reset_frequency": "daily"
            }
        ]
    }
    ```

    Invalid activities will be skipped. Returns updated priorities.
    Each activity's 'complete' field starts at 0 or specified value.
    """
    priorities = user_priorities_service.bulk_add_user_activities(
        db=db, user_id=current_user.id, activities=request.activities
    )
    return priorities


# =====================================================================
# ADMIN ACTIVITY MANAGEMENT ENDPOINTS
# =====================================================================


@router.get(
    "/user/{user_id}/activities",
    response_model=Dict[str, List[Dict[str, Any]]],
    summary="Get all activities for user (Admin)",
)
def get_user_activities(
    user_id: UUID,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get all configured activities for a specific user (Admin only).
    """
    return user_priorities_service.get_all_user_activities(db=db, user_id=user_id)


@router.get(
    "/user/{user_id}/activities/{pillar}",
    response_model=List[Dict[str, Any]],
    summary="Get user activities by pillar (Admin)",
)
def get_user_activities_by_pillar(
    user_id: UUID,
    pillar: str,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """
    Get activities for a specific user and pillar (Admin only).
    """
    return user_priorities_service.get_user_activities_by_pillar(
        db=db, user_id=user_id, pillar=pillar
    )
