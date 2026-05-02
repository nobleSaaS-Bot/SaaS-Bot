from sqlalchemy.ext.asyncio import AsyncSession

from services.ai.ai_product_generator import generate_products_for_store
from services.ai.ai_branding import generate_branding
from services.ai.ai_categories import generate_categories
from services.ai.ai_storefront import generate_storefront_content


async def build_store_with_ai(
    db: AsyncSession,
    store_id: str,
    business_name: str,
    business_type: str,
    description: str | None = None,
    target_audience: str | None = None,
    style_preferences: str | None = None,
    num_products: int = 5,
) -> dict:
    storefront = await generate_storefront_content(business_name, business_type, description)
    branding = await generate_branding(business_name, business_type)
    categories = await generate_categories(business_type, num_categories=3)

    products = []
    for category in categories[:2]:
        category_products = await generate_products_for_store(
            store_id=store_id,
            category=category["name"],
            num_products=max(2, num_products // len(categories)),
            style=style_preferences,
        )
        products.extend(category_products)

    return {
        "storefront": storefront,
        "branding": branding,
        "categories": categories,
        "products": products,
    }
