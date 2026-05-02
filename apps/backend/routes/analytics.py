from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from models.order import Order, OrderStatus
from core.security import get_current_user
from core.billing import enforce_plan
from services.analytics_service import (
    get_revenue_summary,
    get_orders_over_time,
    get_top_products,
)

router = APIRouter()


@router.get("/summary")
async def get_summary(
    store_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await enforce_plan(db, current_user["id"], "analytics")
    summary = await get_revenue_summary(db, store_id)
    return summary


@router.get("/orders-over-time")
async def orders_over_time(
    store_id: str = Query(...),
    days: int = Query(30),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await enforce_plan(db, current_user["id"], "analytics")
    data = await get_orders_over_time(db, store_id, days)
    return data


@router.get("/top-products")
async def top_products(
    store_id: str = Query(...),
    limit: int = Query(10),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await enforce_plan(db, current_user["id"], "analytics")
    data = await get_top_products(db, store_id, limit)
    return data
