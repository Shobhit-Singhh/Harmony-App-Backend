# app/api/routers/auth.py
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_admin_user,
    verify_refresh_token
)
from app.services.user_auth import user_auth_service
from app.models.user_auth import UserAuth, UserRole, Status
from app.schemas.user_auth import (
    # Auth schemas
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    
    # User schemas
    UserAuthCreate,
    UserAuthOut,
    UserAuthOutDetailed,
    UserAuthAdmin,
    UserAuthUpdate,
    UserAuthUpdatePassword,
    AdminPasswordUpdate,
    UserAuthRoleUpdate,
    UserAuthStatusUpdate,
    
    # Query schemas
    UserAuthQueryParams,
    
    # Response schemas
    SuccessResponse,
)

router = APIRouter(prefix="/auth", tags=["User Authentication"])


# =====================================================================
# PUBLIC ENDPOINTS - No authentication required
# =====================================================================

@router.post(
    "/register",
    response_model=UserAuthOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account"
)
def register(
    email: str,
    password: str,
    username: str = None,
    phone_number: str = None,
    db: Session = Depends(get_db)
):
    """
    Register a new user account (public endpoint).
    
    - **email**: Valid email address (required)
    - **password**: Password with min 8 characters (required)
    - **username**: Optional username
    - **phone_number**: Optional phone number
    
    Returns the created user information (without sensitive data).
    """
    user = user_auth_service.register_user(
        db=db,
        email=email,
        password=password,
        username=username,
        phone_number=phone_number
    )
    return user


@router.post(
    "/register-admin",
    response_model=UserAuthOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register initial admin account (one-time setup)"
)
def register_admin(
    user_data: UserAuthCreate,
    db: Session = Depends(get_db)
):
    """
    Register the first admin account (one-time setup).
    
    - **email**: Valid email address (required)
    - **password_hash**: Password with min 8 characters (required)
    - **role**: Must be 'admin'
    
    This endpoint can only be used if no admin accounts exist.
    """
    user = user_auth_service.create_user(
        db=db,
        user_data=user_data
    )
    return user

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login to get access token"
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and receive access and refresh tokens.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns access token, refresh token, and user information.
    
    **Note**: Account will be locked for 30 minutes after 5 failed attempts.
    """
    # Authenticate user
    user = user_auth_service.authenticate_user(db, login_data)
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserAuthOut.model_validate(user)
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token"
)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Get new access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token and user information.
    """
    # Verify refresh token and get user_id
    user_id = verify_refresh_token(refresh_data.refresh_token)
    
    # Get user
    user = user_auth_service.get_user_by_id(db, user_id=UUID(user_id))
    
    # Check if user is still active
    if user.status != Status.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )
    
    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserAuthOut.model_validate(user)
    )


# =====================================================================
# USER ENDPOINTS - Authentication required
# =====================================================================

@router.get(
    "/me",
    response_model=UserAuthOutDetailed,
    summary="Get current user profile"
)
def get_current_user_profile(
    current_user: UserAuth = Depends(get_current_user)
):
    """
    Get the authenticated user's profile information.
    
    Requires valid access token in Authorization header.
    """
    return current_user


@router.put(
    "/me",
    response_model=UserAuthOut,
    summary="Update current user profile"
)
def update_current_user_profile(
    update_data: UserAuthUpdate,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the authenticated user's profile information.
    
    - **username**: New username (optional)
    - **email**: New email (optional)
    - **phone_number**: New phone number (optional)
    
    All fields are optional - only provided fields will be updated.
    """
    updated_user = user_auth_service.update_user(
        db=db,
        user_id=current_user.id,
        update_data=update_data,
        requesting_user=current_user
    )
    return updated_user


@router.put(
    "/me/password",
    response_model=SuccessResponse,
    summary="Change current user password"
)
def change_password(
    password_data: UserAuthUpdatePassword,
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change the authenticated user's password.
    
    - **old_password**: Current password (required for verification)
    - **new_password**: New password (min 8 chars, must contain uppercase, lowercase, digit)
    
    Requires correct old password for security.
    """
    user_auth_service.update_password(
        db=db,
        user_id=current_user.id,
        password_data=password_data,
        requesting_user=current_user
    )
    return SuccessResponse(message="Password updated successfully")


@router.delete(
    "/me",
    response_model=SuccessResponse,
    summary="Delete current user account"
)
def delete_current_user_account(
    current_user: UserAuth = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) the authenticated user's account.
    
    This is a soft delete - account will be deactivated but not permanently removed.
    """
    user_auth_service.delete_user(
        db=db,
        user_id=current_user.id,
        requesting_user=current_user,
        hard_delete=False
    )
    return SuccessResponse(message="Account deactivated successfully")


# =====================================================================
# ADMIN ENDPOINTS - Admin authentication required
# =====================================================================

@router.post(
    "/users",
    response_model=UserAuthOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user (Admin only)"
)
def create_user(
    user_data: UserAuthCreate,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user account with specified role (Admin only).
    
    - **email**: User's email address
    - **password_hash**: User's password (will be hashed)
    - **role**: User role (user/professional/admin)
    - **status**: Account status (active/suspended/deactivated)
    - **username**: Optional username
    - **phone_number**: Optional phone number
    
    Only admins can create professional and admin accounts.
    """
    user = user_auth_service.create_user(
        db=db,
        user_data=user_data,
        created_by=current_user
    )
    return user


@router.get(
    "/users",
    response_model=List[UserAuthOutDetailed],
    summary="List all users (Admin only)"
)
def list_users(
    params: UserAuthQueryParams = Depends(),
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get list of users with filtering and pagination (Admin only).
    
    **Query Parameters:**
    - **role**: Filter by role (user/professional/admin)
    - **status**: Filter by status (active/suspended/deactivated)
    - **is_verified**: Filter by verification status
    - **search**: Search in username, email, or phone
    - **created_after**: Filter users created after date
    - **created_before**: Filter users created before date
    - **last_login_after**: Filter by last login after date
    - **last_login_before**: Filter by last login before date
    - **sort_by**: Sort field (created_at/updated_at/email/username/last_login_at)
    - **sort_order**: Sort order (asc/desc)
    - **limit**: Items per page (1-100)
    - **offset**: Number of items to skip
    """
    users, total = user_auth_service.get_users(
        db=db,
        params=params,
        requesting_user=current_user
    )
    return users


@router.get(
    "/users/{user_id}",
    response_model=UserAuthAdmin,
    summary="Get user by ID (Admin only)"
)
def get_user(
    user_id: UUID,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed user information by ID (Admin only).
    
    Returns all user fields including security metadata.
    """
    user = user_auth_service.get_user_by_id(
        db=db,
        user_id=user_id,
        requesting_user=current_user
    )
    return user


@router.put(
    "/users/{user_id}",
    response_model=UserAuthOut,
    summary="Update user (Admin only)"
)
def update_user(
    user_id: UUID,
    update_data: UserAuthUpdate,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update user information (Admin only).
    
    - **username**: New username (optional)
    - **email**: New email (optional)
    - **phone_number**: New phone number (optional)
    """
    updated_user = user_auth_service.update_user(
        db=db,
        user_id=user_id,
        update_data=update_data,
        requesting_user=current_user
    )
    return updated_user


@router.put(
    "/users/{user_id}/password",
    response_model=SuccessResponse,
    summary="Reset user password (Admin only)"
)
def reset_user_password(
    user_id: UUID,
    password_data: AdminPasswordUpdate,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Reset user password without requiring old password (Admin only).
    
    - **new_password**: New password (min 8 chars, must contain uppercase, lowercase, digit)
    """
    user_auth_service.admin_update_password(
        db=db,
        user_id=user_id,
        password_data=password_data,
        requesting_user=current_user
    )
    return SuccessResponse(message="Password reset successfully")


@router.put(
    "/users/{user_id}/role",
    response_model=UserAuthOut,
    summary="Update user role (Admin only)"
)
def update_user_role(
    user_id: UUID,
    role_data: UserAuthRoleUpdate,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update user role (Admin only).
    
    - **role**: New role (user/professional/admin)
    """
    updated_user = user_auth_service.update_role(
        db=db,
        user_id=user_id,
        role_data=role_data,
        requesting_user=current_user
    )
    return updated_user


@router.put(
    "/users/{user_id}/status",
    response_model=UserAuthOut,
    summary="Update user status (Admin only)"
)
def update_user_status(
    user_id: UUID,
    status_data: UserAuthStatusUpdate,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update user account status (Admin only).
    
    - **status**: New status (active/suspended/deactivated)
    """
    updated_user = user_auth_service.update_status(
        db=db,
        user_id=user_id,
        status_data=status_data,
        requesting_user=current_user
    )
    return updated_user


@router.post(
    "/users/{user_id}/suspend",
    response_model=UserAuthOut,
    summary="Suspend user account (Admin only)"
)
def suspend_user(
    user_id: UUID,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Suspend user account (Admin only).
    
    Suspended accounts cannot login until reactivated.
    """
    suspended_user = user_auth_service.suspend_account(
        db=db,
        user_id=user_id,
        requesting_user=current_user
    )
    return suspended_user


@router.post(
    "/users/{user_id}/activate",
    response_model=UserAuthOut,
    summary="Activate user account (Admin only)"
)
def activate_user(
    user_id: UUID,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Activate user account (Admin only).
    
    Reactivates suspended or deactivated accounts.
    """
    activated_user = user_auth_service.activate_account(
        db=db,
        user_id=user_id,
        requesting_user=current_user
    )
    return activated_user


@router.delete(
    "/users/{user_id}",
    response_model=SuccessResponse,
    summary="Delete user account (Admin only)"
)
def delete_user(
    user_id: UUID,
    hard_delete: bool = False,
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account (Admin only).
    
    - **hard_delete**: If true, permanently delete user. Otherwise, soft delete (deactivate).
    
    **Note**: Cannot delete the last admin account.
    """
    user_auth_service.delete_user(
        db=db,
        user_id=user_id,
        requesting_user=current_user,
        hard_delete=hard_delete
    )
    
    delete_type = "permanently deleted" if hard_delete else "deactivated"
    return SuccessResponse(message=f"User {delete_type} successfully")


@router.get(
    "/statistics",
    summary="Get user statistics (Admin only)"
)
def get_statistics(
    current_user: UserAuth = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get user statistics and analytics (Admin only).
    
    Returns:
    - Total user count
    - Users by role (user/professional/admin)
    - Users by status (active/suspended/deactivated)
    """
    stats = user_auth_service.get_user_statistics(
        db=db,
        requesting_user=current_user
    )
    return stats