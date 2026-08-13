from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts import ModelListResponse, ModelProfile
from packages.db.database import get_db_session
from packages.db.models import ModelRegistry, User

from ..dependencies.auth import get_current_authenticated_user

router = APIRouter(prefix="/v1", tags=["Models & Profiles"])

@router.get("/models", response_model=ModelListResponse)
async def list_available_models(
    current_user: Annotated[User, Depends(get_current_authenticated_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Returns active model routing profiles accessible to the user."""
    query = select(ModelRegistry).where(ModelRegistry.is_active == True)
    result = await session.execute(query)
    models = result.scalars().all()

    profile_list = []
    for m in models:
        # Infer capabilities
        capabilities = ["chat", "edits"]
        if "7b" in m.id.lower() or "fast" in m.id.lower():
            capabilities.append("autocomplete")

        profile_list.append(
            ModelProfile(
                id=m.id,
                name=m.display_name,
                provider=m.provider,
                capabilities=capabilities,
                context_window=m.context_window,
            )
        )

    return ModelListResponse(object="list", data=profile_list)
