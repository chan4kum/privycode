from pydantic import BaseModel
from uuid import UUID

class ModelProfile(BaseModel):
    id: str
    name: str
    provider: str
    capabilities: list[str]
    context_window: int

class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelProfile]

class RateLimitInfo(BaseModel):
    requests_per_minute: int
    requests_remaining: int
    reset_in_seconds: int

class UsageResponse(BaseModel):
    user_id: UUID
    tier: str
    monthly_token_limit: int
    tokens_used_this_month: int
    tokens_remaining: int
    rate_limit: RateLimitInfo
