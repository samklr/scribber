"""
Admin Usage Statistics Router.
"""
import logging
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, Project, UsageLog, ModelConfig
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


# --- Response Models ---


class UsageSummary(BaseModel):
    """Overall usage summary."""
    total_projects: int
    total_transcriptions: int
    total_summaries: int
    total_audio_seconds: float
    total_tokens_used: int
    estimated_total_cost: float
    projects_today: int
    projects_this_week: int
    projects_this_month: int


class DailyUsage(BaseModel):
    """Daily usage data point."""
    date: str
    projects: int
    transcriptions: int
    summaries: int
    audio_seconds: float
    tokens_used: int


class ModelUsage(BaseModel):
    """Usage by model."""
    model_id: int
    model_name: str
    model_type: str
    usage_count: int
    total_audio_seconds: float
    total_tokens: int
    estimated_cost: float


class TopUser(BaseModel):
    """Top user by usage."""
    user_id: int
    email: str
    name: Optional[str]
    project_count: int
    total_audio_seconds: float
    total_tokens: int


class UsageLogEntry(BaseModel):
    """Usage log entry."""
    id: int
    user_email: str
    project_title: str
    model_name: str
    operation: str
    input_size_bytes: int
    duration_seconds: float
    tokens_used: int
    estimated_cost: float
    created_at: str


# --- Endpoints ---


@router.get("/summary", response_model=UsageSummary)
async def get_usage_summary(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get overall usage summary (admin only).
    """
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Total projects
    total_projects_result = await db.execute(select(func.count(Project.id)))
    total_projects = total_projects_result.scalar() or 0

    # Projects with transcriptions
    transcriptions_result = await db.execute(
        select(func.count(Project.id)).where(Project.transcription.isnot(None))
    )
    total_transcriptions = transcriptions_result.scalar() or 0

    # Projects with summaries
    summaries_result = await db.execute(
        select(func.count(Project.id)).where(Project.summary.isnot(None))
    )
    total_summaries = summaries_result.scalar() or 0

    # Total audio duration from usage logs
    audio_result = await db.execute(
        select(func.sum(UsageLog.duration_seconds)).where(
            UsageLog.operation == "transcription"
        )
    )
    total_audio_seconds = audio_result.scalar() or 0

    # Total tokens
    tokens_result = await db.execute(select(func.sum(UsageLog.tokens_used)))
    total_tokens_used = tokens_result.scalar() or 0

    # Estimated cost
    cost_result = await db.execute(select(func.sum(UsageLog.estimated_cost)))
    estimated_total_cost = cost_result.scalar() or 0

    # Projects today
    today_result = await db.execute(
        select(func.count(Project.id)).where(Project.created_at >= today)
    )
    projects_today = today_result.scalar() or 0

    # Projects this week
    week_result = await db.execute(
        select(func.count(Project.id)).where(Project.created_at >= week_ago)
    )
    projects_this_week = week_result.scalar() or 0

    # Projects this month
    month_result = await db.execute(
        select(func.count(Project.id)).where(Project.created_at >= month_ago)
    )
    projects_this_month = month_result.scalar() or 0

    return UsageSummary(
        total_projects=total_projects,
        total_transcriptions=total_transcriptions,
        total_summaries=total_summaries,
        total_audio_seconds=float(total_audio_seconds),
        total_tokens_used=int(total_tokens_used),
        estimated_total_cost=float(estimated_total_cost),
        projects_today=projects_today,
        projects_this_week=projects_this_week,
        projects_this_month=projects_this_month,
    )


@router.get("/daily", response_model=List[DailyUsage])
async def get_daily_usage(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get daily usage data for the past N days (admin only).
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Build daily data
    daily_data = []
    current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    while current_date <= end_date:
        next_date = current_date + timedelta(days=1)

        # Projects created on this day
        projects_result = await db.execute(
            select(func.count(Project.id)).where(
                and_(
                    Project.created_at >= current_date,
                    Project.created_at < next_date,
                )
            )
        )
        projects = projects_result.scalar() or 0

        # Transcriptions on this day
        trans_result = await db.execute(
            select(func.count(UsageLog.id)).where(
                and_(
                    UsageLog.created_at >= current_date,
                    UsageLog.created_at < next_date,
                    UsageLog.operation == "transcription",
                )
            )
        )
        transcriptions = trans_result.scalar() or 0

        # Summaries on this day
        sum_result = await db.execute(
            select(func.count(UsageLog.id)).where(
                and_(
                    UsageLog.created_at >= current_date,
                    UsageLog.created_at < next_date,
                    UsageLog.operation == "summarization",
                )
            )
        )
        summaries = sum_result.scalar() or 0

        # Audio seconds on this day
        audio_result = await db.execute(
            select(func.sum(UsageLog.duration_seconds)).where(
                and_(
                    UsageLog.created_at >= current_date,
                    UsageLog.created_at < next_date,
                    UsageLog.operation == "transcription",
                )
            )
        )
        audio_seconds = audio_result.scalar() or 0

        # Tokens on this day
        tokens_result = await db.execute(
            select(func.sum(UsageLog.tokens_used)).where(
                and_(
                    UsageLog.created_at >= current_date,
                    UsageLog.created_at < next_date,
                )
            )
        )
        tokens_used = tokens_result.scalar() or 0

        daily_data.append(
            DailyUsage(
                date=current_date.strftime("%Y-%m-%d"),
                projects=projects,
                transcriptions=transcriptions,
                summaries=summaries,
                audio_seconds=float(audio_seconds),
                tokens_used=int(tokens_used),
            )
        )

        current_date = next_date

    return daily_data


@router.get("/by-model", response_model=List[ModelUsage])
async def get_usage_by_model(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get usage statistics grouped by model (admin only).
    """
    # Get all models with usage
    result = await db.execute(
        select(
            UsageLog.model_id,
            func.count(UsageLog.id).label("usage_count"),
            func.sum(UsageLog.duration_seconds).label("total_audio"),
            func.sum(UsageLog.tokens_used).label("total_tokens"),
            func.sum(UsageLog.estimated_cost).label("total_cost"),
        )
        .group_by(UsageLog.model_id)
        .order_by(func.count(UsageLog.id).desc())
    )
    usage_data = result.all()

    model_usages = []
    for row in usage_data:
        # Get model details
        model_result = await db.execute(
            select(ModelConfig).where(ModelConfig.id == row.model_id)
        )
        model = model_result.scalar_one_or_none()

        if model:
            model_usages.append(
                ModelUsage(
                    model_id=model.id,
                    model_name=model.display_name,
                    model_type=model.model_type,
                    usage_count=row.usage_count,
                    total_audio_seconds=float(row.total_audio or 0),
                    total_tokens=int(row.total_tokens or 0),
                    estimated_cost=float(row.total_cost or 0),
                )
            )

    return model_usages


@router.get("/top-users", response_model=List[TopUser])
async def get_top_users(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get top users by usage (admin only).
    """
    # Get users with most projects
    result = await db.execute(
        select(
            Project.user_id,
            func.count(Project.id).label("project_count"),
        )
        .group_by(Project.user_id)
        .order_by(func.count(Project.id).desc())
        .limit(limit)
    )
    user_data = result.all()

    top_users = []
    for row in user_data:
        # Get user details
        user_result = await db.execute(
            select(User).where(User.id == row.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user:
            # Get usage stats
            usage_result = await db.execute(
                select(
                    func.sum(UsageLog.duration_seconds).label("total_audio"),
                    func.sum(UsageLog.tokens_used).label("total_tokens"),
                ).where(UsageLog.user_id == user.id)
            )
            usage = usage_result.one()

            top_users.append(
                TopUser(
                    user_id=user.id,
                    email=user.email,
                    name=user.name,
                    project_count=row.project_count,
                    total_audio_seconds=float(usage.total_audio or 0),
                    total_tokens=int(usage.total_tokens or 0),
                )
            )

    return top_users


@router.get("/logs", response_model=List[UsageLogEntry])
async def get_usage_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = None,
    model_id: Optional[int] = None,
    operation: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    """
    Get paginated usage logs (admin only).
    """
    query = select(UsageLog)

    if user_id:
        query = query.where(UsageLog.user_id == user_id)
    if model_id:
        query = query.where(UsageLog.model_id == model_id)
    if operation:
        query = query.where(UsageLog.operation == operation)

    query = query.order_by(UsageLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    log_entries = []
    for log in logs:
        # Get related data
        user_result = await db.execute(select(User).where(User.id == log.user_id))
        user = user_result.scalar_one_or_none()

        project_result = await db.execute(
            select(Project).where(Project.id == log.project_id)
        )
        project = project_result.scalar_one_or_none()

        model_result = await db.execute(
            select(ModelConfig).where(ModelConfig.id == log.model_id)
        )
        model = model_result.scalar_one_or_none()

        log_entries.append(
            UsageLogEntry(
                id=log.id,
                user_email=user.email if user else "Unknown",
                project_title=project.title if project else "Unknown",
                model_name=model.display_name if model else "Unknown",
                operation=log.operation,
                input_size_bytes=log.input_size_bytes or 0,
                duration_seconds=float(log.duration_seconds or 0),
                tokens_used=log.tokens_used or 0,
                estimated_cost=float(log.estimated_cost or 0),
                created_at=log.created_at.isoformat(),
            )
        )

    return log_entries
