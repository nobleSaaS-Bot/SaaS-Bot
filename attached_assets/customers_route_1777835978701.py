"""
routes/customers.py

Customer CRM API — full read/write access for merchants to manage
the Telegram users who shop at their store.

Endpoints
─────────
GET    /customers                  Paginated list with filters + search
GET    /customers/stats            Aggregate CRM stats (for dashboard cards)
GET    /customers/{id}             Single customer profile + recent orders
PATCH  /customers/{id}             Update notes, tags, segments, blocked status
GET    /customers/{id}/orders      Order history for a customer
POST   /customers/{id}/segment     Add/remove a segment label
GET    /customers/export           CSV export of full customer list
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from core.security import get_current_business
from models.customer import Customer
from models.order import Order

router = APIRouter(prefix="/customers", tags=["customers"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CustomerSummary(BaseModel):
    id: str
    display_name: str
    telegram_username: Optional[str]
    telegram_user_id: int
    total_orders: int
    total_spent: float
    average_order_value: float
    last_order_at: Optional[str]
    first_order_at: Optional[str]
    segments: List[str]
    tags: List[str]
    is_blocked: bool
    last_seen_at: Optional[str]
    message_count: int
    created_at: str

    @classmethod
    def from_orm(cls, c: Customer) -> "CustomerSummary":
        def fmt(dt): return dt.isoformat() if dt else None
        return cls(
            id=str(c.id),
            display_name=c.display_name,
            telegram_username=c.telegram_username,
            telegram_user_id=c.telegram_user_id,
            total_orders=c.total_orders,
            total_spent=round(c.total_spent, 2),
            average_order_value=round(c.average_order_value, 2),
            last_order_at=fmt(c.last_order_at),
            first_order_at=fmt(c.first_order_at),
            segments=c.segments or [],
            tags=c.tags or [],
            is_blocked=c.is_blocked,
            last_seen_at=fmt(c.last_seen_at),
            message_count=c.message_count,
            created_at=fmt(c.created_at),
        )


class CustomerDetail(CustomerSummary):
    notes: Optional[str]
    language_code: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]

    @classmethod
    def from_orm(cls, c: Customer) -> "CustomerDetail":
        base = CustomerSummary.from_orm(c)
        return cls(
            **base.dict(),
            notes=c.notes,
            language_code=c.language_code,
            first_name=c.first_name,
            last_name=c.last_name,
        )


class OrderSummary(BaseModel):
    id: str
    total: float
    status: str
    created_at: str
    item_count: Optional[int]


class CustomerDetailResponse(BaseModel):
    customer: CustomerDetail
    recent_orders: List[OrderSummary]


class CRMStats(BaseModel):
    total_customers: int
    new_this_month: int
    repeat_buyers: int
    vip_count: int
    at_risk_count: int
    total_revenue: float
    avg_customer_value: float
    top_spender_amount: float


class UpdateCustomerRequest(BaseModel):
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_blocked: Optional[bool] = None


class SegmentRequest(BaseModel):
    segment: str
    action: str  # "add" | "remove"


class PaginatedCustomers(BaseModel):
    items: List[CustomerSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedCustomers)
async def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search display_name or @username"),
    segment: Optional[str] = Query(None, description="Filter by segment label"),
    sort_by: str = Query("last_order_at", enum=["last_order_at", "total_spent", "total_orders", "created_at"]),
    sort_dir: str = Query("desc", enum=["asc", "desc"]),
    is_blocked: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    base_q = select(Customer).where(Customer.business_id == str(business.id))

    if search:
        term = f"%{search.lower()}%"
        base_q = base_q.where(
            or_(
                func.lower(Customer.display_name).like(term),
                func.lower(Customer.telegram_username).like(term),
            )
        )
    if segment:
        base_q = base_q.where(Customer.segments.contains([segment]))
    if is_blocked is not None:
        base_q = base_q.where(Customer.is_blocked == is_blocked)

    # Count
    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Sort
    sort_col = getattr(Customer, sort_by)
    order_fn = desc if sort_dir == "desc" else lambda x: x
    base_q = base_q.order_by(order_fn(sort_col)).offset((page - 1) * page_size).limit(page_size)

    rows = (await db.execute(base_q)).scalars().all()

    return PaginatedCustomers(
        items=[CustomerSummary.from_orm(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, -(-total // page_size)),
    )


@router.get("/stats", response_model=CRMStats)
async def get_crm_stats(
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    bid = str(business.id)
    month_ago = datetime.utcnow() - timedelta(days=30)

    total = (await db.execute(select(func.count(Customer.id)).where(Customer.business_id == bid))).scalar_one()
    new_month = (await db.execute(select(func.count(Customer.id)).where(Customer.business_id == bid, Customer.created_at >= month_ago))).scalar_one()
    repeat = (await db.execute(select(func.count(Customer.id)).where(Customer.business_id == bid, Customer.segments.contains(["repeat_buyer"])))).scalar_one()
    vip = (await db.execute(select(func.count(Customer.id)).where(Customer.business_id == bid, Customer.segments.contains(["vip"])))).scalar_one()
    at_risk = (await db.execute(select(func.count(Customer.id)).where(Customer.business_id == bid, Customer.segments.contains(["at_risk"])))).scalar_one()
    revenue = (await db.execute(select(func.coalesce(func.sum(Customer.total_spent), 0)).where(Customer.business_id == bid))).scalar_one()
    avg_val = revenue / total if total else 0
    top_spend = (await db.execute(select(func.coalesce(func.max(Customer.total_spent), 0)).where(Customer.business_id == bid))).scalar_one()

    return CRMStats(
        total_customers=total,
        new_this_month=new_month,
        repeat_buyers=repeat,
        vip_count=vip,
        at_risk_count=at_risk,
        total_revenue=round(float(revenue), 2),
        avg_customer_value=round(float(avg_val), 2),
        top_spender_amount=round(float(top_spend), 2),
    )


@router.get("/export")
async def export_customers(
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    rows = (await db.execute(
        select(Customer).where(Customer.business_id == str(business.id)).order_by(Customer.total_spent.desc())
    )).scalars().all()

    def fmt(dt): return dt.isoformat() if dt else ""

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "display_name", "telegram_username", "telegram_user_id",
        "total_orders", "total_spent", "avg_order_value",
        "first_order_at", "last_order_at", "segments", "tags",
        "is_blocked", "notes", "created_at",
    ])
    writer.writeheader()
    for c in rows:
        writer.writerow({
            "display_name": c.display_name,
            "telegram_username": c.telegram_username or "",
            "telegram_user_id": c.telegram_user_id,
            "total_orders": c.total_orders,
            "total_spent": round(c.total_spent, 2),
            "avg_order_value": round(c.average_order_value, 2),
            "first_order_at": fmt(c.first_order_at),
            "last_order_at": fmt(c.last_order_at),
            "segments": ",".join(c.segments or []),
            "tags": ",".join(c.tags or []),
            "is_blocked": c.is_blocked,
            "notes": c.notes or "",
            "created_at": fmt(c.created_at),
        })

    buf.seek(0)
    filename = f"customers_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    c = await _get_owned_customer(db, customer_id, business.id)

    orders_q = await db.execute(
        select(Order).where(Order.customer_id == str(c.id)).order_by(Order.created_at.desc()).limit(10)
    )
    orders = orders_q.scalars().all()

    return CustomerDetailResponse(
        customer=CustomerDetail.from_orm(c),
        recent_orders=[
            OrderSummary(
                id=str(o.id),
                total=round(float(o.total), 2),
                status=o.status,
                created_at=o.created_at.isoformat(),
                item_count=getattr(o, "item_count", None),
            )
            for o in orders
        ],
    )


@router.patch("/{customer_id}", response_model=CustomerDetail)
async def update_customer(
    customer_id: UUID,
    body: UpdateCustomerRequest,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    c = await _get_owned_customer(db, customer_id, business.id)
    if body.notes is not None:
        c.notes = body.notes
    if body.tags is not None:
        c.tags = body.tags
    if body.is_blocked is not None:
        c.is_blocked = body.is_blocked
    c.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(c)
    return CustomerDetail.from_orm(c)


@router.post("/{customer_id}/segment", response_model=CustomerDetail)
async def update_segment(
    customer_id: UUID,
    body: SegmentRequest,
    db: AsyncSession = Depends(get_db),
    business=Depends(get_current_business),
):
    c = await _get_owned_customer(db, customer_id, business.id)
    segs = list(c.segments or [])
    if body.action == "add" and body.segment not in segs:
        segs.append(body.segment)
    elif body.action == "remove" and body.segment in segs:
        segs.remove(body.segment)
    c.segments = segs
    c.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(c)
    return CustomerDetail.from_orm(c)


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_owned_customer(db, customer_id, business_id) -> Customer:
    c = await db.get(Customer, str(customer_id))
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    if str(c.business_id) != str(business_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return c


# ── Called by order_service.py after order completion ────────────────────────

async def upsert_customer_from_telegram(
    db: AsyncSession,
    business_id: str,
    telegram_user: dict,
) -> Customer:
    """
    Called by order_service / session handler to create or update a Customer.
    telegram_user: dict from Telegram update (user object).
    """
    tg_id = telegram_user["id"]
    result = await db.execute(
        select(Customer).where(
            Customer.business_id == business_id,
            Customer.telegram_user_id == tg_id,
        )
    )
    c = result.scalar_one_or_none()

    first = telegram_user.get("first_name", "")
    last = telegram_user.get("last_name", "")
    username = telegram_user.get("username")

    display = " ".join(p for p in [first, last] if p) or (f"@{username}" if username else f"User {tg_id}")

    if c is None:
        c = Customer(
            business_id=business_id,
            telegram_user_id=tg_id,
            telegram_username=username,
            first_name=first,
            last_name=last,
            language_code=telegram_user.get("language_code"),
            display_name=display,
            last_seen_at=datetime.utcnow(),
            message_count=1,
        )
        db.add(c)
    else:
        c.telegram_username = username
        c.first_name = first
        c.last_name = last
        c.display_name = display
        c.last_seen_at = datetime.utcnow()
        c.message_count = (c.message_count or 0) + 1
        c.updated_at = datetime.utcnow()

    await db.flush()
    return c


async def record_order_for_customer(
    db: AsyncSession,
    customer_id: str,
    order_total: float,
) -> None:
    """
    Called by order_service after an order is paid.
    Updates denormalised stats + auto-segments.
    """
    c = await db.get(Customer, customer_id)
    if not c:
        return

    now = datetime.utcnow()
    c.total_orders += 1
    c.total_spent += order_total
    c.average_order_value = c.total_spent / c.total_orders
    c.last_order_at = now
    if not c.first_order_at:
        c.first_order_at = now

    # Merge auto-segments with any manual ones
    auto = set(c.auto_segment())
    manual = set(c.segments or []) - {"new", "repeat_buyer", "vip", "at_risk"}
    c.segments = sorted(auto | manual)
    c.updated_at = now
    await db.flush()
