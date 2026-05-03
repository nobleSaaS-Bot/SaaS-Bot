from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.database import get_db
from core.security import get_current_business
from models.customer import Customer, CustomerSegment
from models.order import Order

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class CustomerUpdate(BaseModel):
    segment: Optional[CustomerSegment] = None
    tags: Optional[list[str]] = None
    notes: Optional[str] = None
    is_blocked: Optional[bool] = None


class CustomerOut(BaseModel):
    id: str
    telegram_id: str
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    photo_url: Optional[str]
    segment: CustomerSegment
    tags: list
    notes: Optional[str]
    total_orders: int
    total_spent: float
    currency: str
    last_order_at: Optional[datetime]
    is_blocked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OrderSummary(BaseModel):
    id: str
    status: str
    total: float
    currency: str
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerDetail(CustomerOut):
    recent_orders: list[OrderSummary] = []


class CustomerStats(BaseModel):
    total: int
    new_this_month: int
    vip: int
    at_risk: int
    total_revenue: float


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=CustomerStats)
async def get_customer_stats(
    store_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    base = and_(Customer.business_id == business.id)
    if store_id:
        base = and_(base, Customer.store_id == store_id)

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total = await db.scalar(select(func.count()).where(base))
    new_this_month = await db.scalar(
        select(func.count()).where(and_(base, Customer.created_at >= month_start))
    )
    vip = await db.scalar(
        select(func.count()).where(and_(base, Customer.segment == CustomerSegment.vip))
    )
    at_risk = await db.scalar(
        select(func.count()).where(and_(base, Customer.segment == CustomerSegment.at_risk))
    )
    revenue_result = await db.scalar(
        select(func.sum(Customer.total_spent)).where(base)
    )

    return CustomerStats(
        total=total or 0,
        new_this_month=new_this_month or 0,
        vip=vip or 0,
        at_risk=at_risk or 0,
        total_revenue=float(revenue_result or 0),
    )


@router.get("", response_model=list[CustomerOut])
async def list_customers(
    store_id: Optional[str] = Query(None),
    segment: Optional[CustomerSegment] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    filters = [Customer.business_id == business.id]
    if store_id:
        filters.append(Customer.store_id == store_id)
    if segment:
        filters.append(Customer.segment == segment)
    if search:
        term = f"%{search}%"
        filters.append(
            or_(
                Customer.first_name.ilike(term),
                Customer.last_name.ilike(term),
                Customer.username.ilike(term),
                Customer.phone.ilike(term),
                Customer.email.ilike(term),
            )
        )

    stmt = (
        select(Customer)
        .where(and_(*filters))
        .order_by(desc(Customer.last_order_at.nullslast()), desc(Customer.created_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{customer_id}", response_model=CustomerDetail)
async def get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    result = await db.execute(
        select(Customer).where(
            and_(Customer.id == customer_id, Customer.business_id == business.id)
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    orders_result = await db.execute(
        select(Order)
        .where(
            and_(
                Order.business_id == business.id,
                Order.customer_telegram_id == customer.telegram_id,
            )
        )
        .order_by(desc(Order.created_at))
        .limit(20)
    )
    recent_orders = orders_result.scalars().all()

    detail = CustomerDetail.model_validate(customer)
    detail.recent_orders = [OrderSummary.model_validate(o) for o in recent_orders]
    return detail


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    result = await db.execute(
        select(Customer).where(
            and_(Customer.id == customer_id, Customer.business_id == business.id)
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)
    return customer
