from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from core.security import get_current_business
from core.queue import enqueue_broadcast
from models.broadcast import Broadcast, BroadcastStatus, BroadcastSegment
from models.customer import Customer

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class BroadcastCreate(BaseModel):
    title: str
    message: str
    image_url: Optional[str] = None
    buttons: Optional[list[dict]] = []
    segment: BroadcastSegment = BroadcastSegment.all
    store_id: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class BroadcastOut(BaseModel):
    id: str
    title: str
    message: str
    image_url: Optional[str]
    buttons: list
    segment: BroadcastSegment
    status: BroadcastStatus
    scheduled_at: Optional[datetime]
    sent_at: Optional[datetime]
    total_recipients: int
    sent_count: int
    delivered_count: int
    failed_count: int
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BroadcastStats(BaseModel):
    total: int
    sent: int
    scheduled: int
    total_messages_sent: int


# ── Helpers ────────────────────────────────────────────────────────────────────

_SEGMENT_MAP: dict = {
    "new": "new",
    "regular": "repeat_buyer",
    "vip": "vip",
    "at_risk": "at_risk",
    "churned": "at_risk",
}


async def count_recipients(db: AsyncSession, business_id: str, segment: BroadcastSegment, store_id: Optional[str]) -> int:
    filters = [Customer.business_id == str(business_id), Customer.is_blocked == False]
    if segment != BroadcastSegment.all:
        seg_string = _SEGMENT_MAP.get(segment.value)
        if seg_string:
            filters.append(Customer.segments.contains([seg_string]))
    return await db.scalar(select(func.count()).where(and_(*filters))) or 0


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=BroadcastStats)
async def get_broadcast_stats(
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    total = await db.scalar(
        select(func.count()).where(Broadcast.business_id == business.id)
    ) or 0
    sent = await db.scalar(
        select(func.count()).where(
            and_(Broadcast.business_id == business.id, Broadcast.status == BroadcastStatus.sent)
        )
    ) or 0
    scheduled = await db.scalar(
        select(func.count()).where(
            and_(Broadcast.business_id == business.id, Broadcast.status == BroadcastStatus.scheduled)
        )
    ) or 0
    total_sent_result = await db.scalar(
        select(func.sum(Broadcast.sent_count)).where(Broadcast.business_id == business.id)
    )
    return BroadcastStats(
        total=total,
        sent=sent,
        scheduled=scheduled,
        total_messages_sent=int(total_sent_result or 0),
    )


@router.get("", response_model=list[BroadcastOut])
async def list_broadcasts(
    store_id: Optional[str] = Query(None),
    status: Optional[BroadcastStatus] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    filters = [Broadcast.business_id == business.id]
    if store_id:
        filters.append(Broadcast.store_id == store_id)
    if status:
        filters.append(Broadcast.status == status)

    result = await db.execute(
        select(Broadcast)
        .where(and_(*filters))
        .order_by(desc(Broadcast.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return result.scalars().all()


@router.post("", response_model=BroadcastOut, status_code=201)
async def create_broadcast(
    body: BroadcastCreate,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    recipients = await count_recipients(db, business.id, body.segment, body.store_id)

    status = BroadcastStatus.scheduled if body.scheduled_at else BroadcastStatus.draft
    broadcast = Broadcast(
        business_id=business.id,
        store_id=body.store_id,
        title=body.title,
        message=body.message,
        image_url=body.image_url,
        buttons=body.buttons or [],
        segment=body.segment,
        status=status,
        scheduled_at=body.scheduled_at,
        total_recipients=recipients,
    )
    db.add(broadcast)
    await db.commit()
    await db.refresh(broadcast)
    return broadcast


@router.post("/{broadcast_id}/send", response_model=BroadcastOut)
async def send_broadcast(
    broadcast_id: str,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    result = await db.execute(
        select(Broadcast).where(
            and_(Broadcast.id == broadcast_id, Broadcast.business_id == business.id)
        )
    )
    broadcast = result.scalar_one_or_none()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    if broadcast.status in (BroadcastStatus.sending, BroadcastStatus.sent):
        raise HTTPException(status_code=400, detail=f"Broadcast is already {broadcast.status.value}")

    recipients = await count_recipients(db, business.id, broadcast.segment, broadcast.store_id)
    broadcast.total_recipients = recipients
    broadcast.status = BroadcastStatus.sending
    await db.commit()
    await db.refresh(broadcast)

    enqueue_broadcast(broadcast_id=broadcast.id)
    return broadcast


@router.delete("/{broadcast_id}", status_code=204)
async def cancel_broadcast(
    broadcast_id: str,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    result = await db.execute(
        select(Broadcast).where(
            and_(Broadcast.id == broadcast_id, Broadcast.business_id == business.id)
        )
    )
    broadcast = result.scalar_one_or_none()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    if broadcast.status == BroadcastStatus.sending:
        raise HTTPException(status_code=400, detail="Cannot cancel a broadcast that is currently sending")

    broadcast.status = BroadcastStatus.cancelled
    await db.commit()


@router.get("/{broadcast_id}", response_model=BroadcastOut)
async def get_broadcast(
    broadcast_id: str,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    result = await db.execute(
        select(Broadcast).where(
            and_(Broadcast.id == broadcast_id, Broadcast.business_id == business.id)
        )
    )
    broadcast = result.scalar_one_or_none()
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return broadcast
