from .base import Base
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime, Numeric, Computed, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

class ModelRegistry(Base):
    __tablename__ = "model_registry"
    
    id = Column(String(100), primary_key=True)
    display_name = Column(String(150), nullable=False)
    provider = Column(String(50), nullable=False)
    worker_url = Column(String(255), nullable=False)
    context_window = Column(Integer, default=32768, nullable=False)
    cost_per_1k_prompt_tokens = Column(Numeric(10, 6), default=0.0)
    cost_per_1k_completion_tokens = Column(Numeric(10, 6), default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class InferenceWorker(Base):
    __tablename__ = "inference_workers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    runtime = Column(String(50), nullable=False)
    base_url = Column(String(255), nullable=False)
    status = Column(String(50), default="offline")
    max_context_tokens = Column(Integer, default=32768)
    last_heartbeat_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        Index("idx_usage_user_date", "user_id", "recorded_at"),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    inference_worker_id = Column(UUID(as_uuid=True), ForeignKey("inference_workers.id", ondelete="SET NULL"))
    endpoint = Column(String(50), nullable=False)
    model_id = Column(String(100), ForeignKey("model_registry.id"), nullable=False, index=True)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, Computed("prompt_tokens + completion_tokens"))
    latency_ms = Column(Integer, nullable=False)
    status_code = Column(Integer, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String(100), ForeignKey("model_registry.id", ondelete="CASCADE"), nullable=False)
    benchmark_name = Column(String(150), nullable=False)
    quality_score = Column(Numeric(5, 2))
    latency_ms = Column(Integer)
    estimated_cost = Column(Numeric(10, 6))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
