from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.store import Store


async def verify_custom_domain(domain: str) -> dict:
    return {
        "domain": domain,
        "verified": False,
        "cname_target": "stores.yoursaasplatform.com",
        "instructions": f"Add a CNAME record pointing {domain} to stores.yoursaasplatform.com",
    }


async def provision_ssl(domain: str) -> bool:
    return True


async def get_store_by_custom_domain(db: AsyncSession, domain: str) -> Store | None:
    result = await db.execute(select(Store).where(Store.custom_domain == domain))
    return result.scalar_one_or_none()


async def set_custom_domain(db: AsyncSession, store_id: str, domain: str) -> Store:
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise ValueError("Store not found")
    store.custom_domain = domain
    await db.commit()
    await db.refresh(store)
    return store


async def remove_custom_domain(db: AsyncSession, store_id: str) -> Store:
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise ValueError("Store not found")
    store.custom_domain = None
    await db.commit()
    await db.refresh(store)
    return store
