import os
import pytest
import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from apps.api.middleware.tier_enforcer import evaluate_user_tier_quota
from packages.config import common_settings
from packages.db.models import Organization, Plan, UsageRecord, User


@pytest.mark.asyncio
async def test_tier_enforcer_pro_plan_allowed():
    db_url = os.getenv("DATABASE_URL", common_settings.database_url)
    engine = create_async_engine(db_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        plan = Plan(
            id=uuid.uuid4(),
            code=f"test-pro-{uuid.uuid4().hex[:6]}",
            monthly_token_limit=50000000,
            monthly_request_limit=50000,
            strong_model_allowed=True,
        )
        org = Organization(
            id=uuid.uuid4(),
            name="Test Pro Org",
            slug=f"pro-org-{uuid.uuid4().hex[:6]}",
        )
        user = User(
            id=uuid.uuid4(),
            org_id=org.id,
            plan_id=plan.id,
            email=f"test-pro-{uuid.uuid4().hex[:6]}@acmecorp.com",
            password_hash="testhash",
            role="developer",
        )
        session.add_all([plan, org, user])
        await session.commit()

        result = await evaluate_user_tier_quota(session, user, estimated_tokens=100)
        assert result["allowed"] is True
        assert result["plan"] == plan.code
        assert result["quota"] == 50000000
        assert result["remaining"] == 50000000

    await engine.dispose()


@pytest.mark.asyncio
async def test_tier_enforcer_starter_quota_exhausted():
    db_url = os.getenv("DATABASE_URL", common_settings.database_url)
    engine = create_async_engine(db_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        plan = Plan(
            id=uuid.uuid4(),
            code=f"test-tiny-{uuid.uuid4().hex[:6]}",
            monthly_token_limit=100,
            monthly_request_limit=100,
            strong_model_allowed=False,
        )
        org = Organization(
            id=uuid.uuid4(),
            name="Test Tiny Org",
            slug=f"tiny-org-{uuid.uuid4().hex[:6]}",
        )
        user = User(
            id=uuid.uuid4(),
            org_id=org.id,
            plan_id=plan.id,
            email=f"test-tiny-{uuid.uuid4().hex[:6]}@acmecorp.com",
            password_hash="testhash",
            role="developer",
        )
        session.add_all([plan, org, user])
        await session.commit()

        # Add usage record using 90 tokens
        usage = UsageRecord(
            user_id=user.id,
            model_id="mock-qwen-32b",
            endpoint="/v1/chat",
            prompt_tokens=50,
            completion_tokens=40,
            latency_ms=30,
            status_code=200,
        )
        session.add(usage)
        await session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await evaluate_user_tier_quota(session, user, estimated_tokens=20)
        
        assert exc_info.value.status_code == 402
        assert "Monthly token quota exhausted" in exc_info.value.detail

    await engine.dispose()
