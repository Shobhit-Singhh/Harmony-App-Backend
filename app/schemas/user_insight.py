# schemas/user_insight.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Any
from datetime import datetime
from uuid import UUID


# =====================================================================
# A. BASE SCHEMAS
# =====================================================================

class DemographicsBase(BaseModel):
    """Base demographics fields."""
    age: Optional[int] = Field(None, ge=0, le=150)
    living_situation: Optional[str] = Field(None, max_length=255)
    occupation: Optional[str] = Field(None, max_length=255)
    marital_status: Optional[str] = Field(None, max_length=50)
    education_level: Optional[str] = Field(None, max_length=255)


class MedicalHistoryBase(BaseModel):
    """Base medical history fields."""
    prior_diagnoses: Optional[List[str]] = None
    family_history: Optional[Dict[str, Any]] = None
    current_medications: Optional[List[Dict[str, Any]]] = None
    therapy_history: Optional[List[Dict[str, Any]]] = None
    lab_results: Optional[Dict[str, Any]] = None


class LifestyleFactorsBase(BaseModel):
    """Base lifestyle factors fields."""
    sleep_pattern: Optional[str] = Field(None, max_length=255)
    exercise_habits: Optional[str] = Field(None, max_length=255)
    substance_use: Optional[str] = Field(None, max_length=255)
    nutrition_pattern: Optional[str] = Field(None, max_length=255)
    risk_behaviors: Optional[Dict[str, Any]] = None


class PsychologicalAssessmentBase(BaseModel):
    """Base psychological assessment fields."""
    assessment_scales: Optional[Dict[str, Any]] = None
    resilience_score: Optional[Dict[str, Any]] = None
    coping_score: Optional[Dict[str, Any]] = None


class ConclusionBase(BaseModel):
    """Base conclusion fields."""
    caregiver_notes: Optional[str] = None
    therapy_goals: Optional[List[str]] = None
    clinician_summary: Optional[str] = None


class MetadataBase(BaseModel):
    """Base metadata fields."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    assessed_by: Optional[UUID] = None
    assessment_date: Optional[datetime] = None

# =====================================================================
# B. CREATE SCHEMAS
# =====================================================================

class UserInsightCreate(
    DemographicsBase,
    MedicalHistoryBase,
    LifestyleFactorsBase,
    PsychologicalAssessmentBase,
    ConclusionBase,
    MetadataBase
):
    """Schema for creating user insight."""
    user_id: UUID


# =====================================================================
# C. UPDATE SCHEMAS
# =====================================================================

class UserInsightUpdate(
    DemographicsBase,
    MedicalHistoryBase,
    LifestyleFactorsBase,
    PsychologicalAssessmentBase,
    ConclusionBase,
    MetadataBase
):
    """Schema for updating user insight (all fields optional)."""
    pass


# =====================================================================
# D. READ SCHEMAS
# =====================================================================

# Complete insight output
class UserInsightOut(
    DemographicsBase,
    MedicalHistoryBase,
    LifestyleFactorsBase,
    PsychologicalAssessmentBase,
    ConclusionBase,
    MetadataBase
):
    """Complete user insight output."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID


# Summary output (without detailed medical data)
class UserInsightSummary(BaseModel):
    """Summary view of user insight."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    age: Optional[int] = None
    occupation: Optional[str] = None
    assessment_date: Optional[datetime] = None
    assessed_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


# Sectioned output for better organization
class UserInsightSectioned(BaseModel):
    """Organized sectioned output."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    demographics: DemographicsBase
    medical_history: MedicalHistoryBase
    lifestyle_factors: LifestyleFactorsBase
    psychological_assessment: PsychologicalAssessmentBase
    conclusion: ConclusionBase
    metadata: MetadataBase