from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine
from routes import auth, products, stores, flows, payments, billing, ai, analytics, customers, broadcasts
from routes.webhooks import telegram, stripe, telebirr, mpesa


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="SaaS Bot Platform",
    version="1.0.0",
    description="Multi-tenant Telegram SaaS e-commerce platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(stores.router, prefix="/api/stores", tags=["stores"])
app.include_router(flows.router, prefix="/api/flows", tags=["flows"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(customers.router, prefix="/api/customers", tags=["customers"])
app.include_router(broadcasts.router, prefix="/api/broadcasts", tags=["broadcasts"])

app.include_router(telegram.router, prefix="/webhooks/telegram", tags=["webhooks"])
app.include_router(stripe.router, prefix="/webhooks/stripe", tags=["webhooks"])
app.include_router(telebirr.router, prefix="/webhooks/telebirr", tags=["webhooks"])
app.include_router(mpesa.router, prefix="/webhooks/mpesa", tags=["webhooks"])


@app.get("/health")
async def health():
    return {"status": "ok"}
