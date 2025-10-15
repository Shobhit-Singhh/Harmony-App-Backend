# services/user_insight.py
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user_insight import UserInsight
from app.models.user_auth import UserAuth, UserRole
from app.schemas.user_insight import (
    UserInsightCreate,
    UserInsightUpdate,
)
from app.crud.user_insight import crud_user_insight
from app.crud.user_auth import crud_user_auth


# =====================================================================
# EXCEPTIONS
# =====================================================================

class InsightNotFoundError(HTTPException):
    """Insight not found exception."""
    def __init__(self, detail: str = "Insight not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class PermissionDeniedError(HTTPException):
    """Permission denied exception."""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# =====================================================================
# SERVICE CLASS
# =====================================================================

class UserInsightService:
    """Service layer for user insights."""

    def __init__(self):
        self.crud = crud_user_insight
        self.user_crud = crud_user_auth

    # =====================================================================
    # PERMISSION HELPERS
    # =====================================================================

    def _can_access_insight(
        self,
        insight: UserInsight,
        requesting_user: UserAuth
    ) -> bool:
        """
        Check if user can access insight.
        
        - Users can access their own insights
        - Professionals can access insights they created
        - Admins can access all insights
        """
        if requesting_user.role == UserRole.admin:
            return True
        
        if insight.user_id == requesting_user.id:
            return True
        
        if (requesting_user.role == UserRole.professional and 
            insight.assessed_by == requesting_user.id):
            return True
        
        return False

    def _can_modify_insight(
        self,
        insight: UserInsight,
        requesting_user: UserAuth
    ) -> bool:
        """
        Check if user can modify insight.
        
        - Professionals can modify insights they created
        - Admins can modify all insights
        - Users cannot modify insights (read-only)
        """
        if requesting_user.role == UserRole.admin:
            return True
        
        if (requesting_user.role == UserRole.professional and 
            insight.assessed_by == requesting_user.id):
            return True
        
        return False

    # =====================================================================
    # CREATE OPERATIONS
    # =====================================================================

    def create_insight(
        self,
        db: Session,
        insight_data: UserInsightCreate,
        requesting_user: UserAuth
    ) -> UserInsight:
        """
        Create new user insight.

        Args:
            db: Database session
            insight_data: Insight creation data
            requesting_user: User creating the insight

        Returns:
            Created UserInsight instance

        Raises:
            PermissionDeniedError: If user doesn't have permission
        """
        # Only professionals and admins can create insights
        if requesting_user.role not in [UserRole.professional, UserRole.admin]:
            raise PermissionDeniedError(
                detail="Only professionals and admins can create insights"
            )

        # Check if user exists
        target_user = self.user_crud.get(db, id=insight_data.user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Set assessed_by to current user if not provided
        if not insight_data.assessed_by:
            insight_data.assessed_by = requesting_user.id

        # Create insight (multiple insights per user allowed)
        insight = self.crud.create(db, obj_in=insight_data)
        return insight

    # =====================================================================
    # READ OPERATIONS
    # =====================================================================

    def get_insight_by_id(
        self,
        db: Session,
        insight_id: UUID,
        requesting_user: UserAuth
    ) -> UserInsight:
        """
        Get insight by ID.

        Args:
            db: Database session
            insight_id: Insight UUID
            requesting_user: User requesting the insight

        Returns:
            UserInsight instance

        Raises:
            InsightNotFoundError: If insight not found
            PermissionDeniedError: If user doesn't have permission
        """
        insight = self.crud.get_by_id(db, id=insight_id)
        if not insight:
            raise InsightNotFoundError()

        # Check permission
        if not self._can_access_insight(insight, requesting_user):
            raise PermissionDeniedError(
                detail="You don't have permission to access this insight"
            )

        return insight

    def get_insights_by_user_id(
        self,
        db: Session,
        user_id: UUID,
        requesting_user: UserAuth
    ) -> List[UserInsight]:
        """
        Get all insights by user ID.

        Args:
            db: Database session
            user_id: User UUID
            requesting_user: User requesting the insights

        Returns:
            List of UserInsight instances

        Raises:
            PermissionDeniedError: If user doesn't have permission
        """
        # Check if requesting user can access this user's insights
        if requesting_user.role == UserRole.user and requesting_user.id != user_id:
            raise PermissionDeniedError(
                detail="You don't have permission to access these insights"
            )

        insights = self.crud.get_by_user_id(db, user_id=user_id)
        
        # Filter by permission for professionals
        if requesting_user.role == UserRole.professional:
            insights = [
                insight for insight in insights
                if self._can_access_insight(insight, requesting_user)
            ]
        
        return insights

    def get_my_insights(
        self,
        db: Session,
        requesting_user: UserAuth
    ) -> List[UserInsight]:
        """
        Get all insights for current user.

        Args:
            db: Database session
            requesting_user: Current user

        Returns:
            List of UserInsight instances
        """
        insights = self.crud.get_by_user_id(db, user_id=requesting_user.id)
        return insights

    def list_insights(
        self,
        db: Session,
        requesting_user: UserAuth,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserInsight]:
        """
        List insights (admin only).

        Args:
            db: Database session
            requesting_user: User requesting the list
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserInsight instances

        Raises:
            PermissionDeniedError: If user is not admin
        """
        # Only admins can list all insights
        if requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(
                detail="Only admins can list all insights"
            )

        return self.crud.get_multi(db, skip=skip, limit=limit)

    def list_my_assessments(
        self,
        db: Session,
        requesting_user: UserAuth,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserInsight]:
        """
        List insights created by current professional.

        Args:
            db: Database session
            requesting_user: Current user (must be professional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserInsight instances

        Raises:
            PermissionDeniedError: If user is not professional or admin
        """
        # Only professionals can see their assessments
        if requesting_user.role not in [UserRole.professional]:
            raise PermissionDeniedError(
                detail="Only professionals can view their assessments"
            )

        return self.crud.get_by_assessor(
            db,
            assessed_by=requesting_user.id,
            skip=skip,
            limit=limit
        )

    # =====================================================================
    # UPDATE OPERATIONS
    # =====================================================================

    def update_insight(
        self,
        db: Session,
        insight_id: UUID,
        update_data: UserInsightUpdate,
        requesting_user: UserAuth
    ) -> UserInsight:
        """
        Update insight.

        Args:
            db: Database session
            insight_id: Insight UUID
            update_data: Update data
            requesting_user: User updating the insight

        Returns:
            Updated UserInsight instance

        Raises:
            InsightNotFoundError: If insight not found
            PermissionDeniedError: If user doesn't have permission
        """
        insight = self.crud.get_by_id(db, id=insight_id)
        if not insight:
            raise InsightNotFoundError()

        # Check permission
        if not self._can_modify_insight(insight, requesting_user):
            raise PermissionDeniedError(
                detail="You don't have permission to modify this insight"
            )

        return self.crud.update(db, db_obj=insight, obj_in=update_data)

    # =====================================================================
    # DELETE OPERATIONS
    # =====================================================================

    def delete_insight(
        self,
        db: Session,
        insight_id: UUID,
        requesting_user: UserAuth
    ) -> UserInsight:
        """
        Delete insight.

        Args:
            db: Database session
            insight_id: Insight UUID
            requesting_user: User deleting the insight

        Returns:
            Deleted UserInsight instance

        Raises:
            InsightNotFoundError: If insight not found
            PermissionDeniedError: If user doesn't have permission
        """
        insight = self.crud.get_by_id(db, id=insight_id)
        if not insight:
            raise InsightNotFoundError()

        # Only admins can delete insights
        if requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(
                detail="Only admins can delete insights"
            )

        return self.crud.delete(db, id=insight_id)

    def delete_insights_by_user(
        self,
        db: Session,
        user_id: UUID,
        requesting_user: UserAuth
    ) -> Optional[UserInsight]:
        """
        Delete all insights for a specific user.

        Args:
            db: Database session
            user_id: User UUID
            requesting_user: User deleting the insights

        Returns:
            Deleted UserInsight instance or None

        Raises:
            PermissionDeniedError: If user doesn't have permission
        """
        # Only admins can delete insights
        if requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(
                detail="Only admins can delete insights"
            )

        return self.crud.delete_by_user_id(db, user_id=user_id)

    # =====================================================================
    # STATISTICS
    # =====================================================================

    def get_insight_count(
        self,
        db: Session,
        requesting_user: UserAuth
    ) -> int:
        """
        Get total count of insights (admin only).

        Args:
            db: Database session
            requesting_user: User requesting the count

        Returns:
            Total number of insights

        Raises:
            PermissionDeniedError: If user is not admin
        """
        if requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(
                detail="Only admins can view insight statistics"
            )

        return self.crud.count(db)

    def check_user_has_insight(
        self,
        db: Session,
        user_id: UUID,
        requesting_user: UserAuth
    ) -> bool:
        """
        Check if user has any insights.

        Args:
            db: Database session
            user_id: User UUID
            requesting_user: User making the request

        Returns:
            True if user has insights, False otherwise

        Raises:
            PermissionDeniedError: If user doesn't have permission
        """
        # Users can check their own, professionals and admins can check any
        if (requesting_user.role == UserRole.user and 
            requesting_user.id != user_id):
            raise PermissionDeniedError(
                detail="You don't have permission to check this information"
            )

        count = self.crud.exists(db, user_id=user_id)
        return count > 0


# =====================================================================
# SINGLETON INSTANCE
# =====================================================================

user_insight_service = UserInsightService()