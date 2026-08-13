from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.database import get_db_session
from packages.db.models import InferenceWorker

router = APIRouter(prefix="/internal/workers", tags=["Worker Management"])

class WorkerRegistrationRequest(BaseModel):
    name: str
    runtime: str
    base_url: str
    status: str = "healthy"
    max_context_tokens: int = 32768

@router.post("/register", status_code=status.HTTP_200_OK)
async def register_worker(
    req: WorkerRegistrationRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Registers or updates an inference worker node."""
    query = select(InferenceWorker).where(InferenceWorker.name == req.name)
    result = await session.execute(query)
    worker = result.scalar_one_or_none()

    if worker:
        worker.runtime = req.runtime
        worker.base_url = req.base_url
        worker.status = req.status
        worker.max_context_tokens = req.max_context_tokens
        worker.last_heartbeat_at = datetime.now(timezone.utc)
    else:
        worker = InferenceWorker(
            name=req.name,
            runtime=req.runtime,
            base_url=req.base_url,
            status=req.status,
            max_context_tokens=req.max_context_tokens,
            last_heartbeat_at=datetime.now(timezone.utc),
        )
        session.add(worker)

    await session.commit()
    return {"status": "registered", "worker_id": str(worker.id)}

@router.post("/heartbeat", status_code=status.HTTP_200_OK)
async def worker_heartbeat(
    req: WorkerRegistrationRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Updates the heartbeat timestamp for an active inference worker node."""
    query = select(InferenceWorker).where(InferenceWorker.name == req.name)
    result = await session.execute(query)
    worker = result.scalar_one_or_none()

    if not worker:
        return await register_worker(req, session)

    worker.status = req.status
    worker.last_heartbeat_at = datetime.now(timezone.utc)
    await session.commit()
    return {"status": "heartbeat_acknowledged"}
