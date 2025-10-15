# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings, get_db
from app.crud.user_auth import crud_user_auth
from app.models.user_auth import UserAuth, UserRole, Status


# =====================================================================
# JWT TOKEN CONFIGURATION
# =====================================================================

security = HTTPBearer()


# =====================================================================
# TOKEN CREATION
# =====================================================================

def create_access_token(data: dict) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Dictionary containing user data (typically {"sub": user_id})
        
    Returns:
        Encoded JWT access token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token.
    
    Args:
        data: Dictionary containing user data (typically {"sub": user_id})
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.REFRESH_SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


# =====================================================================
# TOKEN VERIFICATION
# =====================================================================

def verify_token(token: str, secret_key: str, token_type: str = "access") -> str:
    """
    Verify JWT token and return user_id.
    
    Args:
        token: JWT token string
        secret_key: Secret key for decoding
        token_type: Type of token ("access" or "refresh")
        
    Returns:
        User ID from token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_type_payload: str = payload.get("type")
        
        if user_id is None:
            raise credentials_exception
            
        if token_type_payload != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user_id
        
    except JWTError:
        raise credentials_exception


def verify_access_token(token: str) -> str:
    """
    Verify access token.
    
    Args:
        token: JWT access token
        
    Returns:
        User ID from token
    """
    return verify_token(token, settings.SECRET_KEY, "access")


def verify_refresh_token(token: str) -> str:
    """
    Verify refresh token.
    
    Args:
        token: JWT refresh token
        
    Returns:
        User ID from token
    """
    return verify_token(token, settings.REFRESH_SECRET_KEY, "refresh")


# =====================================================================
# USER AUTHENTICATION DEPENDENCIES
# =====================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserAuth:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials containing JWT token
        db: Database session
        
    Returns:
        Current authenticated UserAuth instance
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    user_id = verify_access_token(token)
    
    # Get user from database
    user = crud_user_auth.get(db, id=UUID(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is active
    if user.status != Status.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}",
        )
    
    return user


async def get_current_active_user(
    current_user: UserAuth = Depends(get_current_user)
) -> UserAuth:
    """
    Get current active user (account must be active and verified).
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active UserAuth instance
        
    Raises:
        HTTPException: If account is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not verified",
        )
    return current_user


async def get_current_admin_user(
    current_user: UserAuth = Depends(get_current_user)
) -> UserAuth:
    """
    Get current user with admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current admin UserAuth instance
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def get_current_professional_user(
    current_user: UserAuth = Depends(get_current_user)
) -> UserAuth:
    """
    Get current user with professional or admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current professional/admin UserAuth instance
        
    Raises:
        HTTPException: If user is not professional or admin
    """
    if current_user.role not in [UserRole.professional, UserRole.admin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Professional or admin privileges required",
        )
    return current_user


# =====================================================================
# ROLE CHECKING UTILITIES
# =====================================================================

def require_role(required_role: UserRole):
    """
    Dependency factory for checking user role.
    
    Args:
        required_role: Required user role
        
    Returns:
        Dependency function that checks role
        
    Example:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.admin))])
    """
    async def role_checker(current_user: UserAuth = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' required",
            )
        return current_user
    return role_checker


def require_any_role(*roles: UserRole):
    """
    Dependency factory for checking if user has any of the specified roles.
    
    Args:
        roles: Tuple of allowed user roles
        
    Returns:
        Dependency function that checks roles
        
    Example:
        @router.get("/staff-only", dependencies=[Depends(require_any_role(UserRole.professional, UserRole.admin))])
    """
    async def role_checker(current_user: UserAuth = Depends(get_current_user)):
        if current_user.role not in roles:
            role_names = ", ".join([r.value for r in roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {role_names}",
            )
        return current_user
    return role_checker


# =====================================================================
# OPTIONAL AUTHENTICATION
# =====================================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[UserAuth]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for endpoints that work both with and without authentication.
    
    Args:
        credentials: Optional HTTP Bearer credentials
        db: Database session
        
    Returns:
        UserAuth instance if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user_id = verify_access_token(token)
        user = crud_user_auth.get(db, id=UUID(user_id))
        
        if user and user.status == Status.active:
            return user
    except:
        pass
    
    return None