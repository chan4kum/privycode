import logging
from typing import Optional
from uuid import UUID
from packages.db.database import AsyncSessionLocal
from packages.db.models import UsageRecord

logger = logging.getLogger("usage-telemetry")

async def record_usage_telemetry(
    user_id: UUID,
    model_id: str,
    endpoint: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    status_code: int = 200,
    worker_id: Optional[UUID] = None,
):
    """
    Asynchronously records anonymized token telemetry to PostgreSQL.
    Guarantees zero-retention: NO code snippets, messages, or diffs are persisted.
    """
    try:
        async with AsyncSessionLocal() as session:
            record = UsageRecord(
                user_id=user_id,
                inference_worker_id=worker_id,
                endpoint=endpoint,
                model_id=model_id,
                prompt_tokens=max(0, prompt_tokens),
                completion_tokens=max(0, completion_tokens),
                latency_ms=max(0, latency_ms),
                status_code=status_code,
            )
            session.add(record)
            await session.commit()
            logger.debug(
                f"Recorded usage for user {user_id}: {prompt_tokens}+{completion_tokens} tokens "
                f"[{latency_ms}ms] on {endpoint}"
            )
    except Exception as e:
        logger.error(f"Failed to record usage telemetry for user {user_id}: {e}")
