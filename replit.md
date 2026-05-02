# SaaS Bot Platform

## Overview

Multi-tenant Telegram SaaS platform that lets businesses run full e-commerce stores inside Telegram bots. Includes an AI store builder, multi-provider payments, conversation flow engine, and a React merchant dashboard.

## Architecture

```
apps/
  backend/          # FastAPI Python backend
    app/            # Entry point, config, database connection
    core/           # Billing, limits, plans, security, Redis queue
    models/         # SQLAlchemy models (business, store, product, order, etc.)
    routes/         # REST API routes + webhook receivers
    services/       # Business logic (AI, Telegram, payments, analytics)
    flow_engine.py  # Telegram conversation flow router
    flow_executor.py# Executes individual flow steps
    workers/        # RQ background job handlers
    alembic/        # Database migrations
  worker/
    worker.py       # Standalone RQ worker process

artifacts/
  frontend/         # React + Vite merchant dashboard (pnpm workspace)
    src/
      pages/        # Dashboard, AIBuilder, Products, Orders, Analytics, Pricing, StorePreview
      components/   # Layout, Sidebar, Navbar, ProductCard, Loader
      services/     # api.ts (axios), auth.ts
      utils/        # formatCurrency.ts, getSubdomain.ts

infra/
  docker-compose.yml  # Local dev (PostgreSQL + Redis + backend + worker)

render.yaml         # Render.com deployment config
.env.example        # All required environment variables
```

## Stack

### Backend (Python)
- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL + SQLAlchemy (async) + Alembic migrations
- **Queue**: Redis + RQ (background jobs)
- **Auth**: JWT (python-jose) + bcrypt (passlib)
- **AI**: OpenAI GPT-4o-mini
- **Payments**: Stripe, Telebirr, M-Pesa
- **Telegram**: httpx webhook bot (no polling)

### Frontend (TypeScript/React)
- **Framework**: React 18 + Vite
- **Routing**: Wouter
- **HTTP**: Axios
- **UI**: Tailwind CSS + Shadcn/ui components
- **Build**: pnpm workspace (`@workspace/frontend`)

## Key Commands

### Frontend
- `pnpm --filter @workspace/frontend run dev` — start dev server
- `pnpm --filter @workspace/frontend run build` — production build

### Backend
- `uvicorn app.main:app --reload` — start FastAPI server
- `python apps/worker/worker.py` — start RQ worker
- `alembic upgrade head` — run DB migrations
- `alembic revision --autogenerate -m "description"` — generate migration

### Monorepo
- `pnpm run typecheck` — full TypeScript check
- `pnpm --filter @workspace/api-spec run codegen` — regen API hooks

## Environment Variables

Copy `.env.example` to `.env` and fill in:
- `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `TELEBIRR_*` — Telebirr credentials
- `MPESA_*` — M-Pesa credentials
- `OPENAI_API_KEY`

## Subscription Plans

Four tiers: **Free → Starter ($29/mo) → Pro ($79/mo) → Enterprise ($199/mo)**

Plan limits enforced via `core/billing.py` + `core/limits.py` on every protected route.

## Data Flow

1. **Customer order**: Telegram → webhook → FastAPI → Flow Engine → Payment Service → RQ Worker → DB update → Telegram notification
2. **AI store build**: Dashboard → POST /ai/build-store → FastAPI background task → OpenAI → DB (store, categories, products)
3. **Subscription**: Dashboard → POST /billing/subscribe → DB → RQ worker checks renewals daily
