from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts import RateLimitInfo, UsageResponse, UserResponse
from packages.db.database import get_db_session
from packages.db.models import Plan, UsageRecord, User

from ..dependencies.auth import get_current_authenticated_user
from ..middleware.rate_limiter import rate_limiter

router = APIRouter(prefix="/v1", tags=["User & Usage"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_authenticated_user)],
):
    """Returns the authenticated developer's profile."""
    return UserResponse(
        id=current_user.id,
        org_id=current_user.org_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )

@router.get("/me/usage", response_model=UsageResponse)
async def get_user_usage_and_quota(
    current_user: Annotated[User, Depends(get_current_authenticated_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Returns the developer's monthly token consumption and real-time rate limit status."""
    # 1. Fetch user plan limits
    plan = None
    if current_user.plan_id:
        plan_result = await session.execute(select(Plan).where(Plan.id == current_user.plan_id))
        plan = plan_result.scalar_one_or_none()

    monthly_limit = plan.monthly_token_limit if plan and plan.monthly_token_limit else 50_000_000
    tier_name = plan.code if plan else "developer"

    # 2. Query monthly token usage from usage_records (indexed by user_id and recorded_at)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    usage_query = select(
        func.coalesce(func.sum(UsageRecord.total_tokens), 0)
    ).where(
        UsageRecord.user_id == current_user.id,
        UsageRecord.recorded_at >= thirty_days_ago,
    )
    result = await session.execute(usage_query)
    tokens_used = int(result.scalar() or 0)
    tokens_remaining = max(0, monthly_limit - tokens_used)

    # 3. Check rate limit state in Redis
    rl_status = await rate_limiter.check_rate_limit(
        user_id=str(current_user.id),
        endpoint="/v1/me/usage",
        capacity=60,
    )

    return UsageResponse(
        user_id=current_user.id,
        tier=tier_name,
        monthly_token_limit=monthly_limit,
        tokens_used_this_month=tokens_used,
        tokens_remaining=tokens_remaining,
        rate_limit=RateLimitInfo(
            requests_per_minute=60,
            requests_remaining=rl_status["remaining"],
            reset_in_seconds=rl_status["reset_in_seconds"],
        ),
    )
