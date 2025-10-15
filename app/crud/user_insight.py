# crud/user_insight.py
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user_insight import UserInsight
from app.schemas.user_insight import (
    UserInsightCreate,
    UserInsightUpdate
)


class CRUDUserInsight:
    """CRUD operations for UserInsight model."""

    # =====================================================================
    # CREATE OPERATIONS
    # =====================================================================

    def create(self, db: Session, *, obj_in: UserInsightCreate) -> UserInsight:
        """
        Create a new user insight.

        Args:
            db: Database session
            obj_in: UserInsightCreate schema with insight data

        Returns:
            Created UserInsight instance
        """
        # Convert Pydantic model to dict
        obj_data = obj_in.model_dump(exclude_unset=True)
        
        # Create insight instance
        db_obj = UserInsight(**obj_data)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # =====================================================================
    # READ OPERATIONS
    # =====================================================================

    def get(self, db: Session, id: UUID) -> Optional[UserInsight]:
        """
        Get insight by ID.

        Args:
            db: Database session
            id: Insight UUID

        Returns:
            UserInsight instance or None
        """
        return db.query(UserInsight).filter(UserInsight.id == id).first()

    def get_by_id(self, db: Session, id: UUID) -> Optional[UserInsight]:
        """
        Get insight by ID.

        Args:
            db: Database session
            id: Insight UUID

        Returns:
            UserInsight instance or None
        """
        return db.query(UserInsight).filter(UserInsight.id == id).first()

    def get_by_user_id(self, db: Session, user_id: UUID) -> List[UserInsight]:
        """
        Get insight by user ID.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            UserInsight instance or None
        """
        return db.query(UserInsight).filter(UserInsight.user_id == user_id).all()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[UserInsight]:
        """
        Get multiple insights with pagination.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserInsight instances
        """
        return db.query(UserInsight).offset(skip).limit(limit).all()

    def get_by_assessor(
        self, db: Session, *, assessed_by: UUID, skip: int = 0, limit: int = 100
    ) -> List[UserInsight]:
        """
        Get insights by assessor (professional/admin who created the assessment).

        Args:
            db: Database session
            assessed_by: Assessor UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserInsight instances
        """
        return (
            db.query(UserInsight)
            .filter(UserInsight.assessed_by == assessed_by)
            .offset(skip)
            .limit(limit)
            .all()
        )

    # =====================================================================
    # UPDATE OPERATIONS
    # =====================================================================

    def update(
        self, db: Session, *, db_obj: UserInsight, obj_in: UserInsightUpdate
    ) -> UserInsight:
        """
        Update user insight (full update).

        Args:
            db: Database session
            db_obj: Existing UserInsight instance
            obj_in: UserInsightUpdate schema with updated data

        Returns:
            Updated UserInsight instance
        """
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db_obj.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # =====================================================================
    # DELETE OPERATIONS
    # =====================================================================

    def delete(self, db: Session, *, id: UUID) -> Optional[UserInsight]:
        """
        Delete insight by ID.

        Args:
            db: Database session
            id: Insight UUID

        Returns:
            Deleted UserInsight instance or None
        """
        obj = db.query(UserInsight).filter(UserInsight.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def delete_by_user_id(self, db: Session, *, user_id: UUID) -> Optional[UserInsight]:
        """
        Delete insight by user ID.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Deleted UserInsight instance or None
        """
        obj = db.query(UserInsight).filter(UserInsight.user_id == user_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    # =====================================================================
    # UTILITY OPERATIONS
    # =====================================================================

    def exists(self, db: Session, *, user_id: UUID) -> int:
        """
        Check if insight exists for user.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            True if insight exists, False otherwise
        """
        return db.query(UserInsight).filter(UserInsight.user_id == user_id).count()

    def count(self, db: Session) -> int:
        """
        Get total count of insights.

        Args:
            db: Database session

        Returns:
            Total number of insights
        """
        return db.query(UserInsight).count()


# Create singleton instance
crud_user_insight = CRUDUserInsight()