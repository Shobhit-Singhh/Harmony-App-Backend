# schemas/user_priorities.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from uuid import UUID
from app.data.activity_repository import PillarType
from enum import Enum


# =====================================================================
# ENUMS
# =====================================================================

class PillarName(str, Enum):
    """Life pillar categories."""

    health = "health"
    work = "work"
    growth = "growth"
    relationships = "relationships"


class DimensionType(str, Enum):
    """Measurement dimension types."""

    time = "time"
    distance = "distance"
    weight = "weight"
    volume = "volume"
    count = "count"
    rating = "rating"
    boolean = "boolean"
    text = "text"


class FrequencyUnit(str, Enum):
    """Frequency units for quotas."""
    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


# =====================================================================
# DIMENSION UNITS MAPPING
# =====================================================================

DIMENSION_UNITS = {
    DimensionType.time: ["minutes", "hours"],
    DimensionType.distance: ["steps", "km", "miles", "meters"],
    DimensionType.weight: ["kg", "lbs", "grams"],
    DimensionType.volume: ["liters", "ml", "gallons"],
    DimensionType.count: [
        "count",
        "times",
        "repetitions",
        "pages",
        "books",
        "people",
        "messages",
    ],
    DimensionType.rating: ["rating", "stars"],
    DimensionType.boolean: ["completed"],
    DimensionType.text: ["text"],
}


# =====================================================================
# ACTIVITY SCHEMAS
# =====================================================================

class QuotaConfig(BaseModel):
    """Quota configuration for activities."""

    value: float = Field(..., gt=0, description="Target value for the quota")
    reset_frequency: FrequencyUnit = Field()

    class Config:
        json_schema_extra = {"example": {"value": 10000, "reset_frequency": "daily"}}


class ActivityConfiguration(BaseModel):
    """Complete activity configuration."""

    dimension: DimensionType = Field(..., description="Type of measurement")
    complete: int = Field(default=0, ge=0, description="Current progress value")
    unit: str = Field(..., description="Measurement unit")
    quota: QuotaConfig = Field(..., description="Target quota configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "dimension": "distance",
                "complete": 5000,
                "unit": "steps",
                "quota": {"value": 10000, "reset_frequency": "daily"},
            }
        }


class CompleteActivity(BaseModel):
    """Complete activity with all details."""

    name: str = Field(..., min_length=1, max_length=100, description="Activity name")
    description: str = Field(..., min_length=1, max_length=500, description="Activity description")
    pillar: PillarName = Field(..., description="Associated life pillar")
    configuration: ActivityConfiguration = Field(
        ..., description="Activity configuration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Morning Walk",
                "description": "Daily morning walk for fitness",
                "pillar": "health",
                "configuration": {
                    "dimension": "distance",
                    "complete": 5000,
                    "unit": "steps",
                    "quota": {"value": 10000, "reset_frequency": "daily"},
                },
            }
        }


# =====================================================================
# USER PROFILE SCHEMAS
# =====================================================================

class MinimalProfileBase(BaseModel):
    """Minimal profile information."""
    display_name: Optional[str] = Field(None, max_length=255)
    age_group: Optional[str] = Field(None, max_length=50)
    gender_identity: Optional[str] = Field(None, max_length=50)
    preferred_pronouns: Optional[str] = Field(None, max_length=50)


class PillarImportanceBase(BaseModel):
    """Pillar importance ranking (must sum to 1.0)."""
    pillar_importance: Optional[Dict[str, float]] = Field(
        None,
        description="Importance weights for each pillar (must sum to 1.0)",
    )

    @field_validator("pillar_importance")
    @classmethod
    def validate_pillar_importance(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if v is not None:
            total = sum(v.values())
            if not (0.99 <= total <= 1.01):
                raise ValueError("Pillar importance values must sum to 1.0")
            
            valid_pillars = {p.value for p in PillarName}
            if not all(key in valid_pillars for key in v.keys()):
                raise ValueError(f"Invalid pillar names. Must be one of: {valid_pillars}")
        return v


# =====================================================================
# PILLAR SCHEMAS
# =====================================================================

class HealthPillarBase(BaseModel):
    """Health pillar configuration."""
    health_goals: Optional[str] = None
    health_baseline: Optional[str] = None
    health_activities: Optional[List[CompleteActivity]] = Field(default_factory=list)


class WorkPillarBase(BaseModel):
    """Work pillar configuration."""
    work_goals: Optional[str] = None
    work_baseline: Optional[str] = None
    work_activities: Optional[List[CompleteActivity]] = Field(default_factory=list)


class GrowthPillarBase(BaseModel):
    """Growth pillar configuration."""
    growth_goals: Optional[str] = None
    growth_baseline: Optional[str] = None
    growth_activities: Optional[List[CompleteActivity]] = Field(default_factory=list)


class RelationshipsPillarBase(BaseModel):
    """Relationships pillar configuration."""
    relationships_goals: Optional[str] = None
    relationships_baseline: Optional[str] = None
    relationships_activities: Optional[List[CompleteActivity]] = Field(default_factory=list)


class PreferencesBase(BaseModel):
    """User preferences and engagement."""
    checkin_schedule: Optional[Dict[str, Any]] = None
    privacy_settings: Optional[Dict[str, Any]] = None
    notification_preferences: Optional[Dict[str, Any]] = None


# =====================================================================
# CRUD SCHEMAS
# =====================================================================

class UserPrioritiesCreate(
    MinimalProfileBase,
    PillarImportanceBase,
    HealthPillarBase,
    WorkPillarBase,
    GrowthPillarBase,
    RelationshipsPillarBase,
    PreferencesBase,
):
    """Schema for creating user priorities."""
    pass


class UserPrioritiesUpdate(
    MinimalProfileBase,
    PillarImportanceBase,
    HealthPillarBase,
    WorkPillarBase,
    GrowthPillarBase,
    RelationshipsPillarBase,
    PreferencesBase,
):
    """Schema for updating user priorities (all fields optional)."""
    pass


class UserPrioritiesOut(
    MinimalProfileBase,
    PillarImportanceBase,
    HealthPillarBase,
    WorkPillarBase,
    GrowthPillarBase,
    RelationshipsPillarBase,
    PreferencesBase,
):
    """Complete user priorities output."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class UserPrioritiesSummary(MinimalProfileBase):
    """Summary view of user priorities."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class OnboardingComplete(BaseModel):
    """Mark onboarding as complete."""
    completed: bool = True


# =====================================================================
# ACTIVITY REQUEST SCHEMAS
# =====================================================================


class AddActivityRequest(BaseModel):
    """Request to add an activity to a pillar."""

    name: str = Field(..., min_length=1, max_length=100, description="Activity name")
    description: str = Field(
        ..., min_length=1, max_length=500, description="Activity description"
    )
    pillar: PillarName = Field(..., description="Target pillar for this activity")
    dimension: DimensionType = Field(..., description="Measurement dimension")
    complete: int = Field(default=0, ge=0, description="Initial progress value")
    unit: str = Field(..., description="Measurement unit")
    quota_value: float = Field(..., gt=0, description="Target quota value")
    reset_frequency: FrequencyUnit = Field(..., description="Quota reset frequency")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str, info) -> str:
        """Validate unit matches dimension."""
        dimension = info.data.get("dimension")
        if dimension and v not in DIMENSION_UNITS.get(dimension, []):
            raise ValueError(f"Unit '{v}' not valid for dimension '{dimension}'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Morning Walk",
                "description": "Daily morning walk for fitness",
                "pillar": "health",
                "dimension": "distance",
                "complete": 5000,
                "unit": "steps",
                "quota_value": 10000,
                "reset_frequency": "daily",
            }
        }


class BulkAddActivitiesRequest(BaseModel):
    """Request to add multiple activities at once."""

    activities: List[AddActivityRequest] = Field(
        ..., min_items=1, max_items=50, description="List of activities to add"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "activities": [
                    {
                        "name": "Morning Walk",
                        "description": "Daily morning walk",
                        "pillar": "health",
                        "dimension": "distance",
                        "complete": 5000,
                        "unit": "steps",
                        "quota_value": 10000,
                        "reset_frequency": "daily",
                    },
                    {
                        "name": "Reading",
                        "description": "Daily reading habit",
                        "pillar": "growth",
                        "dimension": "time",
                        "complete": 15,
                        "unit": "minutes",
                        "quota_value": 30,
                        "reset_frequency": "daily",
                    },
                ]
            }
        }


# =====================================================================
# ACTIVITY BUILD REQUEST SCHEMA
# =====================================================================


class BuildActivityRequest(BaseModel):
    """Request to build/configure an activity before adding it."""

    name: str = Field(..., min_length=1, max_length=100, description="Activity name")
    description: str = Field(
        ..., min_length=1, max_length=500, description="Activity description"
    )
    pillar: PillarName = Field(..., description="Target pillar")
    dimension: DimensionType = Field(..., description="Measurement dimension")
    complete: int = Field(default=0, ge=0, description="Initial progress value")
    unit: str = Field(..., description="Measurement unit")
    quota_value: float = Field(..., gt=0, description="Target quota value")
    reset_frequency: FrequencyUnit = Field(..., description="Quota reset frequency")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str, info) -> str:
        """Validate unit matches dimension."""
        dimension = info.data.get("dimension")
        if dimension and v not in DIMENSION_UNITS.get(dimension, []):
            raise ValueError(f"Unit '{v}' not valid for dimension '{dimension}'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Morning Walk",
                "description": "Daily morning walk for fitness",
                "pillar": "health",
                "dimension": "distance",
                "complete": 5000,
                "unit": "steps",
                "quota_value": 10000,
                "reset_frequency": "daily",
            }
        }


# =====================================================================
# RESPONSE SCHEMAS
# =====================================================================


class ActivityResponse(BaseModel):
    """Response for single activity operations."""

    message: str = Field(..., description="Success message")
    activity: Optional[CompleteActivity] = Field(None, description="Activity details")
    pillar: PillarName = Field(..., description="Associated pillar")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Activity added successfully",
                "activity": {
                    "name": "Morning Walk",
                    "description": "Daily morning walk",
                    "pillar": "health",
                    "configuration": {
                        "dimension": "distance",
                        "complete": 5000,
                        "unit": "steps",
                        "quota": {"value": 10000, "reset_frequency": "daily"},
                    },
                },
                "pillar": "health",
            }
        }


class BulkActivityResponse(BaseModel):
    """Response for bulk activity operations."""

    message: str = Field(..., description="Overall result message")
    added_count: int = Field(..., description="Number of activities successfully added")
    skipped_count: int = Field(..., description="Number of activities skipped")
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages for skipped activities",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Bulk add completed",
                "added_count": 3,
                "skipped_count": 1,
                "errors": ["Skipped 'Running': Activity already exists"],
            }
        }

    """Response for bulk activity operations."""
    message: str
    added: int
    failed: int
    details: Optional[List[str]] = None


# =====================================================================
# UTILITY SCHEMAS
# =====================================================================


class DimensionUnitsResponse(BaseModel):
    """Response schema for dimension units."""

    dimension: DimensionType
    units: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "dimension": "distance",
                "units": ["steps", "km", "miles", "meters"],
            }
        }


class ActivityTemplateResponse(BaseModel):
    """Response schema for activity templates."""

    name: str
    description: str
    pillars: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Walking",
                "description": "Track your daily walking activity",
                "pillars": ["health"],
            }
        }


# =====================================================================
# ACTIVITY UPDATE REQUEST SCHEMAS
# =====================================================================


class UpdateActivityProgressRequest(BaseModel):
    """Request to update just the progress of an activity."""

    complete: int = Field(..., ge=0, description="New progress value")

    class Config:
        json_schema_extra = {"example": {"complete": 7500}}


class UpdateActivityRequest(BaseModel):
    """Request to update an activity's configuration."""

    description: Optional[str] = Field(None, min_length=1, max_length=500)
    dimension: Optional[DimensionType] = None
    complete: Optional[int] = Field(None, ge=0)
    unit: Optional[str] = None
    quota_value: Optional[float] = Field(None, gt=0)
    reset_frequency: Optional[FrequencyUnit] = None

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: Optional[str], info) -> Optional[str]:
        """Validate unit matches dimension if both provided."""
        if v is None:
            return v
        dimension = info.data.get("dimension")
        if dimension and v not in DIMENSION_UNITS.get(dimension, []):
            raise ValueError(f"Unit '{v}' not valid for dimension '{dimension}'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "description": "Updated description",
                "complete": 8000,
                "quota_value": 12000,
            }
        }