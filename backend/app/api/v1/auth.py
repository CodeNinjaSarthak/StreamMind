"""Authentication API routes."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    hash_password,
    verify_password,
    verify_token,
)
from backend.app.db.models.teacher import Teacher
from backend.app.db.session import get_db
from backend.app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TeacherResponse,
    Token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> Teacher:
    """Register a new teacher.

    Args:
        request: Registration request.
        db: Database session.

    Returns:
        Created teacher.

    Raises:
        HTTPException: If email already exists.
    """
    existing_teacher = db.query(Teacher).filter(Teacher.email == request.email).first()
    if existing_teacher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    teacher = Teacher(
        email=request.email,
        name=request.name,
        hashed_password=hash_password(request.password),
        is_active=True,
        is_verified=False
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    return teacher


@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Login endpoint.

    Args:
        credentials: Login credentials.
        db: Database session.

    Returns:
        Token response.

    Raises:
        HTTPException: If credentials are invalid.
    """
    teacher = db.query(Teacher).filter(Teacher.email == credentials.email).first()

    if not teacher or not verify_password(credentials.password, teacher.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not teacher.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    access_token = create_access_token(data={"sub": str(teacher.id)})
    refresh_token = create_refresh_token(data={"sub": str(teacher.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }


@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Refresh token endpoint.

    Args:
        request: Refresh token request.
        db: Database session.

    Returns:
        New token response.

    Raises:
        HTTPException: If refresh token is invalid.
    """
    payload = verify_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    teacher_id = payload.get("sub")
    if not teacher_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    from uuid import UUID
    teacher = db.query(Teacher).filter(Teacher.id == UUID(teacher_id)).first()
    if not teacher or not teacher.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    access_token = create_access_token(data={"sub": str(teacher.id)})
    refresh_token = create_refresh_token(data={"sub": str(teacher.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60
    }


@router.get("/me", response_model=TeacherResponse)
async def get_current_teacher(
    current_user: Teacher = Depends(get_current_active_user)
) -> Teacher:
    """Get current authenticated teacher.

    Args:
        current_user: Current authenticated user.

    Returns:
        Teacher information.
    """
    return current_user


@router.post("/logout")
async def logout() -> dict:
    """Logout endpoint.

    Returns:
        Status response.
    """
    return {"status": "ok", "message": "Logged out successfully"}

