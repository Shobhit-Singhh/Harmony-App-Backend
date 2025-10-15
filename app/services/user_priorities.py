# =====================================================================
# UPDATED SERVICE LAYER - services/user_priorities.py
# =====================================================================

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user_priorities import UserPriorities
from app.models.user_auth import UserAuth, UserRole
from app.schemas.user_priorities import (
    UserPrioritiesCreate,
    UserPrioritiesUpdate,
    AddActivityRequest,
    BulkAddActivitiesRequest,
    CompleteActivity,
    ActivityConfiguration,
    QuotaConfig,
    PillarName,
    DimensionType,
    FrequencyUnit,
    DIMENSION_UNITS,
)
from app.crud.user_priorities import crud_user_priorities
from app.data.activity_repository import ACTIVITY_REPOSITORY, PillarType


class PrioritiesNotFoundError(HTTPException):
    def __init__(self, detail: str = "Priorities not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class PrioritiesAlreadyExistError(HTTPException):
    def __init__(self, detail: str = "Priorities already exist"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class PermissionDeniedError(HTTPException):
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UserPrioritiesService:
    """Service layer for user priorities."""

    def __init__(self):
        self.priorities_crud = crud_user_priorities

    # =====================================================================
    # PERMISSION HELPERS
    # =====================================================================

    def _can_access_priorities(
        self, priorities: UserPriorities, requesting_user: UserAuth
    ) -> bool:
        """Check if user can access priorities."""
        if requesting_user.role in {UserRole.admin, UserRole.professional}:
            return True
        return priorities.id == requesting_user.id

    def _can_modify_priorities(
        self, priorities: UserPriorities, requesting_user: UserAuth
    ) -> bool:
        """Check if user can modify priorities."""
        return priorities.id == requesting_user.id

    # =====================================================================
    # CREATE OPERATIONS
    # =====================================================================

    def create_priorities(
        self,
        db: Session,
        priorities_data: UserPrioritiesCreate,
        requesting_user: UserAuth,
    ) -> UserPriorities:
        """Create user priorities."""
        if self.priorities_crud.exists(db, user_id=requesting_user.id):
            raise PrioritiesAlreadyExistError()

        return self.priorities_crud.create(
            db, user_id=requesting_user.id, obj_in=priorities_data
        )

    # =====================================================================
    # READ OPERATIONS
    # =====================================================================

    def get_my_priorities(
        self, db: Session, requesting_user: UserAuth
    ) -> UserPriorities:
        """Get priorities for current user."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=requesting_user.id)
        if not priorities:
            raise PrioritiesNotFoundError("You haven't set up your priorities yet")
        return priorities

    def get_priorities_by_user_id(
        self, db: Session, user_id: UUID, requesting_user: UserAuth
    ) -> UserPriorities:
        """Get priorities by user ID."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError()

        if not self._can_access_priorities(priorities, requesting_user):
            raise PermissionDeniedError()

        return priorities

    # =====================================================================
    # UPDATE OPERATIONS
    # =====================================================================

    def update_my_priorities(
        self, db: Session, update_data: UserPrioritiesUpdate, requesting_user: UserAuth
    ) -> UserPriorities:
        """Update current user's priorities."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=requesting_user.id)
        if not priorities:
            raise PrioritiesNotFoundError()

        return self.priorities_crud.update_priorities(
            db, db_obj=priorities, obj_in=update_data
        )

    def complete_onboarding(
        self, db: Session, requesting_user: UserAuth
    ) -> UserPriorities:
        """Mark onboarding as complete."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=requesting_user.id)
        if not priorities:
            raise PrioritiesNotFoundError()

        return self.priorities_crud.complete_onboarding(db, db_obj=priorities)

    # =====================================================================
    # DELETE OPERATIONS
    # =====================================================================

    def delete_priorities(
        self, db: Session, user_id: UUID, requesting_user: UserAuth
    ) -> UserPriorities:
        """Delete priorities."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError()

        if not self._can_modify_priorities(priorities, requesting_user):
            raise PermissionDeniedError()

        return self.priorities_crud.delete(db, id=user_id)

    # =====================================================================
    # ACTIVITY TEMPLATE OPERATIONS
    # =====================================================================

    def get_all_activity_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all activity templates grouped by pillar."""
        grouped = {pillar.value: [] for pillar in PillarName}

        for activity in ACTIVITY_REPOSITORY:
            for pillar in activity.get("pillars", []):
                if hasattr(pillar, "value"):
                    grouped[pillar.value].append(
                        {
                            "name": activity["name"],
                            "description": activity["description"],
                            "pillars": [p.value for p in activity["pillars"]],
                        }
                    )

        return grouped

    def get_activity_templates_by_pillar(self, pillar: str) -> List[Dict[str, Any]]:
        """Get activity templates for a specific pillar."""
        try:
            pillar_enum = PillarName(pillar.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pillar: {pillar}. Must be one of: health, work, growth, relationships",
            )

        templates = []
        for activity in ACTIVITY_REPOSITORY:
            if any(p.value == pillar_enum.value for p in activity.get("pillars", [])):
                templates.append(
                    {
                        "name": activity["name"],
                        "description": activity["description"],
                        "pillars": [p.value for p in activity["pillars"]],
                    }
                )

        return templates

    def get_activity_template(self, activity_name: str) -> Dict[str, Any]:
        """Get a specific activity template by name."""
        for activity in ACTIVITY_REPOSITORY:
            if activity["name"].lower() == activity_name.lower():
                return {
                    "name": activity["name"],
                    "description": activity["description"],
                    "pillars": [p.value for p in activity["pillars"]],
                }

        raise HTTPException(
            status_code=404, detail=f"Activity template '{activity_name}' not found"
        )

    def get_dimension_units(self, dimension: str) -> List[str]:
        """Get available units for a dimension."""
        try:
            dimension_enum = DimensionType(dimension.lower())
            return DIMENSION_UNITS.get(dimension_enum, [])
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail=f"Dimension not found: {dimension}. Valid dimensions: {[d.value for d in DimensionType]}",
            )

    def get_all_dimension_options(self) -> List[Dict[str, Any]]:
        """Get all dimensions with their units."""
        return [
            {"dimension": dimension.value, "units": DIMENSION_UNITS[dimension]}
            for dimension in DimensionType
        ]

    # =====================================================================
    # ACTIVITY BUILDING
    # =====================================================================

    def build_activity(
        self,
        name: str,
        description: str,
        pillar: PillarName,
        dimension: DimensionType,
        complete: int,
        unit: str,
        quota_value: float,
        reset_frequency: FrequencyUnit,
    ) -> Dict[str, Any]:
        """
        Build a custom activity configuration with validation.
        Returns a validated activity configuration ready to be added.
        """
        # Validate unit matches dimension
        valid_units = DIMENSION_UNITS.get(dimension, [])
        if unit not in valid_units:
            raise HTTPException(
                status_code=400,
                detail=f"Unit '{unit}' is not valid for dimension '{dimension.value}'. Valid units: {valid_units}",
            )

        # Build complete activity structure
        activity = CompleteActivity(
            name=name,
            description=description,
            pillar=pillar,
            configuration=ActivityConfiguration(
                dimension=dimension,
                complete=complete,
                unit=unit,
                quota=QuotaConfig(value=quota_value, reset_frequency=reset_frequency),
            ),
        )

        return activity.model_dump()

    # =====================================================================
    # USER ACTIVITY CRUD OPERATIONS
    # =====================================================================

    def add_user_activity(
        self,
        db: Session,
        user_id: UUID,
        pillar: PillarName,
        name: str,
        description: str,
        dimension: DimensionType,
        complete: int,
        unit: str,
        quota_value: float,
        reset_frequency: FrequencyUnit,
    ) -> UserPriorities:
        """Add an activity to user's pillar."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError()

        # Validate unit matches dimension
        valid_units = DIMENSION_UNITS.get(dimension, [])
        if unit not in valid_units:
            raise HTTPException(
                status_code=400,
                detail=f"Unit '{unit}' is not valid for dimension '{dimension.value}'. Valid units: {valid_units}",
            )

        # Build complete activity
        activity = CompleteActivity(
            name=name,
            description=description,
            pillar=pillar,
            configuration=ActivityConfiguration(
                dimension=dimension,
                complete=complete,
                unit=unit,
                quota=QuotaConfig(value=quota_value, reset_frequency=reset_frequency),
            ),
        )

        try:
            updated_priorities = self.priorities_crud.add_activity_to_pillar(
                db=db, db_obj=priorities, pillar=pillar, activity=activity
            )
            return updated_priorities
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    def update_user_activity(
        self,
        db: Session,
        user_id: UUID,
        pillar: str,
        activity_name: str,
        dimension: Optional[str] = None,
        complete: Optional[int] = None,
        unit: Optional[str] = None,
        quota_value: Optional[float] = None,
        reset_frequency: Optional[str] = None,
        description: Optional[str] = None,
    ) -> UserPriorities:
        """Update an existing activity."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError()

        # Validate pillar
        try:
            pillar_enum = PillarName(pillar.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pillar: {pillar}. Must be one of: health, work, growth, relationships",
            )

        # Build updates dict
        updates = {}
        if description is not None:
            updates["description"] = description
        if dimension is not None:
            updates["dimension"] = dimension
        if complete is not None:
            updates["complete"] = complete
        if unit is not None:
            updates["unit"] = unit
        if quota_value is not None:
            updates["quota_value"] = quota_value
        if reset_frequency is not None:
            updates["reset_frequency"] = reset_frequency

        # Validate unit matches dimension if both provided
        if dimension and unit:
            try:
                dim_enum = DimensionType(dimension.lower())
                valid_units = DIMENSION_UNITS.get(dim_enum, [])
                if unit not in valid_units:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unit '{unit}' is not valid for dimension '{dimension}'. Valid units: {valid_units}",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid dimension: {dimension}"
                )

        try:
            updated_priorities = self.priorities_crud.update_activity_in_pillar(
                db=db,
                db_obj=priorities,
                pillar=pillar_enum,
                activity_name=activity_name,
                updates=updates,
            )
            return updated_priorities
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    def update_activity_progress(
        self,
        db: Session,
        user_id: UUID,
        pillar: str,
        activity_name: str,
        complete_value: int,
    ) -> UserPriorities:
        """Update the progress (complete) value for an activity."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError()

        # Validate pillar
        try:
            pillar_enum = PillarName(pillar.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pillar: {pillar}. Must be one of: health, work, growth, relationships",
            )

        # Validate complete value
        if complete_value < 0:
            raise HTTPException(
                status_code=400,
                detail="Progress value (complete) must be non-negative",
            )

        try:
            updated_priorities = self.priorities_crud.update_activity_progress(
                db=db,
                db_obj=priorities,
                pillar=pillar_enum,
                activity_name=activity_name,
                complete_value=complete_value,
            )
            return updated_priorities
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    def remove_user_activity(
        self, db: Session, user_id: UUID, pillar: str, activity_name: str
    ) -> UserPriorities:
        """Remove an activity from user's pillar."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError()

        # Validate pillar
        try:
            pillar_enum = PillarName(pillar.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pillar: {pillar}. Must be one of: health, work, growth, relationships",
            )

        try:
            updated_priorities = self.priorities_crud.delete_activity_from_pillar(
                db=db,
                db_obj=priorities,
                pillar=pillar_enum,
                activity_name=activity_name,
            )
            return updated_priorities
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    def get_user_activities_by_pillar(
        self, db: Session, user_id: UUID, pillar: str
    ) -> List[Dict[str, Any]]:
        """Get all activities for a specific pillar."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError()

        try:
            pillar_enum = PillarName(pillar.lower())
            return self.priorities_crud.get_activities_for_pillar(
                priorities, pillar_enum
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pillar: {pillar}. Must be one of: health, work, growth, relationships",
            )

    def get_all_user_activities(
        self, db: Session, user_id: UUID
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all activities across all pillars."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError()

        return self.priorities_crud.get_all_activities(priorities)

    def bulk_add_user_activities(
        self, db: Session, user_id: UUID, activities: List[AddActivityRequest]
    ) -> UserPriorities:
        """Add multiple activities at once."""
        priorities = self.priorities_crud.get_by_user_id(db, user_id=user_id)
        if not priorities:
            raise PrioritiesNotFoundError()

        activities_by_pillar = {}
        errors = []

        for activity_request in activities:
            try:
                # Validate unit matches dimension
                valid_units = DIMENSION_UNITS.get(activity_request.dimension, [])
                if activity_request.unit not in valid_units:
                    errors.append(
                        f"Skipped '{activity_request.name}': Unit '{activity_request.unit}' "
                        f"not valid for dimension '{activity_request.dimension.value}'"
                    )
                    continue

                # Build activity
                activity = CompleteActivity(
                    name=activity_request.name,
                    description=activity_request.description,
                    pillar=activity_request.pillar,
                    configuration=ActivityConfiguration(
                        dimension=activity_request.dimension,
                        complete=activity_request.complete,
                        unit=activity_request.unit,
                        quota=QuotaConfig(
                            value=activity_request.quota_value,
                            reset_frequency=activity_request.reset_frequency,
                        ),
                    ),
                )

                pillar = activity_request.pillar.value
                if pillar not in activities_by_pillar:
                    activities_by_pillar[pillar] = []

                activities_by_pillar[pillar].append(activity)
            except Exception as e:
                errors.append(f"Skipped '{activity_request.name}': {str(e)}")

        try:
            updated_priorities = self.priorities_crud.bulk_add_activities(
                db=db, db_obj=priorities, activities_by_pillar=activities_by_pillar
            )
            return updated_priorities
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # =====================================================================
    # UTILITY
    # =====================================================================

    def check_user_has_priorities(self, db: Session, user_id: UUID) -> bool:
        """Check if user has priorities set up."""
        return self.priorities_crud.exists(db, user_id=user_id)


user_priorities_service = UserPrioritiesService()
