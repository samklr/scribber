"""
Admin User Management Router.
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, Project, UsageLog
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Admin Check Dependency ---


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# --- Request/Response Models ---


class UserResponse(BaseModel):
    """Response with user details."""
    id: int
    email: str
    name: Optional[str]
    is_admin: bool
    is_active: bool
    created_at: str
    project_count: int = 0
    total_usage_seconds: float = 0


class UserUpdate(BaseModel):
    """Request to update a user."""
    name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class UserListResponse(BaseModel):
    """Response with paginated user list."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


class UserStats(BaseModel):
    """User statistics."""
    total_users: int
    active_users: int
    admin_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int


# --- Endpoints ---


@router.get("/stats", response_model=UserStats)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get user statistics (admin only).
    """
    from datetime import timedelta

    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Total users
    total_result = await db.execute(select(func.count(User.id)))
    total_users = total_result.scalar() or 0

    # Active users
    active_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_result.scalar() or 0

    # Admin users
    admin_result = await db.execute(
        select(func.count(User.id)).where(User.is_admin == True)
    )
    admin_users = admin_result.scalar() or 0

    # New users today
    today_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= today)
    )
    new_users_today = today_result.scalar() or 0

    # New users this week
    week_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )
    new_users_this_week = week_result.scalar() or 0

    # New users this month
    month_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= month_ago)
    )
    new_users_this_month = month_result.scalar() or 0

    return UserStats(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        new_users_today=new_users_today,
        new_users_this_week=new_users_this_week,
        new_users_this_month=new_users_this_month,
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_admin: Optional[bool] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    List all users with pagination (admin only).
    """
    # Build query
    query = select(User)

    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))
        )

    if is_admin is not None:
        query = query.where(User.is_admin == is_admin)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    users = result.scalars().all()

    # Get project counts and usage for each user
    user_responses = []
    for user in users:
        # Project count
        project_count_result = await db.execute(
            select(func.count(Project.id)).where(Project.user_id == user.id)
        )
        project_count = project_count_result.scalar() or 0

        # Total usage seconds
        usage_result = await db.execute(
            select(func.sum(UsageLog.duration_seconds)).where(UsageLog.user_id == user.id)
        )
        total_usage = usage_result.scalar() or 0

        user_responses.append(
            UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                is_admin=user.is_admin,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                project_count=project_count,
                total_usage_seconds=float(total_usage),
            )
        )

    return UserListResponse(
        users=user_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get a user by ID (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Project count
    project_count_result = await db.execute(
        select(func.count(Project.id)).where(Project.user_id == user.id)
    )
    project_count = project_count_result.scalar() or 0

    # Total usage seconds
    usage_result = await db.execute(
        select(func.sum(UsageLog.duration_seconds)).where(UsageLog.user_id == user.id)
    )
    total_usage = usage_result.scalar() or 0

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        project_count=project_count,
        total_usage_seconds=float(total_usage),
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Update a user (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent admin from removing their own admin status
    if user.id == admin.id and request.is_admin is False:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove your own admin privileges"
        )

    # Update fields
    if request.name is not None:
        user.name = request.name
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    if request.is_active is not None:
        user.is_active = request.is_active

    await db.commit()
    await db.refresh(user)

    logger.info(f"Admin {admin.email} updated user: {user.email}")

    # Get stats
    project_count_result = await db.execute(
        select(func.count(Project.id)).where(Project.user_id == user.id)
    )
    project_count = project_count_result.scalar() or 0

    usage_result = await db.execute(
        select(func.sum(UsageLog.duration_seconds)).where(UsageLog.user_id == user.id)
    )
    total_usage = usage_result.scalar() or 0

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        project_count=project_count,
        total_usage_seconds=float(total_usage),
    )


@router.post("/{user_id}/toggle-admin")
async def toggle_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Toggle a user's admin status (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot modify your own admin status"
        )

    user.is_admin = not user.is_admin
    await db.commit()

    status = "granted" if user.is_admin else "revoked"
    logger.info(f"Admin {admin.email} {status} admin for user: {user.email}")

    return {"message": f"Admin privileges {status}", "is_admin": user.is_admin}


@router.post("/{user_id}/toggle-active")
async def toggle_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Toggle a user's active status (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate your own account"
        )

    user.is_active = not user.is_active
    await db.commit()

    status = "activated" if user.is_active else "deactivated"
    logger.info(f"Admin {admin.email} {status} user: {user.email}")

    return {"message": f"User {status}", "is_active": user.is_active}
