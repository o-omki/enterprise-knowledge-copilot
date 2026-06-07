import asyncio
import hashlib
import os
import sys

from sqlalchemy import select

from packages.shared.database import async_session_maker
from packages.shared.orm_models import ApiKey

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def seed_api_keys():
    """Seeds default and dev API keys into the database."""
    cleartext_key = os.getenv("DEFAULT_API_KEY", "ekc_dev_key_12345")
    key_hash = hashlib.sha256(cleartext_key.encode("utf-8")).hexdigest()
    label = "Default Development Key"

    print("Checking database for existing API key...")
    async with async_session_maker() as db:
        query = select(ApiKey).where(ApiKey.key_hash == key_hash)
        result = await db.execute(query)
        existing_key = result.scalar_one_or_none()

        if existing_key:
            print(f"API key already exists in DB! ID: {existing_key.id}")
            print(f"Cleartext API Key: {cleartext_key}")
            return

        print("Key not found. Seeding new developer API key...")
        new_key = ApiKey(key_hash=key_hash, label=label, is_active=True)
        db.add(new_key)
        await db.commit()

        # Reload key to print ID
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash)
        result = await db.execute(stmt)
        added_key = result.scalar_one()

        print("--------------------------------------------------")
        print("Successfully seeded developer API key!")
        print(f"Key ID:        {added_key.id}")
        print(f"Cleartext Key: {cleartext_key}")
        print(f"Label:         {label}")
        print("--------------------------------------------------")
        print("Use the 'X-API-Key' header in your requests:")
        print(f"X-API-Key: {cleartext_key}")
        print("--------------------------------------------------")


if __name__ == "__main__":
    asyncio.run(seed_api_keys())
