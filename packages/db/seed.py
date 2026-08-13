import asyncio
import hashlib
from database import engine, AsyncSessionLocal
from models import Base, Plan, Organization, User, ApiKey, ModelRegistry

async def seed_database():
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Inserting seed data...")
    async with AsyncSessionLocal() as session:
        # Seed Plans
        free_plan = Plan(code="free", monthly_request_limit=1000, monthly_token_limit=1000000, strong_model_allowed=False)
        pro_plan = Plan(code="pro", monthly_request_limit=10000, monthly_token_limit=50000000, strong_model_allowed=True)
        session.add_all([free_plan, pro_plan])
        await session.flush()
        
        # Seed Mock Organization and User
        org = Organization(name="Acme Corp", slug="acme-corp")
        session.add(org)
        await session.flush()
        
        test_user = User(
            org_id=org.id,
            plan_id=pro_plan.id,
            email="dev@acmecorp.local",
            password_hash="bcrypt_hash_placeholder",
            full_name="Test Dev"
        )
        session.add(test_user)
        await session.flush()
        
        # Seed Development API Key: 'sk_live_dev_test_12345'
        raw_key = "sk_live_dev_test_12345"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        dev_api_key = ApiKey(
            user_id=test_user.id,
            key_hash=key_hash,
            key_prefix=raw_key[:12],
            name="Development Key"
        )
        session.add(dev_api_key)
        
        # Seed Model Registry
        mock_cheap = ModelRegistry(
            id="mock-qwen-7b", 
            display_name="Mock Qwen 7B (Fast)", 
            provider="mock", 
            worker_url="http://mock-worker:8001"
        )
        mock_strong = ModelRegistry(
            id="mock-qwen-32b", 
            display_name="Mock Qwen 32B (Strong)", 
            provider="mock", 
            worker_url="http://mock-worker:8001"
        )
        session.add_all([mock_cheap, mock_strong])
        
        await session.commit()
    print("Seed complete! Seeded dev API key: sk_live_dev_test_12345")

if __name__ == "__main__":
    asyncio.run(seed_database())
