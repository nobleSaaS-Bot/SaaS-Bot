from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from core.security import get_current_user
from core.billing import enforce_plan
from services.ai.ai_pipeline import run_store_build_pipeline

router = APIRouter()


class BuildStoreRequest(BaseModel):
    store_id: str
    business_name: str
    business_type: str
    description: Optional[str] = None
    target_audience: Optional[str] = None
    style_preferences: Optional[str] = None
    num_products: int = 5


class GenerateProductRequest(BaseModel):
    store_id: str
    category: str
    num_products: int = 3
    style: Optional[str] = None


@router.post("/build-store")
async def build_store(
    payload: BuildStoreRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await enforce_plan(db, current_user["id"], "ai_store_builder")
    background_tasks.add_task(run_store_build_pipeline, payload.model_dump(), current_user["id"])
    return {"message": "Store build started", "store_id": payload.store_id}


@router.post("/generate-products")
async def generate_products(
    payload: GenerateProductRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await enforce_plan(db, current_user["id"], "ai_store_builder")
    from services.ai.ai_product_generator import generate_products_for_store
    products = await generate_products_for_store(
        store_id=payload.store_id,
        category=payload.category,
        num_products=payload.num_products,
        style=payload.style,
    )
    return {"products": products}


@router.post("/generate-branding")
async def generate_branding(
    store_id: str,
    business_name: str,
    business_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await enforce_plan(db, current_user["id"], "ai_store_builder")
    from services.ai.ai_branding import generate_branding
    branding = await generate_branding(business_name, business_type)
    return branding
