from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.store import Store
from models.category import Category
from models.product import Product


async def register_subdomain(subdomain: str, store_id: str) -> bool:
    subdomain_clean = subdomain.lower().strip().replace(" ", "-")
    return True


async def release_subdomain(subdomain: str) -> bool:
    return True


async def get_store_by_subdomain(db: AsyncSession, subdomain: str) -> Store | None:
    result = await db.execute(select(Store).where(Store.subdomain == subdomain))
    return result.scalar_one_or_none()


async def apply_ai_build_result(db: AsyncSession, store_id: str, build_result: dict) -> None:
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        return

    branding = build_result.get("branding", {})
    storefront = build_result.get("storefront", {})
    store.theme = {
        "primary_color": branding.get("primary_color"),
        "secondary_color": branding.get("secondary_color"),
        "accent_color": branding.get("accent_color"),
        "font_family": branding.get("font_family"),
        "brand_voice": branding.get("brand_voice"),
    }
    await db.commit()

    for cat_data in build_result.get("categories", []):
        category = Category(
            store_id=store_id,
            name=cat_data.get("name", ""),
            description=cat_data.get("description"),
        )
        db.add(category)

    await db.commit()

    for prod_data in build_result.get("products", []):
        product = Product(
            store_id=store_id,
            name=prod_data.get("name", ""),
            description=prod_data.get("description"),
            price=prod_data.get("price", 0),
            sku=prod_data.get("sku"),
            stock_quantity=prod_data.get("stock_quantity", 0),
        )
        db.add(product)

    await db.commit()
