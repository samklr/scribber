"""
Authentication endpoints - Self-hosted auth with JWT tokens.

Provides user registration, login, and session management with JWT tokens.
Passwords are hashed using bcrypt for security.
"""
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


# =============================================================================
# Models
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
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "email": "john.doe@example.com",
                    "name": "John Doe",
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
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huLmRvZUBleGFtcGxlLmNvbSIsImV4cCI6MTcwNjcyNDAwMH0...",
                    "token_type": "bearer",
                    "user": {
                        "id": 1,
                        "email": "john.doe@example.com",
                        "name": "John Doe",
                        "created_at": "2024-01-30T12:00:00",
                    },
                }
            ]
        }
    }


class User(BaseModel):
    """Internal user model."""

    id: int
    email: str
    name: str | None
    hashed_password: str
    created_at: datetime


# =============================================================================
# In-memory user storage (replace with database in production)
# =============================================================================

_users_db: dict[str, User] = {}
_next_user_id = 1


def get_user_by_email(email: str) -> User | None:
    """Get user by email."""
    return _users_db.get(email.lower())


def create_user(email: str, password: str, name: str | None = None) -> User:
    """Create a new user."""
    global _next_user_id

    if get_user_by_email(email):
        raise ValueError("User already exists")

    hashed_password = pwd_context.hash(password)
    user = User(
        id=_next_user_id,
        email=email.lower(),
        name=name,
        hashed_password=hashed_password,
        created_at=datetime.utcnow(),
    )
    _users_db[email.lower()] = user
    _next_user_id += 1
    return user


# =============================================================================
# Token utilities
# =============================================================================


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(email: str, password: str) -> User | None:
    """Authenticate a user by email and password."""
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
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

    user = get_user_by_email(email)
    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(
    token: Annotated[str | None, Depends(oauth2_scheme)]
) -> User | None:
    """Get the current user if authenticated, otherwise None."""
    if not token:
        return None
    try:
        return await get_current_user(token)
    except HTTPException:
        return None


def user_to_response(user: User) -> UserResponse:
    """Convert internal user to response model."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
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
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": 1,
                            "email": "john.doe@example.com",
                            "name": "John Doe",
                            "created_at": "2024-01-30T12:00:00",
                        },
                    }
                }
            },
        },
        400: {"description": "User already exists or invalid data"},
    },
)
async def register(user_data: UserCreate):
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
        user = create_user(user_data.email, user_data.password, user_data.name)
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
        200: {
            "description": "Successfully authenticated",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": 1,
                            "email": "john.doe@example.com",
                            "name": "John Doe",
                            "created_at": "2024-01-30T12:00:00",
                        },
                    }
                }
            },
        },
        401: {"description": "Incorrect email or password"},
    },
)
async def login(credentials: UserLogin):
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
    user = authenticate_user(credentials.email, credentials.password)
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
        200: {
            "description": "Current user information",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "email": "john.doe@example.com",
                        "name": "John Doe",
                        "created_at": "2024-01-30T12:00:00",
                    }
                }
            },
        },
        401: {"description": "Not authenticated or invalid token"},
    },
)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
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
        200: {
            "description": "Successfully logged out",
            "content": {
                "application/json": {
                    "example": {"message": "Successfully logged out"}
                }
            },
        },
        401: {"description": "Not authenticated"},
    },
)
async def logout(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Logout the current user.

    **Note:** With JWT tokens, logout is primarily handled client-side by removing
    the token from storage. This endpoint confirms the logout intent and can be
    extended to:

    - Add the token to a server-side blacklist
    - Invalidate all user sessions
    - Track last logout timestamp
    - Trigger cleanup operations

    **Authentication Required:** Yes (Bearer token)

    **Client-side action required:** Delete the stored JWT token after calling this endpoint.
    """
    # In a production app, you might want to:
    # - Add the token to a blacklist
    # - Invalidate all user sessions
    # - Update last_logout timestamp
    return {"message": "Successfully logged out"}
