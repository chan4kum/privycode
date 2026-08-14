from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from packages.db.models import Plan, UsageRecord, User


async def evaluate_user_tier_quota(
    session: AsyncSession,
    user: User,
    estimated_tokens: int = 50,
) -> Dict[str, Any]:
    """
    Evaluates whether the user has remaining monthly token quota under their plan tier.
    Returns quota status or raises HTTPException(402) if monthly budget is exhausted.
    """
    if not user.plan_id:
        return {"allowed": True, "used": 0, "quota": 100000, "plan": "starter", "remaining": 100000}

    plan_res = await session.execute(
        select(Plan).where(Plan.id == user.plan_id)
    )
    plan = plan_res.scalar_one_or_none()
    monthly_quota = plan.monthly_token_limit if (plan and plan.monthly_token_limit is not None) else 50000000
    plan_code = plan.code if plan else "starter"

    # Enterprise tier accounts with unlimited quota (-1 or 0)
    if monthly_quota <= 0:
        return {
            "allowed": True,
            "used": 0,
            "quota": -1,
            "plan": plan_code,
            "remaining": 999999999,
        }

    # Calculate tokens consumed in current calendar month
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    usage_res = await session.execute(
        select(func.coalesce(func.sum(UsageRecord.prompt_tokens + UsageRecord.completion_tokens), 0))
        .where(
            UsageRecord.user_id == user.id,
            UsageRecord.recorded_at >= month_start,
        )
    )
    total_tokens_used = usage_res.scalar() or 0
    remaining = max(0, monthly_quota - total_tokens_used)

    if total_tokens_used + estimated_tokens > monthly_quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Monthly token quota exhausted for plan '{plan_code}'. "
                f"Used: {total_tokens_used:,}/{monthly_quota:,} tokens. "
                f"Upgrade your subscription to continue."
            ),
        )

    return {
        "allowed": True,
        "used": total_tokens_used,
        "quota": monthly_quota,
        "plan": plan_code,
        "remaining": remaining,
    }
