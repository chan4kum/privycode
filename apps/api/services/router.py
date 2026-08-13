from datetime import datetime, timedelta, timezone
import logging
from typing import Tuple
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts import RequestMode
from packages.db.models import InferenceWorker, ModelRegistry, Plan, User

logger = logging.getLogger("model-router")

class ModelRouter:
    """Intelligent Model Router resolving requests based on task, tier, user plan, and worker health."""

    async def resolve_route(
        self,
        session: AsyncSession,
        user: User,
        requested_model: str,
        mode: RequestMode = "balanced",
        request_type: str = "chat",
    ) -> Tuple[ModelRegistry, str]:
        """
        Resolves the appropriate ModelRegistry entry and target worker URL.
        Enforces tenant plan limits (e.g. strong model access) and checks worker heartbeat freshness.
        """
        # 1. Fetch user's plan permissions
        plan = None
        if user.plan_id:
            plan_res = await session.execute(select(Plan).where(Plan.id == user.plan_id))
            plan = plan_res.scalar_one_or_none()

        strong_allowed = plan.strong_model_allowed if plan else False

        # 2. Determine target model ID based on mode & permissions
        target_model_id = requested_model

        if request_type == "autocomplete":
            # Autocomplete always routes to fast lightweight model
            target_model_id = "mock-qwen-7b"
        elif mode == "cheap":
            target_model_id = "mock-qwen-7b"
        elif mode == "strong" and not strong_allowed:
            logger.warning(
                f"User {user.id} requested strong model on plan '{plan.code if plan else 'none'}'. Downgrading to balanced."
            )
            target_model_id = "mock-qwen-7b"

        # 3. Fetch model from Model Registry
        model_res = await session.execute(
            select(ModelRegistry).where(ModelRegistry.id == target_model_id, ModelRegistry.is_active == True)
        )
        model = model_res.scalar_one_or_none()

        # Fallback to any active model if specific ID not found
        if not model:
            fallback_res = await session.execute(
                select(ModelRegistry).where(ModelRegistry.is_active == True).limit(1)
            )
            model = fallback_res.scalar_one_or_none()
            if not model:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No active model inference backend is available.",
                )

        # 4. Resolve worker URL (check healthy worker with fresh heartbeat within 30 seconds)
        freshness_threshold = datetime.now(timezone.utc) - timedelta(seconds=30)
        worker_res = await session.execute(
            select(InferenceWorker)
            .where(
                InferenceWorker.status == "healthy",
                InferenceWorker.last_heartbeat_at >= freshness_threshold,
            )
            .order_by(InferenceWorker.last_heartbeat_at.desc())
            .limit(1)
        )
        worker = worker_res.scalar_one_or_none()
        worker_url = worker.base_url if worker else model.worker_url

        logger.info(f"Routed [{request_type}:{mode}] for user {user.id} -> model '{model.id}' @ '{worker_url}'")
        return model, worker_url

model_router = ModelRouter()
