"""add customers table

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "business_id",
            sa.String(),
            sa.ForeignKey("businesses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=False),
        sa.Column("telegram_username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(128), nullable=True),
        sa.Column("last_name", sa.String(128), nullable=True),
        sa.Column("language_code", sa.String(8), nullable=True),
        sa.Column("display_name", sa.String(256), nullable=False, server_default="Unknown"),
        sa.Column("total_orders", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Float, nullable=False, server_default="0"),
        sa.Column("average_order_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("last_order_at", sa.DateTime, nullable=True),
        sa.Column("first_order_at", sa.DateTime, nullable=True),
        sa.Column("segments", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_blocked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_seen_at", sa.DateTime, nullable=True),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_unique_constraint(
        "uq_customer_per_business", "customers", ["business_id", "telegram_user_id"]
    )
    op.create_index("ix_customers_business_id", "customers", ["business_id"])
    op.create_index("ix_customers_telegram_user_id", "customers", ["telegram_user_id"])
    op.create_index("ix_customers_total_spent", "customers", ["business_id", "total_spent"])
    op.create_index("ix_customers_last_order_at", "customers", ["business_id", "last_order_at"])

    op.add_column(
        "orders",
        sa.Column(
            "customer_id",
            sa.String(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_customer_id", "orders")
    op.drop_column("orders", "customer_id")
    op.drop_index("ix_customers_last_order_at", "customers")
    op.drop_index("ix_customers_total_spent", "customers")
    op.drop_index("ix_customers_telegram_user_id", "customers")
    op.drop_index("ix_customers_business_id", "customers")
    op.drop_table("customers")
