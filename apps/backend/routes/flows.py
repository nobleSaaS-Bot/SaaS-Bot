from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from models.flow import Flow
from core.security import get_current_user

router = APIRouter()


class FlowCreate(BaseModel):
    store_id: str
    name: str
    description: Optional[str] = None
    trigger: str
    steps: list = []
    is_active: bool = True


class FlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger: Optional[str] = None
    steps: Optional[list] = None
    is_active: Optional[bool] = None


@router.get("/")
async def list_flows(
    store_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Flow).where(Flow.store_id == store_id))
    return result.scalars().all()


@router.post("/", status_code=201)
async def create_flow(
    payload: FlowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    flow = Flow(**payload.model_dump())
    db.add(flow)
    await db.commit()
    await db.refresh(flow)
    return flow


@router.get("/{flow_id}")
async def get_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow


@router.patch("/{flow_id}")
async def update_flow(
    flow_id: str,
    payload: FlowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(flow, field, value)
    await db.commit()
    await db.refresh(flow)
    return flow


@router.delete("/{flow_id}", status_code=204)
async def delete_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    await db.delete(flow)
    await db.commit()
