from datetime import datetime, timezone
import hashlib
import sys
from pathlib import Path
from typing import Annotated

# Ensure workspace packages can be imported
root_dir = str(Path(__file__).resolve().parents[3])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.database import get_db_session
from packages.db.models import ApiKey, User

security = HTTPBearer(auto_error=False)

async def get_current_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(security)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """
    Validates Bearer API Key ('sk_live_...') using SHA-256 hash matching against PostgreSQL.
    Returns the User model and updates the ApiKey.last_used_at timestamp.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Provide 'Bearer sk_live_...'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_key = credentials.credentials.strip()
    if not raw_key.startswith("sk_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format. Key must start with 'sk_'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    # Query active API key
    result = await session.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    )
    api_key_record = result.scalar_one_or_none()

    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch active user
    user_result = await session.execute(
        select(User).where(User.id == api_key_record.user_id, User.is_active == True)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Associated user account is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last_used_at audit timestamp
    api_key_record.last_used_at = datetime.now(timezone.utc)
    await session.commit()

    return user
