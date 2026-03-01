"""Authentication API routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    hash_password,
    security_scheme,
    verify_password,
    verify_token,
)
from app.services.token_blacklist import token_blacklist
from app.db.models.teacher import Teacher
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TeacherResponse,
    Token,
    UpdateProfileRequest,
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


@router.patch("/profile", response_model=TeacherResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Teacher:
    current_user.name = request.name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    current_user.hashed_password = hash_password(request.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """Logout endpoint. Blacklists the current JWT token.

    Returns:
        Status response.
    """
    token = credentials.credentials
    payload = verify_token(token)
    if payload:
        exp = payload.get("exp")
        if exp:
            expires_in = int(exp - datetime.now(timezone.utc).timestamp())
            token_blacklist.blacklist_token(token, expires_in)  # skips if <= 0
    return {"status": "ok", "message": "Logged out successfully"}

