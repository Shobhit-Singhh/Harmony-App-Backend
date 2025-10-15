# services/user_auth.py
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user_auth import UserAuth, UserRole, Status
from app.schemas.user_auth import (
    UserAuthCreate,
    UserAuthUpdate,
    UserAuthUpdatePassword,
    UserAuthRoleUpdate,
    UserAuthStatusUpdate,
    UserAuthVerificationUpdate,
    UserAuthSecurityUpdate,
    UserAuthOut,
    UserAuthOutDetailed,
    UserAuthAdmin,
    UserAuthQueryParams,
    LoginRequest,
    TokenResponse,
    AdminPasswordUpdate,
)
from app.crud.user_auth import crud_user_auth


# =====================================================================
# EXCEPTIONS
# =====================================================================


class AuthenticationError(HTTPException):
    """Authentication failed exception."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class AccountLockedError(HTTPException):
    """Account locked exception."""

    def __init__(self, detail: str = "Account is locked"):
        super().__init__(status_code=status.HTTP_423_LOCKED, detail=detail)


class AccountInactiveError(HTTPException):
    """Account inactive exception."""

    def __init__(self, detail: str = "Account is not active"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ResourceNotFoundError(HTTPException):
    """Resource not found exception."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    """Resource conflict exception."""

    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class PermissionDeniedError(HTTPException):
    """Permission denied exception."""

    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# =====================================================================
# SERVICE CLASS
# =====================================================================


class UserAuthService:
    """Service layer for user authentication and management."""

    def __init__(self):
        self.crud = crud_user_auth

    # =====================================================================
    # USER REGISTRATION & CREATION
    # =====================================================================

    def create_user(
        self,
        db: Session,
        user_data: UserAuthCreate,
        created_by: Optional[UserAuth] = None,
    ) -> UserAuth:
        """
        Create a new user account.

        Args:
            db: Database session
            user_data: User creation data
            created_by: User creating the account (for admin operations)

        Returns:
            Created UserAuth instance

        Raises:
            ConflictError: If email or phone already exists
            PermissionDeniedError: If non-admin tries to create admin/professional
        """
        # Check if email already exists
        if self.crud.get_by_email(db, email=user_data.email):
            raise ConflictError(detail="Email already registered")

        # Check if phone already exists
        if user_data.phone_number:
            if self.crud.get_by_phone(db, phone_number=user_data.phone_number):
                raise ConflictError(detail="Phone number already registered")

        # Permission check: only admins can create admin/professional accounts
        if created_by and created_by.role != UserRole.admin:
            if user_data.role in [UserRole.admin, UserRole.professional]:
                raise PermissionDeniedError(
                    detail="Only admins can create admin or professional accounts"
                )

        # Create user
        user = self.crud.create(db, obj_in=user_data)
        return user

    def register_user(
        self,
        db: Session,
        email: str,
        password: str,
        username: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> UserAuth:
        """
        Public user registration (creates regular user account).

        Args:
            db: Database session
            email: User email
            password: User password
            username: Optional username
            phone_number: Optional phone number

        Returns:
            Created UserAuth instance

        Raises:
            ConflictError: If email or phone already exists
        """
        user_data = UserAuthCreate(
            email=email,
            password_hash=password,  # Will be hashed in CRUD
            username=username,
            phone_number=phone_number,
            role=UserRole.user,
            status=Status.active,
            is_verified=False,
        )

        return self.create_user(db, user_data)

    # =====================================================================
    # AUTHENTICATION & LOGIN
    # =====================================================================

    def authenticate_user(self, db: Session, login_data: LoginRequest) -> UserAuth:
        """
        Authenticate user with email and password.

        Args:
            db: Database session
            login_data: Login credentials

        Returns:
            Authenticated UserAuth instance

        Raises:
            AuthenticationError: If credentials are invalid
            AccountLockedError: If account is locked
            AccountInactiveError: If account is not active
        """
        # Get user by email
        user = self.crud.get_by_email(db, email=login_data.email)
        if not user:
            raise AuthenticationError(detail="Invalid email or password")

        # Check if account is locked
        if self.crud.is_account_locked(user):
            raise AccountLockedError(
                detail=f"Account is locked until {user.lockout_until}"
            )

        # Check account status
        if user.status != Status.active:
            raise AccountInactiveError(detail=f"Account is {user.status.value}")

        # Verify password
        if not self.crud.verify_password(login_data.password, user.password_hash):
            # Increment failed attempts
            self.crud.increment_failed_attempts(db, user)
            raise AuthenticationError(detail="Invalid email or password")

        # Reset failed attempts on successful login
        self.crud.reset_failed_attempts(db, user)

        # Update last login time
        security_update = UserAuthSecurityUpdate(
            last_login_at=datetime.now(timezone.utc)
        )
        user = self.crud.update_security_fields(db, db_obj=user, obj_in=security_update)

        return user

    # =====================================================================
    # USER RETRIEVAL
    # =====================================================================

    def get_user_by_id(
        self, db: Session, user_id: UUID, requesting_user: Optional[UserAuth] = None
    ) -> UserAuth:
        """
        Get user by ID with permission checking.

        Args:
            db: Database session
            user_id: User UUID
            requesting_user: User making the request

        Returns:
            UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If access denied
        """
        user = self.crud.get(db, id=user_id)
        if not user:
            raise ResourceNotFoundError(detail="User not found")

        # Permission check: users can only access their own data unless admin
        if requesting_user:
            if requesting_user.id != user_id and requesting_user.role != UserRole.admin:
                raise PermissionDeniedError(
                    detail="You don't have permission to access this user"
                )

        return user

    def get_user_by_email(
        self, db: Session, email: str, requesting_user: Optional[UserAuth] = None
    ) -> UserAuth:
        """
        Get user by email with permission checking.

        Args:
            db: Database session
            email: User email
            requesting_user: User making the request

        Returns:
            UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If access denied (non-admin)
        """
        # Only admins can search by email
        if requesting_user and requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(detail="Only admins can search users by email")

        user = self.crud.get_by_email(db, email=email)
        if not user:
            raise ResourceNotFoundError(detail="User not found")

        return user

    def get_users(
        self, db: Session, params: UserAuthQueryParams, requesting_user: UserAuth
    ) -> Tuple[List[UserAuth], int]:
        """
        Get list of users with filtering and pagination.

        Args:
            db: Database session
            params: Query parameters
            requesting_user: User making the request

        Returns:
            Tuple of (list of users, total count)

        Raises:
            PermissionDeniedError: If non-admin tries to list users
        """
        # Only admins can list users
        if requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(detail="Only admins can list users")

        users, total = self.crud.get_multi_filtered(db, params=params)
        return users, total

    # =====================================================================
    # USER UPDATES
    # =====================================================================

    def update_user(
        self,
        db: Session,
        user_id: UUID,
        update_data: UserAuthUpdate,
        requesting_user: UserAuth,
    ) -> UserAuth:
        """
        Update user basic information.

        Args:
            db: Database session
            user_id: User UUID to update
            update_data: Update data
            requesting_user: User making the request

        Returns:
            Updated UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If access denied
            ConflictError: If email/phone already exists
        """
        # Get user
        user = self.crud.get(db, id=user_id)
        if not user:
            raise ResourceNotFoundError(detail="User not found")

        # Permission check: users can only update their own data unless admin
        if requesting_user.id != user_id and requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(
                detail="You don't have permission to update this user"
            )

        # Check email uniqueness
        if update_data.email and update_data.email != user.email:
            existing_user = self.crud.get_by_email(db, email=update_data.email)
            if existing_user:
                raise ConflictError(detail="Email already registered")

        # Check phone uniqueness
        if update_data.phone_number and update_data.phone_number != user.phone_number:
            existing_user = self.crud.get_by_phone(
                db, phone_number=update_data.phone_number
            )
            if existing_user:
                raise ConflictError(detail="Phone number already registered")

        return self.crud.update(db, db_obj=user, obj_in=update_data)

    def update_password(
        self,
        db: Session,
        user_id: UUID,
        password_data: UserAuthUpdatePassword,
        requesting_user: UserAuth,
    ) -> UserAuth:
        """
        Update user password (requires old password).

        Args:
            db: Database session
            user_id: User UUID
            password_data: Password update data
            requesting_user: User making the request

        Returns:
            Updated UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If access denied
            AuthenticationError: If old password is incorrect
        """
        # Get user
        user = self.crud.get(db, id=user_id)
        if not user:
            raise ResourceNotFoundError(detail="User not found")

        # Permission check: users can only update their own password
        if requesting_user.id != user_id:
            raise PermissionDeniedError(detail="You can only update your own password")

        try:
            return self.crud.update_password(db, db_obj=user, obj_in=password_data)
        except ValueError as e:
            raise AuthenticationError(detail=str(e))

    def admin_update_password(
        self,
        db: Session,
        user_id: UUID,
        password_data: AdminPasswordUpdate,
        requesting_user: UserAuth,
    ) -> UserAuth:
        """
        Admin password update (no old password required).

        Args:
            db: Database session
            user_id: User UUID
            password_data: New password data
            requesting_user: User making the request

        Returns:
            Updated UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If non-admin
        """
        # Only admins can do password resets
        if requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(detail="Only admins can reset user passwords")

        user = self.crud.get(db, id=user_id)
        if not user:
            raise ResourceNotFoundError(detail="User not found")

        return self.crud.admin_update_password(
            db, db_obj=user, new_password=password_data.new_password
        )

    def update_role(
        self,
        db: Session,
        user_id: UUID,
        role_data: UserAuthRoleUpdate,
        requesting_user: UserAuth,
    ) -> UserAuth:
        """
        Update user role (admin only).

        Args:
            db: Database session
            user_id: User UUID
            role_data: Role update data
            requesting_user: User making the request

        Returns:
            Updated UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If non-admin
        """
        # Only admins can update roles
        if requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(detail="Only admins can update user roles")

        user = self.crud.get(db, id=user_id)
        if not user:
            raise ResourceNotFoundError(detail="User not found")

        return self.crud.update_role(db, db_obj=user, obj_in=role_data)

    def update_status(
        self,
        db: Session,
        user_id: UUID,
        status_data: UserAuthStatusUpdate,
        requesting_user: UserAuth,
    ) -> UserAuth:
        """
        Update user status (admin only).

        Args:
            db: Database session
            user_id: User UUID
            status_data: Status update data
            requesting_user: User making the request

        Returns:
            Updated UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If non-admin
        """
        # Only admins can update status
        if requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(detail="Only admins can update user status")

        user = self.crud.get(db, id=user_id)
        if not user:
            raise ResourceNotFoundError(detail="User not found")

        return self.crud.update_status(db, db_obj=user, obj_in=status_data)

    # =====================================================================
    # USER DELETION
    # =====================================================================

    def delete_user(
        self,
        db: Session,
        user_id: UUID,
        requesting_user: UserAuth,
        hard_delete: bool = False,
    ) -> UserAuth:
        """
        Delete user account (soft or hard delete).

        Args:
            db: Database session
            user_id: User UUID
            requesting_user: User making the request
            hard_delete: If True, permanently delete; otherwise soft delete

        Returns:
            Deleted/deactivated UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If access denied
        """
        # Get user
        user = self.crud.get(db, id=user_id)
        if not user:
            raise ResourceNotFoundError(detail="User not found")

        # Permission check: users can delete their own account, admins can delete any
        if requesting_user.id != user_id and requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(
                detail="You don't have permission to delete this user"
            )

        # Prevent deleting the last admin
        if user.role == UserRole.admin:
            admin_count = self.crud.count_by_role(db, role=UserRole.admin)
            if admin_count <= 1:
                raise PermissionDeniedError(
                    detail="Cannot delete the last admin account"
                )

        if hard_delete and requesting_user.role == UserRole.admin:
            return self.crud.delete(db, id=user_id)
        else:
            return self.crud.soft_delete(db, id=user_id)

    # =====================================================================
    # ACCOUNT MANAGEMENT
    # =====================================================================

    def suspend_account(
        self, db: Session, user_id: UUID, requesting_user: UserAuth
    ) -> UserAuth:
        """
        Suspend user account (admin only).

        Args:
            db: Database session
            user_id: User UUID
            requesting_user: User making the request

        Returns:
            Updated UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If non-admin
        """
        status_data = UserAuthStatusUpdate(status=Status.suspended)
        return self.update_status(db, user_id, status_data, requesting_user)

    def activate_account(
        self, db: Session, user_id: UUID, requesting_user: UserAuth
    ) -> UserAuth:
        """
        Activate user account (admin only).

        Args:
            db: Database session
            user_id: User UUID
            requesting_user: User making the request

        Returns:
            Updated UserAuth instance

        Raises:
            ResourceNotFoundError: If user not found
            PermissionDeniedError: If non-admin
        """
        status_data = UserAuthStatusUpdate(status=Status.active)
        return self.update_status(db, user_id, status_data, requesting_user)

    # =====================================================================
    # STATISTICS & ANALYTICS
    # =====================================================================

    def get_user_statistics(
        self, db: Session, requesting_user: UserAuth
    ) -> Dict[str, Any]:
        """
        Get user statistics (admin only).

        Args:
            db: Database session
            requesting_user: User making the request

        Returns:
            Dictionary with user statistics

        Raises:
            PermissionDeniedError: If non-admin
        """
        # Only admins can view statistics
        if requesting_user.role != UserRole.admin:
            raise PermissionDeniedError(detail="Only admins can view user statistics")

        return {
            "total_users": self.crud.count(db),
            "users_by_role": {
                "user": self.crud.count_by_role(db, UserRole.user),
                "professional": self.crud.count_by_role(db, UserRole.professional),
                "admin": self.crud.count_by_role(db, UserRole.admin),
            },
            "users_by_status": {
                "active": self.crud.count_by_status(db, Status.active),
                "suspended": self.crud.count_by_status(db, Status.suspended),
                "deactivated": self.crud.count_by_status(db, Status.deactivated),
            },
        }


# =====================================================================
# SINGLETON INSTANCE
# =====================================================================

user_auth_service = UserAuthService()
