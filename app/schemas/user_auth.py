# schemas/user_auth.py
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
import enum


# =====================================================================
# ENUMS
# =====================================================================

class UserRole(str, enum.Enum):
    user = "user"
    professional = "professional"
    admin = "admin"


class Status(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    deactivated = "deactivated"


# =====================================================================
# 1. BASE SCHEMAS
# =====================================================================

# username, email, phone_number
class UserAuthBase(BaseModel):
    """Base read schema with common public fields."""
    username: Optional[str]
    email: EmailStr
    phone_number: Optional[str]

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Phone number must contain only digits, spaces, + and -')
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Invalid email address')
        return v

# password_hash
class UserAuthPasswordHash(BaseModel):
    """Password hash field for internal use only."""
    password_hash: str

# is_verified, created_at, updated_at
class UserAuthVerification(BaseModel):
    """Shared verification and status fields."""
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime

# is_verified, failed_login_attempts, lockout_until, last_login_at, password_changed_at
class UserAuthSecurity(BaseModel):
    """Shared security and tracking fields."""
    last_login_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    lockout_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None

# =====================================================================
# 2. CREATE SCHEMAS
# =====================================================================

class UserAuthCreate(UserAuthBase, UserAuthPasswordHash):
    """Admin-level user creation with role and status."""
    role: UserRole = Field(..., description="Role assigned to the user")
    status: Status = Status.active

# =====================================================================
# 3. UPDATE SCHEMAS
# =====================================================================

class UserAuthUpdate(UserAuthBase):
    """General update - all optional, excludes immutable fields."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None

class UserAuthUpdatePassword(BaseModel):
    """Restricted update - password change."""
    old_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserAuthRoleUpdate(BaseModel):
    """Restricted update - role change (admin only)."""
    role: UserRole

class UserAuthStatusUpdate(BaseModel):
    """Restricted update - status change (admin only)."""
    status: Status

class UserAuthVerificationUpdate(BaseModel):
    """Internal update - verification status."""
    is_verified: Optional[bool] = None
    updated_at: Optional[datetime] = None

class UserAuthSecurityUpdate(BaseModel):
    """Internal update - login and auth metadata (system use only)."""
    last_login_at: Optional[datetime] = None
    failed_login_attempts: Optional[int] = None
    lockout_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None

# =====================================================================
# 4. READ SCHEMAS
# =====================================================================

# --- Hidden/Internal ---

class UserAuthInternal(UserAuthBase, UserAuthPasswordHash, UserAuthVerificationUpdate, UserAuthSecurity):
    """Backend use only - includes sensitive data."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role: UserRole
    status: Status

# --- Base/Summary ---

class UserAuthOut(UserAuthBase):
    """Minimal public view for lists."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    role: UserRole
    status: Status

# --- Detailed/Expanded ---

class UserAuthOutDetailed(UserAuthOut, UserAuthSecurity):
    """Full details including security metadata."""
    model_config = ConfigDict(from_attributes=True)

# --- Admin View ---

class UserAuthAdmin(UserAuthOutDetailed):
    """Privileged data - admin access only."""
    model_config = ConfigDict(from_attributes=True)

# =====================================================================
# 5. QUERY / FILTER / PARAMS SCHEMAS
# =====================================================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    limit: int = Field(default=50, ge=1, le=100, description="Number of items per page")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


class PagePaginationParams(BaseModel):
    """Page-based pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=50, ge=1, le=100, description="Items per page")


class UserAuthSortBy(str, enum.Enum):
    """Available sort fields for UserAuth queries."""
    created_at = "created_at"
    updated_at = "updated_at"
    email = "email"
    username = "username"
    last_login_at = "last_login_at"


class SortParams(BaseModel):
    """Sorting parameters."""
    sort_by: UserAuthSortBy = UserAuthSortBy.created_at
    sort_order: Literal["asc", "desc"] = "desc"


class UserAuthFilterParams(BaseModel):
    """Filter parameters for UserAuth queries."""
    role: Optional[UserRole] = None
    status: Optional[Status] = None
    is_verified: Optional[bool] = None
    search: Optional[str] = Field(None, description="Search in username, email, or phone")
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_login_after: Optional[datetime] = None
    last_login_before: Optional[datetime] = None


class UserAuthQueryParams(PaginationParams, SortParams, UserAuthFilterParams):
    """Combined query parameters for listing users."""
    pass


# =====================================================================
# 6. AUTH SCHEMAS
# =====================================================================

class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str = Field(..., min_length=1)

class TokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    user: UserAuthOut

class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str

class AdminPasswordUpdate(BaseModel):
    """Password update request."""
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

# =====================================================================
# RESPONSE WRAPPERS
# =====================================================================

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str