from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from core.security import get_current_user
from core.billing import get_active_subscription, create_subscription, cancel_subscription
from core.plans import PLANS

router = APIRouter()


class SubscribeRequest(BaseModel):
    plan_name: str
    billing_cycle: str = "monthly"


@router.get("/plans")
async def list_plans():
    return PLANS


@router.get("/subscription")
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    subscription = await get_active_subscription(db, current_user["id"])
    if not subscription:
        return {"plan": "free", "status": "active"}
    return subscription


@router.post("/subscribe")
async def subscribe(
    payload: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if payload.plan_name not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    subscription = await create_subscription(db, current_user["id"], payload.plan_name)
    return subscription


@router.post("/cancel")
async def cancel(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    subscription = await get_active_subscription(db, current_user["id"])
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription")
    updated = await cancel_subscription(db, subscription.id)
    return updated
