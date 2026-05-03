"""
alembic/versions/0002_add_customers.py

Migration: add customers table with denormalised order stats,
ARRAY segments/tags columns, and proper multi-tenant indexes.

Run with:
    alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_add_customers"
down_revision = "0001_add_bot_configs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "business_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Telegram identity
        sa.Column("telegram_user_id", sa.BigInteger, nullable=False),
        sa.Column("telegram_username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(128), nullable=True),
        sa.Column("last_name", sa.String(128), nullable=True),
        sa.Column("language_code", sa.String(8), nullable=True),
        sa.Column("display_name", sa.String(256), nullable=False, server_default="Unknown"),
        # Order stats (denormalised)
        sa.Column("total_orders", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Float, nullable=False, server_default="0"),
        sa.Column("average_order_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("last_order_at", sa.DateTime, nullable=True),
        sa.Column("first_order_at", sa.DateTime, nullable=True),
        # CRM
        sa.Column("segments", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("tags",     postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        # Engagement
        sa.Column("is_blocked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_seen_at", sa.DateTime, nullable=True),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0"),
        # Timestamps
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Unique: one customer row per (business, telegram user)
    op.create_unique_constraint(
        "uq_customer_per_business", "customers",
        ["business_id", "telegram_user_id"],
    )

    op.create_index("ix_customers_business_id",    "customers", ["business_id"])
    op.create_index("ix_customers_telegram_user",  "customers", ["telegram_user_id"])
    op.create_index("ix_customers_total_spent",    "customers", ["business_id", "total_spent"])
    op.create_index("ix_customers_last_order_at",  "customers", ["business_id", "last_order_at"])

    # Add customer_id FK to orders table (if not already present)
    op.add_column(
        "orders",
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_customer_id", "orders")
    op.drop_column("orders", "customer_id")
    op.drop_table("customers")
