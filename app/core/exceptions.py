import logging
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.requests import Request

logger = logging.getLogger(__name__)

# ---------------------------
# CRUD (Database abstraction)
# ---------------------------

class DatabaseError(Exception):
    """Base class for all database-related errors."""
    pass

class DatabaseConflictError(DatabaseError):
    """Raised when a database constraint is violated (e.g., unique key)."""
    pass

class DatabaseNotFoundError(DatabaseError):
    """Raised when a record is not found in the database."""
    pass

class DatabaseIntegrityError(DatabaseError):
    """Raised when data integrity issues occur (e.g., foreign key violations)."""
    pass

# ---------------------------
# Service (Business logic)
# ---------------------------

class BusinessError(Exception):
    """Base class for all business logic errors."""
    pass

class ServiceError(BusinessError):
    """Generic error for unexpected service failures."""
    pass

class NotFoundError(BusinessError):
    """Raised when a requested resource does not exist."""
    pass

class ConflictError(BusinessError):
    """Raised when a resource already exists or conflicts with another resource."""
    pass

class PermissionError(BusinessError):
    """Raised when a user does not have permission to perform an action."""
    pass

class ValidationError(BusinessError):
    """Raised when business rule validation fails (e.g., invalid input)."""
    pass

class UnauthorizedError(BusinessError):
    """Raised when authentication fails."""
    pass


# ---------------------------
# FastAPI Exception Handlers
# ---------------------------

def register_exception_handlers(app):
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)},
        )

    @app.exception_handler(PermissionError)
    async def permission_handler(request: Request, exc: PermissionError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError):
        logger.error(f"Service error: {exc}", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
