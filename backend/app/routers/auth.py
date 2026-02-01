"""
Authentication endpoints - Self-hosted auth with JWT tokens.

Provides user registration, login, and session management with JWT tokens.
Passwords are hashed using bcrypt for security. Uses database storage.
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User as UserModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


# =============================================================================
# Pydantic Models
# =============================================================================


class UserCreate(BaseModel):
    """User registration request model."""

    email: EmailStr = Field(
        ...,
        description="User email address (must be valid)",
        examples=["john.doe@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User password (minimum 8 characters)",
        examples=["SecurePassword123!"],
    )
    name: str | None = Field(
        None,
        description="Optional display name",
        examples=["John Doe"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john.doe@example.com",
                    "password": "SecurePassword123!",
                    "name": "John Doe",
                }
            ]
        }
    }


class UserLogin(BaseModel):
    """User login request model."""

    email: EmailStr = Field(
        ...,
        description="Registered email address",
        examples=["john.doe@example.com"],
    )
    password: str = Field(
        ...,
        description="User password",
        examples=["SecurePassword123!"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john.doe@example.com",
                    "password": "SecurePassword123!",
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """User response model (excludes password)."""

    id: int = Field(..., description="Unique user identifier", examples=[1])
    email: str = Field(..., description="User email address", examples=["john.doe@example.com"])
    name: str | None = Field(None, description="User display name", examples=["John Doe"])
    is_admin: bool = Field(default=False, description="Whether user has admin privileges")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "email": "john.doe@example.com",
                    "name": "John Doe",
                    "is_admin": False,
                    "created_at": "2024-01-30T12:00:00",
                }
            ]
        }
    }


class AuthResponse(BaseModel):
    """Authentication response with JWT token and user data."""

    access_token: str = Field(
        ...,
        description="JWT access token for authentication",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
    )
    user: UserResponse = Field(..., description="Authenticated user information")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "user": {
                        "id": 1,
                        "email": "john.doe@example.com",
                        "name": "John Doe",
                        "is_admin": False,
                        "created_at": "2024-01-30T12:00:00",
                    },
                }
            ]
        }
    }


# =============================================================================
# Database Operations
# =============================================================================


async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    """Get user by email from database."""
    result = await db.execute(
        select(UserModel).where(UserModel.email == email.lower())
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> UserModel | None:
    """Get user by ID from database."""
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user_db(
    db: AsyncSession,
    email: str,
    password: str,
    name: str | None = None
) -> UserModel:
    """Create a new user in the database."""
    # Check if user already exists
    existing = await get_user_by_email(db, email)
    if existing:
        raise ValueError("User already exists")

    hashed_password = pwd_context.hash(password)
    user = UserModel(
        email=email.lower(),
        name=name,
        hashed_password=hashed_password,
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# =============================================================================
# Token utilities
# =============================================================================


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> UserModel | None:
    """Authenticate a user by email and password."""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> UserModel:
    """Get the current authenticated user from the token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise credentials_exception

    return user


async def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> UserModel | None:
    """Get the current user if authenticated, otherwise None."""
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


async def get_current_admin_user(
    current_user: Annotated[UserModel, Depends(get_current_user)]
) -> UserModel:
    """Get the current user and verify they are an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def user_to_response(user: UserModel) -> UserResponse:
    """Convert database user to response model."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Create a new user account with email and password",
    response_description="JWT access token and user information",
    responses={
        201: {"description": "User successfully registered"},
        400: {"description": "User already exists or invalid data"},
    },
)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.

    Creates a new user with the provided email and password. The password is
    automatically hashed using bcrypt before storage. Returns a JWT access token
    that can be used immediately for authentication.

    **Password Requirements:**
    - Minimum 8 characters
    - Should include a mix of letters, numbers, and special characters (recommended)

    **Note:** Email addresses are case-insensitive and stored in lowercase.
    """
    try:
        user = await create_user_db(db, user_data.email, user_data.password, user_data.name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    access_token = create_access_token(data={"sub": user.email})

    return AuthResponse(
        access_token=access_token,
        user=user_to_response(user),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login User",
    description="Authenticate with email and password to receive a JWT token",
    response_description="JWT access token and user information",
    responses={
        200: {"description": "Successfully authenticated"},
        401: {"description": "Incorrect email or password"},
    },
)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate and receive access token.

    Validates the provided email and password, then returns a JWT access token
    that expires in 24 hours. Use this token in the Authorization header for
    protected endpoints:

    ```
    Authorization: Bearer <your_token>
    ```

    **Token Lifetime:** 24 hours from issue time
    """
    user = await authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})

    return AuthResponse(
        access_token=access_token,
        user=user_to_response(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Retrieve the currently authenticated user's information",
    response_description="Current user information",
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Not authenticated or invalid token"},
    },
)
async def get_me(current_user: Annotated[UserModel, Depends(get_current_user)]):
    """
    Get current authenticated user information.

    Returns the profile information for the currently authenticated user based
    on the JWT token provided in the Authorization header.

    **Authentication Required:** Yes (Bearer token)
    """
    return user_to_response(current_user)


@router.post(
    "/logout",
    summary="Logout User",
    description="Logout the current user (client-side token removal)",
    response_description="Logout confirmation",
    responses={
        200: {"description": "Successfully logged out"},
        401: {"description": "Not authenticated"},
    },
)
async def logout(current_user: Annotated[UserModel, Depends(get_current_user)]):
    """
    Logout the current user.

    **Note:** With JWT tokens, logout is primarily handled client-side by removing
    the token from storage. This endpoint confirms the logout intent.

    **Authentication Required:** Yes (Bearer token)

    **Client-side action required:** Delete the stored JWT token after calling this endpoint.
    """
    return {"message": "Successfully logged out"}
