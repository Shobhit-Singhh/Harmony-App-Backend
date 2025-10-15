# crud/user_auth.py
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from passlib.context import CryptContext

from app.models.user_auth import UserAuth, UserRole, Status
from app.schemas.user_auth import (
    UserAuthCreate,
    UserAuthUpdate,
    UserAuthUpdatePassword,
    UserAuthRoleUpdate,
    UserAuthStatusUpdate,
    UserAuthVerificationUpdate,
    UserAuthSecurityUpdate,
    
    UserAuthQueryParams,
    PaginationParams,
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserAuthCRUD:
    """CRUD operations for UserAuth model."""

    # =====================================================================
    # HELPER METHODS
    # =====================================================================

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def is_account_locked(user: UserAuth) -> bool:
        """Check if account is locked."""
        if user.lockout_until and user.lockout_until > datetime.now(timezone.utc):
            return True
        return False

    @staticmethod
    def reset_failed_attempts(db: Session, user: UserAuth) -> None:
        """Reset failed login attempts."""
        user.failed_login_attempts = 0
        user.lockout_until = None
        db.commit()

    @staticmethod
    def increment_failed_attempts(
        db: Session, user: UserAuth, max_attempts: int = 5
    ) -> None:
        """Increment failed login attempts and lock account if needed."""
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= max_attempts:
            # Lock account for 30 minutes
            user.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=30)

        db.commit()

    # =====================================================================
    # CREATE OPERATIONS
    # =====================================================================

    def create(self, db: Session, *, obj_in: UserAuthCreate) -> UserAuth:
        """
        Create a new user.

        Args:
            db: Database session
            obj_in: UserAuthCreate schema with user data

        Returns:
            Created UserAuth instance
        """
        # Hash the password
        hashed_password = self.hash_password(obj_in.password_hash)

        # Create user instance
        db_obj = UserAuth(
            username=obj_in.username,
            email=obj_in.email,
            phone_number=obj_in.phone_number,
            password_hash=hashed_password,
            role=obj_in.role,
            status=obj_in.status
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # =====================================================================
    # UPDATE OPERATIONS
    # =====================================================================

    def update(
        self, db: Session, *, db_obj: UserAuth, obj_in: UserAuthUpdate
    ) -> UserAuth:
        """
        Update user basic information.

        Args:
            db: Database session
            db_obj: Existing UserAuth instance
            obj_in: UserAuthUpdate schema with updated data

        Returns:
            Updated UserAuth instance
        """
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(db_obj, field, value)

        db_obj.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_password(
        self, db: Session, *, db_obj: UserAuth, obj_in: UserAuthUpdatePassword
    ) -> UserAuth:
        """
        Update user password (requires old password verification).

        Args:
            db: Database session
            db_obj: Existing UserAuth instance
            obj_in: UserAuthUpdatePassword schema

        Returns:
            Updated UserAuth instance

        Raises:
            ValueError: If old password is incorrect
        """
        # Verify old password
        if not self.verify_password(obj_in.old_password, db_obj.password_hash):
            raise ValueError("Incorrect password")

        # Hash and set new password
        db_obj.password_hash = self.hash_password(obj_in.new_password)
        db_obj.password_changed_at = datetime.now(timezone.utc)
        db_obj.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def admin_update_password(
        self, db: Session, *, db_obj: UserAuth, new_password: str
    ) -> UserAuth:
        """
        Admin-level password update (no old password required).

        Args:
            db: Database session
            db_obj: Existing UserAuth instance
            new_password: New password

        Returns:
            Updated UserAuth instance
        """
        db_obj.password_hash = self.hash_password(new_password)
        db_obj.password_changed_at = datetime.now(timezone.utc)
        db_obj.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_role(
        self, db: Session, *, db_obj: UserAuth, obj_in: UserAuthRoleUpdate
    ) -> UserAuth:
        """
        Update user role (admin only).

        Args:
            db: Database session
            db_obj: Existing UserAuth instance
            obj_in: UserAuthRoleUpdate schema

        Returns:
            Updated UserAuth instance
        """
        db_obj.role = obj_in.role
        db_obj.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_status(
        self, db: Session, *, db_obj: UserAuth, obj_in: UserAuthStatusUpdate
    ) -> UserAuth:
        """
        Update user status (admin only).

        Args:
            db: Database session
            db_obj: Existing UserAuth instance
            obj_in: UserAuthStatusUpdate schema

        Returns:
            Updated UserAuth instance
        """
        db_obj.status = obj_in.status
        db_obj.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_verification(
        self, db: Session, *, db_obj: UserAuth, obj_in: UserAuthVerificationUpdate
    ) -> UserAuth:
        """
        Update verification status (internal).

        Args:
            db: Database session
            db_obj: Existing UserAuth instance
            obj_in: UserAuthVerificationUpdate schema

        Returns:
            Updated UserAuth instance
        """
        if obj_in.is_verified is not None:
            db_obj.is_verified = obj_in.is_verified

        db_obj.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_security_fields(
        self, db: Session, *, db_obj: UserAuth, obj_in: UserAuthSecurityUpdate
    ) -> UserAuth:
        """
        Update security fields (internal).

        Args:
            db: Database session
            db_obj: Existing UserAuth instance
            obj_in: UserAuthSecurityFieldsUpdate schema

        Returns:
            Updated UserAuth instance
        """
        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    # =====================================================================
    # READ OPERATIONS
    # =====================================================================

    def get(self, db: Session, id: UUID) -> Optional[UserAuth]:
        """
        Get user by ID.

        Args:
            db: Database session
            id: User UUID

        Returns:
            UserAuth instance or None
        """
        return db.query(UserAuth).filter(UserAuth.id == id).first()

    def get_by_email(self, db: Session, email: str) -> Optional[UserAuth]:
        """
        Get user by email.

        Args:
            db: Database session
            email: User email

        Returns:
            UserAuth instance or None
        """
        return db.query(UserAuth).filter(UserAuth.email == email).first()

    def get_by_phone(self, db: Session, phone_number: str) -> Optional[UserAuth]:
        """
        Get user by phone number.

        Args:
            db: Database session
            phone_number: User phone number

        Returns:
            UserAuth instance or None
        """
        return db.query(UserAuth).filter(UserAuth.phone_number == phone_number).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[UserAuth]:
        """
        Get multiple users with pagination.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of UserAuth instances
        """
        return db.query(UserAuth).offset(skip).limit(limit).all()

    def get_multi_filtered(
        self, db: Session, *, params: UserAuthQueryParams
    ) -> tuple[List[UserAuth], int]:
        """
        Get multiple users with filtering, sorting, and pagination.

        Args:
            db: Database session
            params: Query parameters including filters, sort, and pagination

        Returns:
            Tuple of (list of UserAuth instances, total count)
        """
        query = db.query(UserAuth)

        # Apply filters
        if params.role:
            query = query.filter(UserAuth.role == params.role)

        if params.status:
            query = query.filter(UserAuth.status == params.status)

        if params.is_verified is not None:
            query = query.filter(UserAuth.is_verified == params.is_verified)

        if params.search:
            search_filter = or_(
                UserAuth.username.ilike(f"%{params.search}%"),
                UserAuth.email.ilike(f"%{params.search}%"),
                UserAuth.phone_number.ilike(f"%{params.search}%"),
            )
            query = query.filter(search_filter)

        if params.created_after:
            query = query.filter(UserAuth.created_at >= params.created_after)

        if params.created_before:
            query = query.filter(UserAuth.created_at <= params.created_before)

        if params.last_login_after:
            query = query.filter(UserAuth.last_login_at >= params.last_login_after)

        if params.last_login_before:
            query = query.filter(UserAuth.last_login_at <= params.last_login_before)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_column = getattr(UserAuth, params.sort_by.value)
        if params.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        query = query.offset(params.offset).limit(params.limit)

        return query.all(), total

    def count(self, db: Session) -> int:
        """
        Get total count of users.

        Args:
            db: Database session

        Returns:
            Total number of users
        """
        return db.query(UserAuth).count()

    def count_by_role(self, db: Session, role: UserRole) -> int:
        """
        Count users by role.

        Args:
            db: Database session
            role: User role

        Returns:
            Count of users with specified role
        """
        return db.query(UserAuth).filter(UserAuth.role == role).count()

    def count_by_status(self, db: Session, status: Status) -> int:
        """
        Count users by status.

        Args:
            db: Database session
            status: User status

        Returns:
            Count of users with specified status
        """
        return db.query(UserAuth).filter(UserAuth.status == status).count()

    # =====================================================================
    # DELETE OPERATIONS
    # =====================================================================

    def delete(self, db: Session, *, id: UUID) -> Optional[UserAuth]:
        """
        Delete user by ID (hard delete).

        Args:
            db: Database session
            id: User UUID

        Returns:
            Deleted UserAuth instance or None
        """
        obj = db.query(UserAuth).filter(UserAuth.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def soft_delete(self, db: Session, *, id: UUID) -> Optional[UserAuth]:
        """
        Soft delete user by setting status to deactivated.

        Args:
            db: Database session
            id: User UUID

        Returns:
            Updated UserAuth instance or None
        """
        obj = db.query(UserAuth).filter(UserAuth.id == id).first()
        if obj:
            obj.status = Status.deactivated
            obj.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(obj)
        return obj

# Create singleton instance
crud_user_auth = UserAuthCRUD()
