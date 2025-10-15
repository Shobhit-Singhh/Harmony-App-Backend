# =====================================================================
# UPDATED CRUD LAYER - crud/user_priorities.py
# =====================================================================

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.user_priorities import UserPriorities
from app.schemas.user_priorities import (
    UserPrioritiesCreate,
    UserPrioritiesUpdate,
    CompleteActivity,
    ActivityConfiguration,
    QuotaConfig,
    PillarName,
)


class CRUDUserPriorities:
    """CRUD operations for UserPriorities model."""

    # =====================================================================
    # CREATE OPERATIONS
    # =====================================================================

    def create(
        self, db: Session, *, user_id: UUID, obj_in: UserPrioritiesCreate
    ) -> UserPriorities:
        """Create user priorities."""
        obj_data = obj_in.model_dump(exclude_unset=True)

        db_obj = UserPriorities(id=user_id, **obj_data)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # =====================================================================
    # READ OPERATIONS
    # =====================================================================

    def get(self, db: Session, id: UUID) -> Optional[UserPriorities]:
        """Get priorities by user ID."""
        return db.query(UserPriorities).filter(UserPriorities.id == id).first()

    def get_by_user_id(self, db: Session, user_id: UUID) -> Optional[UserPriorities]:
        """Get priorities by user ID (alias for get)."""
        return self.get(db, id=user_id)

    # =====================================================================
    # UPDATE OPERATIONS
    # =====================================================================

    def update_priorities(
        self, db: Session, *, db_obj: UserPriorities, obj_in: UserPrioritiesUpdate
    ) -> UserPriorities:
        """Update user priorities."""
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db_obj.last_updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def complete_onboarding(
        self, db: Session, *, db_obj: UserPriorities
    ) -> UserPriorities:
        """Mark onboarding as complete."""
        db_obj.onboarding_completed_at = datetime.now(timezone.utc)
        db_obj.last_updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    # =====================================================================
    # DELETE OPERATIONS
    # =====================================================================

    def delete(self, db: Session, *, id: UUID) -> Optional[UserPriorities]:
        """Delete priorities by user ID."""
        obj = db.query(UserPriorities).filter(UserPriorities.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    # =====================================================================
    # UTILITY OPERATIONS
    # =====================================================================

    def exists(self, db: Session, *, user_id: UUID) -> bool:
        """Check if priorities exist for user."""
        return (
            db.query(UserPriorities).filter(UserPriorities.id == user_id).first()
            is not None
        )

    # =====================================================================
    # ACTIVITY CRUD OPERATIONS
    # =====================================================================

    def add_activity_to_pillar(
        self,
        db: Session,
        *,
        db_obj: UserPriorities,
        pillar: PillarName,
        activity: CompleteActivity,
    ) -> UserPriorities:
        """Add an activity to a specific pillar."""
        column_name = f"{pillar.value}_activities"

        existing_activities = getattr(db_obj, column_name)
        if existing_activities is None:
            existing_activities = []
        else:
            existing_activities = list(existing_activities)

        # Check for duplicate
        if any(act.get("name") == activity.name for act in existing_activities):
            raise ValueError(
                f"Activity '{activity.name}' already exists in {pillar.value}"
            )

        # Add activity as dict
        existing_activities.append(activity.model_dump())

        setattr(db_obj, column_name, existing_activities)
        flag_modified(db_obj, column_name)

        db_obj.last_updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_activity_in_pillar(
        self,
        db: Session,
        *,
        db_obj: UserPriorities,
        pillar: PillarName,
        activity_name: str,
        updates: Dict[str, Any],
    ) -> UserPriorities:
        """Update an existing activity in a pillar."""
        column_name = f"{pillar.value}_activities"
        existing_activities = getattr(db_obj, column_name)

        if not existing_activities:
            raise ValueError(f"No activities found in {pillar.value}")

        existing_activities = list(existing_activities)

        activity_found = False
        for activity in existing_activities:
            if activity.get("name") == activity_name:
                activity_found = True

                # Update top-level fields
                if "description" in updates:
                    activity["description"] = updates["description"]

                if "pillar" in updates:
                    activity["pillar"] = updates["pillar"]

                # Update configuration fields
                config = activity.get("configuration", {})

                if "dimension" in updates:
                    config["dimension"] = updates["dimension"]

                if "complete" in updates:
                    config["complete"] = updates["complete"]

                if "unit" in updates:
                    config["unit"] = updates["unit"]

                # Update quota fields
                quota = config.get("quota", {})
                if "quota_value" in updates:
                    quota["value"] = updates["quota_value"]
                if "reset_frequency" in updates:
                    quota["reset_frequency"] = updates["reset_frequency"]

                config["quota"] = quota
                activity["configuration"] = config
                break

        if not activity_found:
            raise ValueError(f"Activity '{activity_name}' not found in {pillar.value}")

        setattr(db_obj, column_name, existing_activities)
        flag_modified(db_obj, column_name)

        db_obj.last_updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_activity_from_pillar(
        self,
        db: Session,
        *,
        db_obj: UserPriorities,
        pillar: PillarName,
        activity_name: str,
    ) -> UserPriorities:
        """Remove an activity from a pillar."""
        column_name = f"{pillar.value}_activities"
        existing_activities = getattr(db_obj, column_name)

        if not existing_activities:
            existing_activities = []

        updated_activities = [
            act for act in existing_activities if act.get("name") != activity_name
        ]

        if len(updated_activities) == len(existing_activities):
            raise ValueError(f"Activity '{activity_name}' not found in {pillar.value}")

        setattr(db_obj, column_name, updated_activities)
        flag_modified(db_obj, column_name)

        db_obj.last_updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_activities_for_pillar(
        self, db_obj: UserPriorities, pillar: PillarName
    ) -> List[Dict[str, Any]]:
        """Get all activities for a specific pillar."""
        column_name = f"{pillar.value}_activities"
        return getattr(db_obj, column_name) or []

    def get_all_activities(
        self, db_obj: UserPriorities
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all activities across all pillars."""
        return {
            "health": db_obj.health_activities or [],
            "work": db_obj.work_activities or [],
            "growth": db_obj.growth_activities or [],
            "relationships": db_obj.relationships_activities or [],
        }

    def bulk_add_activities(
        self,
        db: Session,
        *,
        db_obj: UserPriorities,
        activities_by_pillar: Dict[str, List[CompleteActivity]],
    ) -> UserPriorities:
        """Add multiple activities at once."""
        for pillar_name, activities in activities_by_pillar.items():
            try:
                pillar = PillarName(pillar_name.lower())
            except ValueError:
                continue

            column_name = f"{pillar.value}_activities"
            existing_activities = getattr(db_obj, column_name)

            if existing_activities is None:
                existing_activities = []
            else:
                existing_activities = list(existing_activities)

            for activity in activities:
                if not any(
                    act.get("name") == activity.name for act in existing_activities
                ):
                    existing_activities.append(activity.model_dump())

            setattr(db_obj, column_name, existing_activities)
            flag_modified(db_obj, column_name)

        db_obj.last_updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_activity_progress(
        self,
        db: Session,
        *,
        db_obj: UserPriorities,
        pillar: PillarName,
        activity_name: str,
        complete_value: int,
    ) -> UserPriorities:
        """Update the progress (complete) value for an activity."""
        column_name = f"{pillar.value}_activities"
        existing_activities = getattr(db_obj, column_name)

        if not existing_activities:
            raise ValueError(f"No activities found in {pillar.value}")

        existing_activities = list(existing_activities)

        activity_found = False
        for activity in existing_activities:
            if activity.get("name") == activity_name:
                activity_found = True
                config = activity.get("configuration", {})
                config["complete"] = complete_value
                activity["configuration"] = config
                break

        if not activity_found:
            raise ValueError(f"Activity '{activity_name}' not found in {pillar.value}")

        setattr(db_obj, column_name, existing_activities)
        flag_modified(db_obj, column_name)

        db_obj.last_updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_obj)
        return db_obj


crud_user_priorities = CRUDUserPriorities()
