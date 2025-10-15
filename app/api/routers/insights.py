# app/api/routers/insights.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import get_db
from app.core.security import (
    get_current_user,
    get_current_admin_user,
    require_any_role
)
from app.services.user_insight import user_insight_service
from app.models.user_auth import UserAuth, UserRole
from app.schemas.user_insight import (
    UserInsightCreate,
    UserInsightUpdate,
    UserInsightOut,
    UserInsightSummary
)
from app.schemas.user_auth import SuccessResponse

router = APIRouter(prefix="/insights", tags=["User Insights"])


# =====================================================================
# USER ENDPOINTS - Get own insight
# =====================================================================

@router.get(
    "/me",
    response_model=List[UserInsightOut],
    summary="Get my insight profiles"
)
def get_my_insights(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all insight profiles for the authenticated user.
    
    Users can only view their own insight profiles.
    Returns a list (may be empty if no insights exist).
    """
    insights = user_insight_service.get_my_insights(
        db=db,
        requesting_user=current_user
    )
    return insights


# =====================================================================
# PROFESSIONAL/ADMIN ENDPOINTS - Create and manage insights
# =====================================================================

@router.post(
    "",
    response_model=UserInsightOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create user insight (Professional/Admin only)"
)
def create_insight(
    insight_data: UserInsightCreate,
    current_user: UserAuth = Depends(require_any_role(UserRole.professional, UserRole.admin)),
    db: Session = Depends(get_db)
):
    """
    Create a new user insight profile (Professional/Admin only).
    
    **Sections:**
    - Demographics: age, living situation, occupation, marital status, education
    - Medical History: diagnoses, family history, medications, therapy history, lab results
    - Lifestyle Factors: sleep, exercise, substance use, nutrition, risk behaviors
    - Psychological Assessment: assessment scales, resilience score, coping score
    - Conclusion: caregiver notes, therapy goals, clinician summary
    - Metadata: assessed_by, assessment_date
    
    **Note:** Multiple insights can be created for the same user (e.g., for tracking progress over time).
    """
    insight = user_insight_service.create_insight(
        db=db,
        insight_data=insight_data,
        requesting_user=current_user
    )
    return insight


@router.get(
    "/user/{user_id}/exists",
    summary="Check if user has insights"
)
def check_user_has_insights(
    user_id: UUID,
    current_user: UserAuth = Depends(require_any_role(UserRole.professional, UserRole.admin)),
    db: Session = Depends(get_db)
):
    """
    Check if a user has any insight profiles.
    
    Returns true if user has at least one insight, false otherwise.
    """
    has_insight = user_insight_service.check_user_has_insight(
        db=db,
        user_id=user_id,
        requesting_user=current_user
    )
    return {"has_insight": has_insight, "insight_id_list": has_insight and [insight.id for insight in user_insight_service.get_insights_by_user_id(db, user_id, current_user)] or []}


@router.get(
    "/assessments/me",
    response_model=List[UserInsightSummary],
    summary="Get my assessments (Professional only)"
)
def get_my_assessments(
    skip: int = 0,
    limit: int = 100,
    current_user: UserAuth = Depends(require_any_role(UserRole.professional, UserRole.admin)),
    db: Session = Depends(get_db)
):
    """
    Get list of insights created by the authenticated professional.
    
    Returns a summary list of all assessments performed by this professional.
    """
    insights = user_insight_service.list_my_assessments(
        db=db,
        requesting_user=current_user,
        skip=skip,
        limit=limit
    )
    return insights


@router.get(
    "/user/{user_id}",
    response_model=List[UserInsightOut],
    summary="Get insights by user ID (Professional/Admin only)"
)
def get_insights_by_user(
    user_id: UUID,
    current_user: UserAuth = Depends(require_any_role(UserRole.professional, UserRole.admin)),
    db: Session = Depends(get_db)
):
    """
    Get all insight profiles for a specific user.
    
    - Professionals can view insights they created
    - Admins can view all insights
    
    Returns a list (may be empty if no insights exist).
    """
    insights = user_insight_service.get_insights_by_user_id(
        db=db,
        user_id=user_id,
        requesting_user=current_user
    )
    return insights


@router.get(
    "/{insight_id}",
    response_model=UserInsightOut,
    summary="Get insight by ID (Only related users can view)"
)
def get_insight(
    insight_id: UUID,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get insight by ID.
    
    - Users can view their own insight
    - Professionals can view insights they created
    - Admins can view all insights
    """
    insight = user_insight_service.get_insight_by_id(
        db=db,
        insight_id=insight_id,
        requesting_user=current_user
    )
    return insight


# =====================================================================
# UPDATE ENDPOINTS - Full update only (sectioned updates removed)
# =====================================================================

@router.put(
    "/{insight_id}",
    response_model=UserInsightOut,
    summary="Update insight (Professional/Admin only)"
)
def update_insight(
    insight_id: UUID,
    update_data: UserInsightUpdate,
    current_user: UserAuth = Depends(require_any_role(UserRole.professional, UserRole.admin)),
    db: Session = Depends(get_db)
):
    """
    Update entire insight profile.
    
    - Professionals can update insights they created
    - Admins can update all insights
    
    All fields are optional - only provided fields will be updated.
    """
    insight = user_insight_service.update_insight(
        db=db,
        insight_id=insight_id,
        update_data=update_data,
        requesting_user=current_user
    )
    return insight


# =====================================================================
# ADMIN ENDPOINTS
# =====================================================================

@router.get(
    "",
    response_model=List[UserInsightSummary],
    summary="List all insights (Admin only)"
)
def list_insights(
    skip: int = 0,
    limit: int = 100,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get list of all user insights (Admin only).
    
    Returns a summary list with pagination.
    """
    insights = user_insight_service.list_insights(
        db=db,
        requesting_user=current_user,
        skip=skip,
        limit=limit
    )
    return insights


@router.get(
    "/statistics/count",
    summary="Get total insight count (Admin only)"
)
def get_insight_count(
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get total count of all insights (Admin only).
    """
    count = user_insight_service.get_insight_count(
        db=db,
        requesting_user=current_user
    )
    return {"total_insights": count}


@router.delete(
    "/{insight_id}",
    response_model=SuccessResponse,
    summary="Delete insight (Admin only)"
)
def delete_insight(
    insight_id: UUID,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a user insight (Admin only).
    
    This is a hard delete - the insight will be permanently removed.
    """
    user_insight_service.delete_insight(
        db=db,
        insight_id=insight_id,
        requesting_user=current_user
    )
    return SuccessResponse(message="Insight deleted successfully")