from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from models.store import Store
from core.security import get_current_user
from services.storefront_service import register_subdomain

router = APIRouter()


class StoreCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subdomain: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    currency: str = "USD"


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subdomain: Optional[str] = None
    custom_domain: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_stores(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Store).where(Store.business_id == current_user["id"])
    )
    return result.scalars().all()


@router.post("/", status_code=201)
async def create_store(
    payload: StoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    store = Store(business_id=current_user["id"], **payload.model_dump())
    if payload.subdomain:
        await register_subdomain(payload.subdomain, store.id)
    db.add(store)
    await db.commit()
    await db.refresh(store)
    return store


@router.get("/{store_id}")
async def get_store(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.business_id == current_user["id"])
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.patch("/{store_id}")
async def update_store(
    store_id: str,
    payload: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.business_id == current_user["id"])
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(store, field, value)
    await db.commit()
    await db.refresh(store)
    return store


@router.delete("/{store_id}", status_code=204)
async def delete_store(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Store).where(Store.id == store_id, Store.business_id == current_user["id"])
    )
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    await db.delete(store)
    await db.commit()
