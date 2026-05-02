import asyncio
from services.ai.ai_store_builder import build_store_with_ai
from app.database import AsyncSessionLocal


async def run_store_build_pipeline(payload: dict, business_id: str) -> dict:
    async with AsyncSessionLocal() as db:
        result = await build_store_with_ai(
            db=db,
            store_id=payload["store_id"],
            business_name=payload["business_name"],
            business_type=payload["business_type"],
            description=payload.get("description"),
            target_audience=payload.get("target_audience"),
            style_preferences=payload.get("style_preferences"),
            num_products=payload.get("num_products", 5),
        )

        from services.storefront_service import apply_ai_build_result
        await apply_ai_build_result(db, payload["store_id"], result)

    return result


def run_pipeline_sync(payload: dict, business_id: str):
    asyncio.run(run_store_build_pipeline(payload, business_id))
